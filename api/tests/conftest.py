import pytest


@pytest.fixture
def complete_fields() -> dict[str, object]:
    return {
        "annual_income": 120_000.0,
        "document_income": 118_000.0,
        "loan_amount": 300_000.0,
        "annuity": 18_000.0,
        "goods_price": 270_000.0,
        "years_employed": 4.5,
        "ext_source_1": None,
        "ext_source_2": 0.62,
        "ext_source_3": None,
    }
