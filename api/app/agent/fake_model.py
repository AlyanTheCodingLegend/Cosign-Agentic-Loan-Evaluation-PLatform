"""Rule-based stand-in for the model, used with USE_FAKES for tests and local runs.

The reasoner policy here is a simple threshold function. It is a placeholder for the
fine-tuned model, which learns a distilled policy and not real underwriter judgment.
"""

import json
import re
from typing import Any

from app.agent.reasoner import REASONER_SCHEMA_NAME, ModelError
from app.models.contract import ApplicantFields

EXTRACTION_SCHEMA_NAME = "applicant_fields"

# Policy thresholds for the fake reasoner (ratios and scores, no currency amounts).
DECLINE_PAYMENT_TO_INCOME = 0.50
BORDERLINE_PAYMENT_TO_INCOME = 0.35
DECLINE_LOAN_TO_INCOME = 8.0
BORDERLINE_LOAN_TO_INCOME = 5.0
DECLINE_EXT_SCORE = 0.25
BORDERLINE_EXT_SCORE = 0.40
BASE_CONFIDENCE = 0.90
CONFIDENCE_PENALTY_PER_MISSING_SCORE = 0.10

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
    scores = [
        fields[k] for k in ("ext_source_1", "ext_source_2", "ext_source_3") if fields[k] is not None
    ]
    missing = 3 - len(scores)
    average = sum(scores) / len(scores) if scores else None
    reasons = [f"payment_to_income {pti:.2f}", f"loan_to_income {lti:.2f}"]
    if average is None:
        reasons.append("ext_source_1/2/3 are all missing, so no external score is available")
        return _answer("refer", 0.4, reasons, "Can you provide an external credit score?")
    reasons.append(f"average of available ext_source scores is {average:.2f}")
    if missing:
        reasons.append(f"{missing} of 3 ext_source scores are missing")
    if pti > DECLINE_PAYMENT_TO_INCOME or lti > DECLINE_LOAN_TO_INCOME:
        return _answer("decline", 0.85, reasons, None)
    if average < DECLINE_EXT_SCORE:
        return _answer("decline", 0.80, reasons, None)
    borderline = (
        pti > BORDERLINE_PAYMENT_TO_INCOME
        or lti > BORDERLINE_LOAN_TO_INCOME
        or average < BORDERLINE_EXT_SCORE
    )
    confidence = BASE_CONFIDENCE - CONFIDENCE_PENALTY_PER_MISSING_SCORE * missing
    if borderline:
        return _answer("refer", 0.6, reasons + ["metrics sit near the risk-band edge"], None)
    return _answer("approve", confidence, reasons, None)


def _answer(
    recommendation: str, confidence: float, reasons: list[str], question: str | None
) -> dict[str, Any]:
    needs_human = recommendation != "approve"
    return {
        "recommendation": recommendation,
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
