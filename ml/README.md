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

## Serve the model on Alternate Clouds

Build an Ollama image with the fine-tuned model baked in, push it, and run it as its own service. The image is built on your machine because the `.gguf` (about 2 GB) is not in git.

1. Put the two files from the export notebook in `ml/serve/`: the `.gguf` file and `Modelfile` (the Modelfile's `FROM` line must name that `.gguf`).
2. Log in to GitHub's registry with a personal access token that has the `write:packages` scope:
   `echo <token> | docker login ghcr.io -u <github-username> --password-stdin`
3. Build and push with a version tag (the platform refuses `latest`):
   ```
   docker build -t ghcr.io/<owner>/cosign-model:0.1.0 ml/serve
   docker push ghcr.io/<owner>/cosign-model:0.1.0
   ```
4. Make the package public (GitHub -> Packages -> cosign-model -> Package settings -> Change visibility). The platform cannot pull private images. This publishes the model weights, so only do it if you are comfortable sharing them.
5. Check GPU availability and price: `acc regions --gpu t4` (try other models if none).
6. Deploy it:
   ```
   acc services create --kind docker --image ghcr.io/<owner>/cosign-model:0.1.0 --port 11434 --name cosign-model \
     --gpu --storage 20Gi --memory 8Gi -y
   ```
7. Wait for `acc services list` to show it running, then test:
   `curl https://<model-slug>-app.alternatefutures.ai/v1/models` should list `cosign`.
8. Point the API at it: `acc services env set cosign-api MODEL_BASE_URL https://<model-slug>-app.alternatefutures.ai/v1`, `MODEL_NAME cosign` and `MODEL_API_KEY ollama`, then `acc services deploy`.

The model endpoint has no authentication, so anyone with the URL can use your GPU. Keep the URL private, and stop or delete the service after the demo (`--stop-hours` on create can auto-stop it).
