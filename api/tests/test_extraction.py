import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.agent.extraction import build_extraction_prompt, extract_fields
from app.agent.fake_model import FakeModelClient
from app.agent.reasoner import ModelError
from app.models.application import ApplicationForm, ApplicationInput, Document, DocumentKind


class ScriptedClient:
    def __init__(self, *script: str | Exception) -> None:
        self._script = list(script)
        self.calls = 0

    def complete_json(
        self, system: str, user: str, schema_name: str, schema: dict[str, Any]
    ) -> str:
        item = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def _application(**overrides: Any) -> ApplicationInput:
    form = ApplicationForm(
        annual_income=120_000.0, loan_amount=300_000.0, annuity=9_000.0, goods_price=270_000.0
    )
    return ApplicationInput(form=form, **overrides)


def _slip(text: str) -> Document:
    return Document(name="slip.txt", kind=DocumentKind.SALARY_SLIP, text=text)


def test_form_values_pass_through() -> None:
    fields = extract_fields(_application(), FakeModelClient())

    assert fields.annual_income == 120_000.0
    assert fields.loan_amount == 300_000.0
    assert fields.document_income is None


def test_document_income_is_read_from_document() -> None:
    application = _application(documents=[_slip("Employee slip. Annual income: 95,000")])

    fields = extract_fields(application, FakeModelClient())

    assert fields.document_income == 95_000.0
    assert fields.annual_income == 120_000.0


def test_form_wins_over_model_for_form_fields() -> None:
    model_output = json.dumps({"loan_amount": 999.0, "years_employed": 3.0})

    fields = extract_fields(_application(), ScriptedClient(model_output))

    assert fields.loan_amount == 300_000.0
    assert fields.years_employed == 3.0


def test_model_never_fills_annual_income() -> None:
    application = ApplicationInput(form=ApplicationForm(loan_amount=1.0))
    model_output = json.dumps({"annual_income": 50_000.0})

    fields = extract_fields(application, ScriptedClient(model_output))

    assert fields.annual_income is None


def test_unknown_and_protected_keys_from_model_are_dropped() -> None:
    model_output = json.dumps({"document_income": 80_000.0, "gender": "F", "age": 41})

    fields = extract_fields(_application(), ScriptedClient(model_output))

    assert fields.document_income == 80_000.0
    assert "gender" not in fields.model_dump()


def test_corrections_win_over_everything() -> None:
    application = _application(corrections={"annual_income": 100_000.0})

    fields = extract_fields(application, FakeModelClient())

    assert fields.annual_income == 100_000.0


@pytest.mark.parametrize("failure", ["not json", "[1, 2]", ModelError("timeout")])
def test_model_failure_falls_back_to_form_values(failure: str | Exception) -> None:
    client = ScriptedClient(failure)

    fields = extract_fields(_application(), client)

    assert client.calls == 2
    assert fields.annual_income == 120_000.0
    assert fields.document_income is None


def test_extraction_retries_once_then_succeeds() -> None:
    client = ScriptedClient("not json", json.dumps({"document_income": 70_000.0}))

    fields = extract_fields(_application(), client)

    assert client.calls == 2
    assert fields.document_income == 70_000.0


def test_form_drops_protected_columns_from_raw_rows() -> None:
    form = ApplicationForm.model_validate(
        {"annual_income": 1.0, "CODE_GENDER": "F", "DAYS_BIRTH": -12000}
    )

    assert "CODE_GENDER" not in form.model_dump()
    assert "gender" not in build_extraction_prompt(ApplicationInput(form=form)).lower()


@pytest.mark.parametrize("bad", [{"annual_income": -1.0}, {"annuity": 0.0}, {"ext_source_2": 1.5}])
def test_form_rejects_out_of_range_values(bad: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        ApplicationForm.model_validate(bad)
