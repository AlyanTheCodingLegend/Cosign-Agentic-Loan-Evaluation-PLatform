"""Raw application input as submitted, before extraction. Fields to be defined."""

from pydantic import BaseModel


class ApplicationInput(BaseModel):
    """The submitted form and documents for one application."""
