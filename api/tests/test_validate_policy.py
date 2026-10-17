import importlib.util
import sys
from pathlib import Path
from typing import Any

from app import config

SCRIPT = Path(__file__).resolve().parents[1] / "seed" / "validate_policy.py"
spec = importlib.util.spec_from_file_location("validate_policy", SCRIPT)
assert spec and spec.loader
validate = importlib.util.module_from_spec(spec)
sys.modules["validate_policy"] = validate
spec.loader.exec_module(validate)


def _form(
    annuity: float = 15_000.0, loan: float = 450_000.0, **scores: float | None
) -> dict[str, Any]:
    base: dict[str, Any] = {"ext_source_1": None, "ext_source_2": 0.6, "ext_source_3": None}
    return {"annuity": annuity, "annual_income": 150_000.0, "loan_amount": loan, **base, **scores}


def test_healthy_row_is_approved() -> None:
    assert validate.classify_form(_form()).value == "approve"


def test_high_payment_ratio_is_declined() -> None:
    assert validate.classify_form(_form(annuity=60_000.0)).value == "decline"


def test_low_score_is_declined() -> None:
    low = config.POLICY_DECLINE_SCORE_AVERAGE - 0.1
    assert validate.classify_form(_form(ext_source_2=low)).value == "decline"


def test_high_loan_to_income_refers() -> None:
    assert validate.classify_form(_form(loan=1_000_000.0)).value == "refer"


def test_missing_inputs_or_scores_never_approve() -> None:
    assert validate.classify_form(_form(ext_source_2=None)).value == "refer"
    assert validate.classify_form(_form(annuity=0)).value == "refer"


def test_default_rates_per_bucket() -> None:
    records = [
        {"input": {"form": _form()}, "target": 0},
        {"input": {"form": _form()}, "target": 0},
        {"input": {"form": _form(annuity=60_000.0)}, "target": 1},
        {"input": {"form": _form(annuity=60_000.0)}, "target": 0},
    ]

    rates = validate.default_rates(records)

    assert rates["approve"]["default_rate"] == 0.0
    assert rates["decline"]["default_rate"] == 0.5
    assert rates["decline"]["share"] == 0.5
    assert "refer" not in rates
