import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from app.models.application import ApplicationInput

SCRIPT = Path(__file__).resolve().parents[1] / "seed" / "prepare_home_credit.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prepare_home_credit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["prepare_home_credit"] = module
    spec.loader.exec_module(module)
    return module


prep = _load()


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "SK_ID_CURR": "1",
        "TARGET": "0",
        "AMT_INCOME_TOTAL": "150000.0",
        "AMT_CREDIT": "500000.0",
        "AMT_ANNUITY": "20000.0",
        "AMT_GOODS_PRICE": "450000.0",
        "DAYS_EMPLOYED": "-730",
        "EXT_SOURCE_1": "",
        "EXT_SOURCE_2": "0.5",
        "EXT_SOURCE_3": "0.4",
    }
    row.update(overrides)
    return row


def test_days_are_flipped_to_years() -> None:
    assert prep.years_employed(-730.0) == pytest.approx(2.0, rel=0.01)


def test_pensioner_sentinel_becomes_none() -> None:
    assert prep.years_employed(365243.0) is None
    assert (
        prep.row_to_record(_row(DAYS_EMPLOYED="365243"))["input"]["form"]["years_employed"] is None
    )


def test_blank_scores_become_none_and_record_is_a_valid_input() -> None:
    record = prep.row_to_record(_row())

    assert record["input"]["form"]["ext_source_1"] is None
    assert ApplicationInput.model_validate(record["input"]).form.ext_source_2 == 0.5
    assert record["target"] == 0


def test_protected_columns_are_never_read() -> None:
    record = prep.row_to_record({**_row(), "CODE_GENDER": "F", "DAYS_BIRTH": "-12000"})

    assert "CODE_GENDER" not in str(record)
    assert "DAYS_BIRTH" not in str(record)


def test_sample_keeps_target_proportions() -> None:
    rows = [_row(TARGET="1") for _ in range(100)] + [_row(TARGET="0") for _ in range(900)]

    sample = prep.stratified_sample(rows, 200)

    assert len(sample) == 200
    assert sum(r["TARGET"] == "1" for r in sample) == 20


def test_report_gives_payment_to_income_and_loan_percentile() -> None:
    records = [prep.row_to_record(_row(AMT_CREDIT=str(100_000 * (i + 1)))) for i in range(100)]

    result = prep.report(records)

    assert result["payment_to_income_p50"] == pytest.approx(1.6)
    assert result["loan_amount_p90"] > 8_000_000
