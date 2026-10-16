"""Sample application_train.csv into applications the API accepts, and report percentiles.

Usage (from api/, venv active):
    python seed/prepare_home_credit.py PATH/TO/application_train.csv --size 4000

Writes seed/home_credit_sample.jsonl (git-ignored). Each line has the application input and the
TARGET label, kept apart so the label never reaches a prompt. Protected attributes (gender, age,
family status) are dropped here and again by ApplicationForm at the API boundary.
"""

import argparse
import csv
import json
import random
import statistics
from pathlib import Path
from typing import Any

DAYS_EMPLOYED_SENTINEL = 365243
DAYS_PER_YEAR = 365.25
HIGH_LOAN_PERCENTILE = 90

# Columns read from the source. Anything else (including protected columns) is never touched.
USED_COLUMNS = (
    "SK_ID_CURR",
    "TARGET",
    "AMT_INCOME_TOTAL",
    "AMT_CREDIT",
    "AMT_ANNUITY",
    "AMT_GOODS_PRICE",
    "DAYS_EMPLOYED",
    "EXT_SOURCE_1",
    "EXT_SOURCE_2",
    "EXT_SOURCE_3",
)


def _number(value: str) -> float | None:
    return float(value) if value.strip() else None


def years_employed(days_employed: float | None) -> float | None:
    """Convert a negative day count to years; the pensioner sentinel becomes None."""
    if days_employed is None or days_employed == DAYS_EMPLOYED_SENTINEL:
        return None
    return abs(days_employed) / DAYS_PER_YEAR


def row_to_record(row: dict[str, str]) -> dict[str, Any]:
    """Map one CSV row to {"input": ApplicationInput-shaped dict, "target": 0 or 1}."""
    return {
        "input": {
            "form": {
                "annual_income": _number(row["AMT_INCOME_TOTAL"]),
                "loan_amount": _number(row["AMT_CREDIT"]),
                "annuity": _number(row["AMT_ANNUITY"]),
                "goods_price": _number(row["AMT_GOODS_PRICE"]),
                "years_employed": years_employed(_number(row["DAYS_EMPLOYED"])),
                "ext_source_1": _number(row["EXT_SOURCE_1"]),
                "ext_source_2": _number(row["EXT_SOURCE_2"]),
                "ext_source_3": _number(row["EXT_SOURCE_3"]),
            }
        },
        "target": int(row["TARGET"]),
    }


def stratified_sample(rows: list[dict[str, str]], size: int, seed: int = 0) -> list[dict[str, str]]:
    """Sample about `size` rows, keeping the TARGET proportions."""
    rng = random.Random(seed)
    by_target: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_target.setdefault(row["TARGET"], []).append(row)
    sample: list[dict[str, str]] = []
    for group in by_target.values():
        take = round(size * len(group) / len(rows))
        sample.extend(rng.sample(group, min(take, len(group))))
    rng.shuffle(sample)
    return sample


def percentile(values: list[float], pct: int) -> float:
    """Return the pct-th percentile of values."""
    return statistics.quantiles(values, n=100)[pct - 1]


def report(records: list[dict[str, Any]]) -> dict[str, float]:
    """Return the values that set the config thresholds, as ratios and percentiles."""
    forms = [r["input"]["form"] for r in records]
    loans = [f["loan_amount"] for f in forms if f["loan_amount"] is not None]
    ratios = [
        f["annuity"] / (f["annual_income"] / 12)
        for f in forms
        if f["annuity"] is not None and f["annual_income"]
    ]
    return {
        f"loan_amount_p{HIGH_LOAN_PERCENTILE}": percentile(loans, HIGH_LOAN_PERCENTILE),
        "payment_to_income_p50": percentile(ratios, 50),
        "payment_to_income_p90": percentile(ratios, 90),
    }


def main() -> None:
    """Read the CSV, write the sample and print the percentile report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--size", type=int, default=4000)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).with_name("home_credit_sample.jsonl")
    )
    args = parser.parse_args()

    with args.csv_path.open(newline="", encoding="utf-8") as handle:
        rows = [{k: row[k] for k in USED_COLUMNS} for row in csv.DictReader(handle)]
    records = [row_to_record(r) for r in stratified_sample(rows, args.size)]
    args.out.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} rows to {args.out}")
    for name, value in report(records).items():
        print(f"{name}: {value:.4f}")
    print("Set HIGH_LOAN_AMOUNT_CUTOFF in app/config.py from the loan_amount percentile above.")


if __name__ == "__main__":
    main()
