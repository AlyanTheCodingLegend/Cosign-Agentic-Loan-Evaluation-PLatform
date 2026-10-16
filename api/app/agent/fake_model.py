"""Rule-based stand-in for the model, used with USE_FAKES for tests and local runs.

It recommends with the shared policy in policy.py. The fine-tuned model learns that same
distilled policy, not real underwriter judgment.
"""

import json
import re
from typing import Any

from app.agent.extraction import EXTRACTION_SCHEMA_NAME
from app.agent.policy import classify, score_average
from app.agent.reasoner import REASONER_SCHEMA_NAME, ModelError
from app.models.contract import ApplicantFields, Recommendation

BASE_CONFIDENCE = 0.90
CONFIDENCE_PENALTY_PER_MISSING_SCORE = 0.10
REFER_CONFIDENCE = 0.60
NO_SCORES_CONFIDENCE = 0.40
DECLINE_CONFIDENCE = 0.85
SCORE_KEYS = ("ext_source_1", "ext_source_2", "ext_source_3")

_ANNUAL_INCOME_PATTERN = re.compile(
    r"annual\s+(?:gross\s+|net\s+)?(?:income|salary)\D{0,20}?([\d][\d,]*(?:\.\d+)?)", re.IGNORECASE
)


def _payload(user: str) -> dict[str, Any]:
    start = user.index("{")
    payload: dict[str, Any] = json.loads(user[start:])
    return payload


def _document_income(documents: list[dict[str, Any]]) -> float | None:
    for document in documents:
        match = _ANNUAL_INCOME_PATTERN.search(str(document.get("text", "")))
        if match:
            return float(match.group(1).replace(",", ""))
    return None


def _extract(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = set(ApplicantFields.model_fields)
    fields = {k: v for k, v in payload["form"].items() if k in allowed}
    fields["document_income"] = _document_income(payload.get("documents", []))
    return fields


def _reason(payload: dict[str, Any]) -> dict[str, Any]:
    fields, metrics = payload["fields"], payload["metrics"]
    pti, lti = metrics["payment_to_income"], metrics["loan_to_income"]
    average = score_average([fields[k] for k in SCORE_KEYS])
    reasons = [f"payment_to_income {pti:.2f}", f"loan_to_income {lti:.2f}"]
    if average is None:
        reasons.append("ext_source_1/2/3 are all missing, so no external score is available")
        return _answer(
            Recommendation.REFER,
            NO_SCORES_CONFIDENCE,
            reasons,
            "Can you provide an external credit score?",
        )
    missing = sum(fields[k] is None for k in SCORE_KEYS)
    reasons.append(f"average of available ext_source scores is {average:.2f}")
    if missing:
        reasons.append(f"{missing} of 3 ext_source scores are missing")
    recommendation = classify(pti, lti, average)
    if recommendation is Recommendation.DECLINE:
        return _answer(recommendation, DECLINE_CONFIDENCE, reasons, None)
    if recommendation is Recommendation.REFER:
        reasons.append("metrics sit near the risk-band edge")
        return _answer(recommendation, REFER_CONFIDENCE, reasons, None)
    confidence = BASE_CONFIDENCE - CONFIDENCE_PENALTY_PER_MISSING_SCORE * missing
    return _answer(recommendation, confidence, reasons, None)


def _answer(
    recommendation: Recommendation,
    confidence: float,
    reasons: list[str],
    question: str | None,
) -> dict[str, Any]:
    needs_human = recommendation is not Recommendation.APPROVE
    return {
        "recommendation": recommendation.value,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "needs_human": needs_human,
        "human_question": question if needs_human else None,
    }


class FakeModelClient:
    """ModelClient that answers extraction and reasoning from simple rules."""

    def complete_json(
        self, system: str, user: str, schema_name: str, schema: dict[str, Any]
    ) -> str:
        """Return a JSON answer for the requested schema."""
        payload = _payload(user)
        if schema_name == EXTRACTION_SCHEMA_NAME:
            return json.dumps(_extract(payload))
        if schema_name == REASONER_SCHEMA_NAME:
            return json.dumps(_reason(payload))
        raise ModelError(f"unknown schema {schema_name}")
