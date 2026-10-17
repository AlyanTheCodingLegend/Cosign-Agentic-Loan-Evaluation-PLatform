"""QLoRA fine-tune of the reasoner on Kaggle with Unsloth, built for an unattended overnight run.

Reads train.jsonl, val.jsonl and test.jsonl from the Kaggle dataset next to this file (made by
ml/build_dataset.py). Saves a LoRA checkpoint every SAVE_STEPS steps, stops cleanly before the
Kaggle session limit, and writes the final adapter and a held-out check at the end.

Settings are environment variables so the notebook can change them without editing this file:
BASE_MODEL, EPOCHS, LEARNING_RATE, BATCH_SIZE, GRAD_ACCUM, SAVE_STEPS, MAX_HOURS, EVAL_N,
HF_REPO (optional, push every checkpoint to this Hugging Face repo), RESUME_FROM (a checkpoint dir).
"""

# Unsloth must be imported before transformers, trl and peft.
from unsloth import FastLanguageModel  # isort: skip

import glob
import json
import os
import time
from pathlib import Path
from typing import Any

import torch
from datasets import Dataset
from transformers import TrainerCallback
from trl import SFTConfig, SFTTrainer

BASE_MODEL = os.environ.get("BASE_MODEL", "unsloth/Qwen2.5-3B-Instruct")
EPOCHS = float(os.environ.get("EPOCHS", "3"))
LEARNING_RATE = float(os.environ.get("LEARNING_RATE", "2e-4"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "4"))
GRAD_ACCUM = int(os.environ.get("GRAD_ACCUM", "4"))
SAVE_STEPS = int(os.environ.get("SAVE_STEPS", "50"))
# Kaggle stops a session at 12 hours. Stop before that so the run ends cleanly and saves.
MAX_HOURS = float(os.environ.get("MAX_HOURS", "10.5"))
EVAL_N = int(os.environ.get("EVAL_N", "100"))
HF_REPO = os.environ.get("HF_REPO", "")
RESUME_FROM = os.environ.get("RESUME_FROM", "")
MAX_SEQ_LENGTH = 1536
SEED = 3407

OUT_DIR = Path(os.environ.get("OUT_DIR", "/kaggle/working"))
CHECKPOINT_DIR = OUT_DIR / "outputs"
FINAL_DIR = OUT_DIR / "final_adapter"
# Chat markers for Qwen's ChatML template, used to train only on the assistant's answer.
USER_MARKER = "<|im_start|>user\n"
ASSISTANT_MARKER = "<|im_start|>assistant\n"


def find_data_dir() -> Path:
    """Locate the folder holding train.jsonl: next to this file, or any Kaggle input."""
    here = Path(__file__).resolve().parent
    if (here / "train.jsonl").exists():
        return here
    matches = glob.glob("/kaggle/input/**/train.jsonl", recursive=True)
    if not matches:
        raise FileNotFoundError("train.jsonl not found; attach the dataset to this notebook")
    return Path(matches[0]).parent


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read one JSON object per line."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def hf_token() -> str | None:
    """Return a Hugging Face token from Kaggle secrets or the environment, if any."""
    if not HF_REPO:
        return None
    try:
        from kaggle_secrets import UserSecretsClient

        return str(UserSecretsClient().get_secret("HF_TOKEN"))
    except Exception:  # noqa: BLE001 - secrets are optional; fall back to the environment
        return os.environ.get("HF_TOKEN")


class TimeLimit(TrainerCallback):
    """Save and stop once the run has used its time budget."""

    def __init__(self, hours: float) -> None:
        self.deadline = time.time() + hours * 3600

    def on_step_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> Any:
        """Request a checkpoint and a clean stop when the deadline passes."""
        if time.time() > self.deadline:
            print(f"time budget reached at step {state.global_step}; saving and stopping")
            control.should_save = True
            control.should_training_stop = True
        return control


def to_text_dataset(rows: list[dict[str, Any]], tokenizer: Any) -> Dataset:
    """Render each chat with the model's own template into a single text column."""
    texts = [
        tokenizer.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=False)
        for r in rows
    ]
    return Dataset.from_dict({"text": texts})


def latest_checkpoint() -> str | None:
    """Return the checkpoint to resume from, if any."""
    if RESUME_FROM:
        return RESUME_FROM
    found = sorted(
        glob.glob(str(CHECKPOINT_DIR / "checkpoint-*")), key=lambda p: int(p.rsplit("-", 1)[1])
    )
    return found[-1] if found else None


def evaluate(model: Any, tokenizer: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Greedy-decode held-out rows; report valid JSON, contract rules and policy agreement."""
    FastLanguageModel.for_inference(model)
    valid = agree = 0
    confusion: dict[str, int] = {}
    for row in rows[:EVAL_N]:
        gold = json.loads(row["messages"][2]["content"])
        prompt = tokenizer.apply_chat_template(
            row["messages"][:2], tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        output = model.generate(**inputs, max_new_tokens=300, do_sample=False)
        text = tokenizer.decode(output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        try:
            answer = json.loads(text)
            ok = (
                answer["recommendation"] in ("approve", "decline", "refer")
                and 0 <= answer["confidence"] <= 1
                and len(answer["reasons"]) >= 1
                and (answer["recommendation"] == "approve" or answer["needs_human"] is True)
                and (answer["needs_human"] or answer["human_question"] is None)
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            ok = False
            answer = {}
        valid += ok
        hit = ok and answer["recommendation"] == gold["recommendation"]
        agree += hit
        key = f"{gold['recommendation']}->{answer.get('recommendation', 'invalid')}"
        confusion[key] = confusion.get(key, 0) + 1
    n = min(EVAL_N, len(rows))
    return {
        "n": n,
        "valid_json_rate": valid / n,
        "policy_agreement": agree / n,
        "gold_to_predicted": confusion,
    }


def main() -> None:
    """Train, save the adapter and run the held-out check."""
    data_dir = find_data_dir()
    train_rows = read_jsonl(data_dir / "train.jsonl")
    val_rows = read_jsonl(data_dir / "val.jsonl")
    test_rows = read_jsonl(data_dir / "test.jsonl")
    print(f"train {len(train_rows)}, val {len(val_rows)}, test {len(test_rows)}")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL, max_seq_length=MAX_SEQ_LENGTH, dtype=None, load_in_4bit=True
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=SEED,
    )

    bf16 = torch.cuda.is_bf16_supported()
    token = hf_token()
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=to_text_dataset(train_rows, tokenizer),
        eval_dataset=to_text_dataset(val_rows, tokenizer),
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        packing=False,
        callbacks=[TimeLimit(MAX_HOURS)],
        args=SFTConfig(
            per_device_train_batch_size=BATCH_SIZE,
            per_device_eval_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            num_train_epochs=EPOCHS,
            learning_rate=LEARNING_RATE,
            warmup_ratio=0.03,
            lr_scheduler_type="linear",
            optim="adamw_8bit",
            weight_decay=0.01,
            fp16=not bf16,
            bf16=bf16,
            logging_steps=10,
            eval_strategy="steps",
            eval_steps=max(SAVE_STEPS * 2, 100),
            save_strategy="steps",
            save_steps=SAVE_STEPS,
            save_total_limit=3,
            seed=SEED,
            output_dir=str(CHECKPOINT_DIR),
            report_to="none",
            push_to_hub=token is not None,
            hub_model_id=HF_REPO or None,
            hub_token=token,
            hub_strategy="every_save",
            hub_private_repo=True,
        ),
    )

    try:
        from unsloth.chat_templates import train_on_responses_only

        trainer = train_on_responses_only(
            trainer, instruction_part=USER_MARKER, response_part=ASSISTANT_MARKER
        )
    except ImportError:
        print("train_on_responses_only unavailable; training on the full text")

    resume = latest_checkpoint()
    print(f"resuming from {resume}" if resume else "starting from the base model")
    trainer.train(resume_from_checkpoint=resume)

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(FINAL_DIR))
    tokenizer.save_pretrained(str(FINAL_DIR))
    print(f"saved final adapter to {FINAL_DIR}")

    results = evaluate(model, tokenizer, test_rows)
    (OUT_DIR / "eval_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
