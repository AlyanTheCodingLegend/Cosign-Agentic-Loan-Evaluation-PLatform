"""Build the fine-tuning dataset and the folder to upload to Kaggle.

Run from the repo root with the API venv, because it imports the app's own prompt and policy:

    api\\.venv\\Scripts\\python ml\\build_dataset.py PATH\\TO\\sample.jsonl

The sample comes from `api/seed/prepare_home_credit.py` (use --size 8000 or more). Each training
row is a chat: the exact system prompt and user prompt the API sends at inference, and the
reasoner JSON the policy produces as the answer. The labels come from the explicit policy in
`api/app/agent/policy.py`, so the model learns a distilled policy, not underwriter judgment.
TARGET (default) never enters a row. Protected attributes are never read.

Writes ml/kaggle_bundle/ (git-ignored): train.jsonl, val.jsonl, test.jsonl, train.py. Upload that
folder to Kaggle as a private dataset.
"""

import argparse
import json
import random
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from app.agent.fake_model import FakeModelClient
from app.agent.metrics import compute_metrics
from app.agent.reasoner import REASONER_SCHEMA_NAME, SYSTEM_PROMPT, build_prompt
from app.agent.router import check_completeness
from app.models.contract import ApplicantFields, ReasonerInput, ReasonerOutput

ML_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = ML_DIR / "kaggle_bundle"
PROTECTED_PATTERN = re.compile(r"\b(gender|birth|age|family|marital|sex)\b", re.IGNORECASE)
APPROX_CHARS_PER_TOKEN = 3


def build_example(record: dict[str, Any]) -> dict[str, Any] | None:
    """Return one chat example, or None when required fields are missing (needs_info path)."""
    form = record["input"]["form"]
    fields = ApplicantFields.model_validate(
        {k: v for k, v in form.items() if k in ApplicantFields.model_fields}
    )
    if check_completeness(fields):
        return None
    assert fields.annual_income and fields.loan_amount and fields.annuity
    metrics = compute_metrics(
        fields.annual_income, fields.loan_amount, fields.annuity, fields.document_income
    )
    user = build_prompt(ReasonerInput(fields=fields, metrics=metrics))
    answer = FakeModelClient().complete_json(SYSTEM_PROMPT, user, REASONER_SCHEMA_NAME, {})
    ReasonerOutput.model_validate_json(answer)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": answer},
        ]
    }


def label_of(example: dict[str, Any]) -> str:
    """Return the recommendation in the example's answer."""
    return str(json.loads(example["messages"][2]["content"])["recommendation"])


def assert_no_protected_terms(example: dict[str, Any]) -> None:
    """Fail loudly if a user or assistant message mentions a protected attribute."""
    for message in example["messages"][1:]:
        match = PROTECTED_PATTERN.search(message["content"])
        if match:
            raise ValueError(f"protected term {match.group(0)!r} in training row")


def split(
    examples: list[dict[str, Any]], val: int, test: int, max_train: int, seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Shuffle and split into train, validation and test."""
    shuffled = examples[:]
    random.Random(seed).shuffle(shuffled)
    test_set = shuffled[:test]
    val_set = shuffled[test : test + val]
    train_set = shuffled[test + val :][:max_train]
    return train_set, val_set, test_set


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write one JSON object per line."""
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def main() -> None:
    """Build the examples, split them and write the Kaggle bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path)
    parser.add_argument("--val", type=int, default=300)
    parser.add_argument("--test", type=int, default=500)
    parser.add_argument("--max-train", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    records = [json.loads(line) for line in args.sample.read_text(encoding="utf-8").splitlines()]
    built = [build_example(r) for r in records]
    examples = [e for e in built if e is not None]
    for example in examples:
        assert_no_protected_terms(example)
    print(f"{len(examples)} usable of {len(records)} rows ({len(records) - len(examples)} skipped)")

    train, val, test = split(examples, args.val, args.test, args.max_train, args.seed)
    BUNDLE_DIR.mkdir(exist_ok=True)
    for name, rows in (("train", train), ("val", val), ("test", test)):
        write_jsonl(BUNDLE_DIR / f"{name}.jsonl", rows)
        print(f"{name}: {len(rows)} rows, labels {dict(Counter(label_of(r) for r in rows))}")
    shutil.copy(ML_DIR / "train.py", BUNDLE_DIR / "train.py")

    longest = max(sum(len(m["content"]) for m in e["messages"]) for e in train)
    print(f"longest example is about {longest // APPROX_CHARS_PER_TOKEN} tokens")
    print(f"upload the folder {BUNDLE_DIR} to Kaggle as a private dataset")


if __name__ == "__main__":
    main()
