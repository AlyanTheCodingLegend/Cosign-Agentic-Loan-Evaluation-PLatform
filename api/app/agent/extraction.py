"""Turn the submitted form and documents into structured applicant fields."""

from app.models.application import ApplicationInput
from app.models.contract import ApplicantFields


def extract_fields(application: ApplicationInput) -> ApplicantFields:
    """Extract structured fields from the form and documents, dropping protected attributes."""
    raise NotImplementedError
