"""Check the frozen risk policy against real outcomes in the Home Credit sample.

Usage (from api/, after prepare_home_credit.py):
    python seed/validate_policy.py

Applies app.agent.policy.classify, with the cutoffs frozen in config.py, to every sampled row
and prints the TARGET (default) rate per bucket. If the decline bucket defaults at a clearly
higher rate than the approve bucket, the policy ranks risk in the right order. TARGET is used
only here, to check the policy; it is never an input to it. This is a distilled policy, not
real underwriter judgment.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.agent.policy import classify, score_average
from app.models.contract import Recommendation

SCORE_KEYS = ("ext_source_1", "ext_source_2", "ext_source_3")
BUCKETS = (Recommendation.APPROVE, Recommendation.REFER, Recommendation.DECLINE)


def classify_form(form: dict[str, Any]) -> Recommendation:
    """Apply the policy to one form. A row missing income or annuity is referred."""
    if not form["annuity"] or not form["annual_income"] or not form["loan_amount"]:
        return Recommendation.REFER
    payment_to_income = form["annuity"] / (form["annual_income"] / 12)
    loan_to_income = form["loan_amount"] / form["annual_income"]
    return classify(payment_to_income, loan_to_income, score_average([form[k] for k in SCORE_KEYS]))


def default_rates(records: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Return count, share and default rate for each bucket."""
    counts: dict[Recommendation, int] = defaultdict(int)
    defaults: dict[Recommendation, int] = defaultdict(int)
    for record in records:
        bucket = classify_form(record["input"]["form"])
        counts[bucket] += 1
        defaults[bucket] += record["target"]
    return {
        bucket.value: {
            "count": counts[bucket],
            "share": counts[bucket] / len(records),
            "default_rate": defaults[bucket] / counts[bucket],
        }
        for bucket in BUCKETS
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
    overall = sum(r["target"] for r in records) / len(records)
    print(f"overall default rate: {overall:.1%} ({len(records)} rows)")
    print(f"{'bucket':<10}{'rows':>7}{'share':>9}{'default rate':>15}")
    for bucket, stats in default_rates(records).items():
        print(
            f"{bucket:<10}{stats['count']:>7.0f}{stats['share']:>9.1%}{stats['default_rate']:>15.1%}"
        )


if __name__ == "__main__":
    main()
