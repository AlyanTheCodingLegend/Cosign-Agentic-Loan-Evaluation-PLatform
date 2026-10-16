import pytest

from app.agent.router import check_completeness
from app.models.contract import REQUIRED_FIELDS, ApplicantFields


def test_complete_fields_report_nothing_missing(complete_fields: dict[str, object]) -> None:
    assert check_completeness(ApplicantFields.model_validate(complete_fields)) == []


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_one_missing_field_is_reported(complete_fields: dict[str, object], missing: str) -> None:
    fields = ApplicantFields.model_validate({**complete_fields, missing: None})
    assert check_completeness(fields) == [missing]


def test_all_missing_fields_reported_in_order() -> None:
    fields = ApplicantFields(stated_income_source="form")
    assert check_completeness(fields) == ["annual_income", "loan_amount", "annuity", "goods_price"]


def test_optional_fields_do_not_count_as_missing(complete_fields: dict[str, object]) -> None:
    optional_nulls = {
        "years_employed": None,
        "ext_source_1": None,
        "ext_source_2": None,
        "ext_source_3": None,
    }
    fields = ApplicantFields.model_validate({**complete_fields, **optional_nulls})
    assert check_completeness(fields) == []
