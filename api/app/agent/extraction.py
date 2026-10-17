"""Turn the submitted form and documents into structured applicant fields."""

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.agent.reasoner import ModelClient, ModelError
from app.config import MODEL_MAX_RETRIES
from app.models.application import ApplicationInput
from app.models.contract import ApplicantFields

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA_NAME = "applicant_fields"

# annual_income is what the applicant states; it only ever comes from the form or a reply.
FORM_ONLY_FIELDS: frozenset[str] = frozenset({"annual_income"})

SYSTEM_PROMPT = """You extract structured fields from a loan application form and its \
supporting documents. Return a JSON object using only these keys: annual_income, \
document_income, loan_amount, annuity, goods_price, years_employed, ext_source_1, \
ext_source_2, ext_source_3.

Rules:
- Copy values from the form exactly. Do not round, convert or calculate anything.
- document_income is the annual income stated in a salary slip or bank statement. Return it \
only if the document states an annual figure explicitly; otherwise null.
- Use null for anything you cannot find. Never guess.
- Ignore personal details such as age, gender, family status or names; do not output them."""


def build_extraction_prompt(application: ApplicationInput) -> str:
    """Serialize the form, documents and applicant replies for the extraction model."""
    payload = {
        "form": application.form.model_dump(mode="json"),
        "documents": [d.model_dump(mode="json") for d in application.documents],
        "applicant_replies": application.replies,
    }
    return "Extract the applicant fields as JSON.\n" + json.dumps(payload, indent=2)


def _parse_model_fields(raw: str) -> ApplicantFields:
    """Parse model output, dropping any key that is not a known field (hard rule 4)."""
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    allowed = set(ApplicantFields.model_fields)
    return ApplicantFields.model_validate({k: v for k, v in data.items() if k in allowed})


def _form_fields(application: ApplicationInput) -> dict[str, Any]:
    allowed = set(ApplicantFields.model_fields)
    return {
        k: v for k, v in application.form.model_dump().items() if k in allowed and v is not None
    }


def _call_model(application: ApplicationInput, client: ModelClient) -> ApplicantFields | None:
    for attempt in range(1 + MODEL_MAX_RETRIES):
        try:
            raw = client.complete_json(
                SYSTEM_PROMPT,
                build_extraction_prompt(application),
                EXTRACTION_SCHEMA_NAME,
                ApplicantFields.model_json_schema(),
            )
            return _parse_model_fields(raw)
        except (ModelError, ValidationError, ValueError) as exc:
            logger.warning(
                "extraction attempt failed",
                extra={"attempt": attempt + 1, "error": type(exc).__name__},
            )
    return None


def merge_fields(
    application: ApplicationInput, extracted: ApplicantFields | None
) -> ApplicantFields:
    """Combine form, model output and applicant corrections, in that order of precedence.

    Form values win over the model. The model only fills gaps, and never fills annual_income.
    Corrections from applicant replies win over everything.
    """
    merged: dict[str, Any] = {}
    if extracted is not None:
        merged.update(
            {
                k: v
                for k, v in extracted.model_dump().items()
                if v is not None and k not in FORM_ONLY_FIELDS
            }
        )
    merged.update(_form_fields(application))
    merged.update(application.corrections)
    return ApplicantFields.model_validate(merged)


def extract_fields(application: ApplicationInput, client: ModelClient) -> ApplicantFields:
    """Extract structured fields from the form and documents, dropping protected attributes.

    If the model fails twice, fall back to the form values alone; completeness checking then
    decides whether the applicant must be asked for more.
    """
    return merge_fields(application, _call_model(application, client))
