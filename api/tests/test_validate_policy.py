import importlib.util
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "seed" / "validate_policy.py"
spec = importlib.util.spec_from_file_location("validate_policy", SCRIPT)
assert spec and spec.loader
policy = importlib.util.module_from_spec(spec)
sys.modules["validate_policy"] = policy
spec.loader.exec_module(policy)

CUTOFFS = {"decline_pti": 3.0, "refer_pti": 2.0, "decline_score": 0.2, "refer_score": 0.3}


def _form(annuity: float = 10.0, income: float = 120.0, **scores: float | None) -> dict[str, Any]:
    base: dict[str, Any] = {"ext_source_1": None, "ext_source_2": 0.6, "ext_source_3": None}
    return {"annuity": annuity, "annual_income": income, **base, **scores}


def test_healthy_row_is_approved() -> None:
    assert policy.classify(_form(), CUTOFFS) == "approve"


def test_high_payment_ratio_is_declined() -> None:
    assert policy.classify(_form(annuity=50.0), CUTOFFS) == "decline"


def test_low_score_is_declined() -> None:
    assert policy.classify(_form(ext_source_2=0.1), CUTOFFS) == "decline"


def test_borderline_is_referred() -> None:
    assert policy.classify(_form(annuity=25.0), CUTOFFS) == "refer"
    assert policy.classify(_form(ext_source_2=0.25), CUTOFFS) == "refer"


def test_missing_scores_never_approve() -> None:
    assert policy.classify(_form(ext_source_2=None), CUTOFFS) == "refer"


def test_default_rates_per_bucket() -> None:
    records = [
        {"input": {"form": _form()}, "target": 0},
        {"input": {"form": _form()}, "target": 0},
        {"input": {"form": _form(annuity=50.0)}, "target": 1},
        {"input": {"form": _form(annuity=50.0)}, "target": 0},
    ]

    rates = policy.default_rates(records, CUTOFFS)

    assert rates["approve"]["default_rate"] == 0.0
    assert rates["decline"]["default_rate"] == 0.5
    assert rates["decline"]["share"] == 0.5
    assert "refer" not in rates


def test_cutoffs_come_from_the_sample_distribution() -> None:
    forms = [_form(annuity=float(i + 1), ext_source_2=(i + 1) / 100) for i in range(100)]

    cutoffs = policy.build_cutoffs(forms)

    assert cutoffs["decline_pti"] > cutoffs["refer_pti"]
    assert cutoffs["decline_score"] < cutoffs["refer_score"]
