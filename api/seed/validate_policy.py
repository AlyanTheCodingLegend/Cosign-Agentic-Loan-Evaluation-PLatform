"""Check a percentile-based policy against real outcomes in the Home Credit sample.

Usage (from api/, after prepare_home_credit.py):
    python seed/validate_policy.py

Applies an explicit threshold policy to every sampled row and prints the TARGET (default) rate
per bucket. If the decline bucket defaults at a clearly higher rate than the approve bucket, the
policy ranks risk in the right order. TARGET is used only here, to check the policy; it is never
an input to it. This is a distilled policy, not real underwriter judgment.
"""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

# Cutoffs are percentiles of the sample, not currency amounts or fixed ratios.
DECLINE_PTI_PERCENTILE = 90
REFER_PTI_PERCENTILE = 75
DECLINE_SCORE_PERCENTILE = 15
REFER_SCORE_PERCENTILE = 30

SCORE_KEYS = ("ext_source_1", "ext_source_2", "ext_source_3")
APPROVE, REFER, DECLINE = "approve", "refer", "decline"


def payment_to_income(form: dict[str, Any]) -> float:
    """Annuity divided by monthly income."""
    return float(form["annuity"]) / (float(form["annual_income"]) / 12)


def score_average(form: dict[str, Any]) -> float | None:
    """Mean of the available external scores, or None when all are missing."""
    scores = [form[k] for k in SCORE_KEYS if form[k] is not None]
    return sum(scores) / len(scores) if scores else None


def percentile(values: list[float], pct: int) -> float:
    """Return the pct-th percentile of values."""
    return statistics.quantiles(values, n=100)[pct - 1]


def build_cutoffs(forms: list[dict[str, Any]]) -> dict[str, float]:
    """Derive the policy cutoffs from the sample's own distribution."""
    ratios = [payment_to_income(f) for f in forms if f["annuity"] and f["annual_income"]]
    averages = [a for f in forms if (a := score_average(f)) is not None]
    return {
        "decline_pti": percentile(ratios, DECLINE_PTI_PERCENTILE),
        "refer_pti": percentile(ratios, REFER_PTI_PERCENTILE),
        "decline_score": percentile(averages, DECLINE_SCORE_PERCENTILE),
        "refer_score": percentile(averages, REFER_SCORE_PERCENTILE),
    }


def classify(form: dict[str, Any], cutoffs: dict[str, float]) -> str:
    """Return approve, refer or decline. Missing scores or inputs never approve."""
    if not form["annuity"] or not form["annual_income"]:
        return REFER
    average = score_average(form)
    if average is None:
        return REFER
    ratio = payment_to_income(form)
    if ratio > cutoffs["decline_pti"] or average <= cutoffs["decline_score"]:
        return DECLINE
    if ratio > cutoffs["refer_pti"] or average <= cutoffs["refer_score"]:
        return REFER
    return APPROVE


def default_rates(
    records: list[dict[str, Any]], cutoffs: dict[str, float]
) -> dict[str, dict[str, float]]:
    """Return count, share and default rate for each bucket."""
    counts: dict[str, int] = defaultdict(int)
    defaults: dict[str, int] = defaultdict(int)
    for record in records:
        bucket = classify(record["input"]["form"], cutoffs)
        counts[bucket] += 1
        defaults[bucket] += record["target"]
    return {
        bucket: {
            "count": counts[bucket],
            "share": counts[bucket] / len(records),
            "default_rate": defaults[bucket] / counts[bucket],
        }
        for bucket in (APPROVE, REFER, DECLINE)
        if counts[bucket]
    }


def main() -> None:
    """Load the sample, apply the policy and print the table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample", type=Path, default=Path(__file__).with_name("home_credit_sample.jsonl")
    )
    args = parser.parse_args()
    records = [json.loads(line) for line in args.sample.read_text(encoding="utf-8").splitlines()]
    cutoffs = build_cutoffs([r["input"]["form"] for r in records])
    print("cutoffs:", {k: round(v, 3) for k, v in cutoffs.items()})
    overall = sum(r["target"] for r in records) / len(records)
    print(f"overall default rate: {overall:.1%} ({len(records)} rows)")
    print(f"{'bucket':<10}{'rows':>7}{'share':>9}{'default rate':>15}")
    for bucket, stats in default_rates(records, cutoffs).items():
        print(
            f"{bucket:<10}{stats['count']:>7.0f}{stats['share']:>9.1%}{stats['default_rate']:>15.1%}"
        )


if __name__ == "__main__":
    main()
