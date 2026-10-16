# ml

Owner: Friend. The fine-tune pipeline below was set up by Alyan on `alyan-branch`.

Fine-tunes the reasoner (Qwen2.5-3B-Instruct, Unsloth QLoRA) on labels from the explicit policy in `api/app/agent/policy.py` (see `POLICY.md`). The model learns a distilled policy, not underwriter judgment.

## Build the data (local, from the repo root)

```
cd api
python seed/prepare_home_credit.py PATH/TO/application_train.csv --size 8000 --out PATH/TO/sample_8000.jsonl
.venv\Scripts\python ..\ml\build_dataset.py PATH/TO/sample_8000.jsonl
```

This writes `ml/kaggle_bundle/` (git-ignored, because it derives from competition data): `train.jsonl`, `val.jsonl`, `test.jsonl` and `train.py`. Every row uses the exact system and user prompt the API sends, so swapping in the fine-tune is an env change only. If the prompt, policy or thresholds change, rebuild the data and retrain.

## Train on Kaggle

1. Upload the `ml/kaggle_bundle/` folder as a private Kaggle dataset named `cosign-finetune`.
2. Import `ml/kaggle_finetune.ipynb` as a new notebook. Add the dataset, set GPU to T4, Internet on.
3. Optional: add a Kaggle secret `HF_TOKEN` and set `HF_REPO` in the settings cell to push every checkpoint to Hugging Face.
4. Save Version, Save & Run All.

Checkpoints are saved every 50 steps to `/kaggle/working/outputs/checkpoint-*` (last 3 kept). The run stops itself after `MAX_HOURS` (10.5) and writes `final_adapter/` and `eval_results.json`. To continue a stopped run, add the checkpoint as a dataset and set `RESUME_FROM`.
