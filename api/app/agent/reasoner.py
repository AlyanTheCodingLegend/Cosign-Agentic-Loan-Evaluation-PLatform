"""The single place that calls the model and validates its output against the contract."""

import json
import logging
from functools import lru_cache
from typing import Any, Protocol

import openai
from pydantic import ValidationError

from app.agent.policy import score_average
from app.config import (
    MODEL_MAX_RETRIES,
    MODEL_TIMEOUT_SECONDS,
    POLICY_DECLINE_PAYMENT_TO_INCOME,
    POLICY_DECLINE_SCORE_AVERAGE,
    POLICY_REFER_LOAN_TO_INCOME,
    POLICY_REFER_PAYMENT_TO_INCOME,
    POLICY_REFER_SCORE_AVERAGE,
    get_settings,
)
from app.models.contract import ReasonerInput, ReasonerOutput, Recommendation

logger = logging.getLogger(__name__)

REASONER_SCHEMA_NAME = "reasoner_output"
FALLBACK_REASON = "Automated assessment was unavailable or invalid; manual review is required."

SYSTEM_PROMPT = f"""You are a loan underwriting analyst. You receive structured applicant \
fields and affordability metrics that were already computed in code. Never recompute or adjust \
the numbers; use them as given.

Return a JSON object with exactly these keys:
- recommendation: "approve", "decline" or "refer"
- confidence: a number between 0 and 1
- reasons: a non-empty list of short strings; each must cite the specific field or metric it \
rests on, for example "payment_to_income 0.62"
- needs_human: true unless you recommend approve
- human_question: a specific question for the human, or null

Recommendation policy. Apply these rules in order and use the first that matches. Use \
metrics.ext_source_average as given; it is the mean of the available ext_source scores.
1. ext_source_average is null (all three scores missing): refer, confidence 0.4, and ask for \
an external credit score in human_question.
2. payment_to_income above {POLICY_DECLINE_PAYMENT_TO_INCOME} or ext_source_average at or \
below {POLICY_DECLINE_SCORE_AVERAGE}: decline, confidence 0.85.
3. payment_to_income above {POLICY_REFER_PAYMENT_TO_INCOME}, or loan_to_income above \
{POLICY_REFER_LOAN_TO_INCOME}, or ext_source_average at or below \
{POLICY_REFER_SCORE_AVERAGE}: refer, confidence 0.6.
4. Otherwise approve, with confidence 0.9 minus 0.1 for each ext_source that is null.

Rules:
- needs_human must be true whenever recommendation is not "approve".
- human_question must be null when needs_human is false, and null for decline and refer \
except in rule 1.
- Say in the reasons when an ext_source is null.
- Judge only on the data given. Never infer or mention age, gender or family status."""


class ModelError(Exception):
    """Raised when the model call fails, times out or returns something unusable."""


class ModelClient(Protocol):
    """An OpenAI-compatible chat model that returns a JSON string."""

    def complete_json(
        self, system: str, user: str, schema_name: str, schema: dict[str, Any]
    ) -> str: ...


class OpenAIModelClient:
    """ModelClient backed by any OpenAI-compatible endpoint, set by env."""

    def __init__(self, base_url: str, model_name: str, api_key: str) -> None:
        self._model_name = model_name
        self._client = openai.OpenAI(
            base_url=base_url, api_key=api_key, timeout=MODEL_TIMEOUT_SECONDS, max_retries=0
        )

    def complete_json(
        self, system: str, user: str, schema_name: str, schema: dict[str, Any]
    ) -> str:
        """Call the model with JSON-schema output and return the raw message content."""
        try:
            response = self._client.chat.completions.create(
                model=self._model_name,
                temperature=0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "schema": schema},
                },
            )
        except openai.OpenAIError as exc:
            raise ModelError(f"{type(exc).__name__}: {exc}") from exc
        content = response.choices[0].message.content
        if not content:
            raise ModelError("model returned an empty message")
        return content


@lru_cache
def get_model_client() -> ModelClient:
    """Return the process-wide model client: the rule-based fake when USE_FAKES is set."""
    settings = get_settings()
    if settings.use_fakes:
        from app.agent.fake_model import FakeModelClient

        return FakeModelClient()
    return OpenAIModelClient(
        settings.model_base_url, settings.model_name, settings.model_api_key.get_secret_value()
    )


def build_prompt(inp: ReasonerInput) -> str:
    """Build the reasoner prompt from fields and precomputed metrics, without protected data."""
    fields = inp.fields
    # The average is computed here, in code, so the model never does the arithmetic.
    average = score_average([fields.ext_source_1, fields.ext_source_2, fields.ext_source_3])
    metrics = inp.metrics.model_dump(mode="json")
    metrics["ext_source_average"] = None if average is None else round(average, 4)
    payload = {"fields": fields.model_dump(mode="json"), "metrics": metrics}
    return "Assess this loan application and answer in JSON.\n" + json.dumps(payload, indent=2)


def _fallback() -> ReasonerOutput:
    return ReasonerOutput(
        recommendation=Recommendation.REFER,
        confidence=0.0,
        reasons=[FALLBACK_REASON],
        needs_human=True,
        human_question=None,
    )


def _attempt(inp: ReasonerInput, client: ModelClient) -> ReasonerOutput:
    raw = client.complete_json(
        SYSTEM_PROMPT,
        build_prompt(inp),
        REASONER_SCHEMA_NAME,
        ReasonerOutput.model_json_schema(),
    )
    return ReasonerOutput.model_validate_json(raw)


def recommend(inp: ReasonerInput, client: ModelClient) -> ReasonerOutput:
    """Call the model, retry once on failure, and fall back to refer with needs_human."""
    for attempt in range(1 + MODEL_MAX_RETRIES):
        try:
            return _attempt(inp, client)
        except (ModelError, ValidationError) as exc:
            logger.warning(
                "reasoner attempt failed",
                extra={"attempt": attempt + 1, "error": type(exc).__name__},
            )
    return _fallback()
