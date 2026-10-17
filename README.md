# Loan Approval Agent (human in the loop)

An AI analyst does the underwriting legwork on a loan application, and a human loan officer steps in only where judgment is needed. The agent extracts applicant data, computes affordability ratios in code, and recommends `approve`, `decline` or `refer`, with every reason tied to a field or metric. A rule-based router then sends the case to auto-clear, back to the applicant for missing information, or to a reviewer's queue. Nothing is ever auto-rejected, every action is written to an append-only audit log, and every reviewer override is stored with its reason.

## Running locally

Copy `.env.example` to `.env` at the repo root and fill in the values.

```
# API setup (once)
cd api
python -m venv .venv
.venv\Scripts\activate          # Windows; on macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

# API (from api/, with the venv active)
uvicorn app.main:app --reload
pytest
ruff check . && ruff format --check . && mypy app

# Web
cd web && npm run dev
cd web && npm run lint && npm run typecheck
```

The web commands work once the Next.js app has been created in `web/`.

## Running without credentials

Set `USE_FAKES=true` in `.env`. The API then uses an in-memory store and a rule-based stand-in for the model, so the whole flow runs offline. Demo applicants are in `api/seed/demo_applicants.json`; each one exercises a different routing path and is covered by `api/tests/test_pipeline.py`.

## API

All three endpoints return immediately; progress shows up in Supabase realtime.

- `POST /applications` takes `{form, documents[]}` and returns `202 {id, status}`. `form` fields are all optional numbers (`annual_income`, `loan_amount`, `annuity`, `goods_price`, `years_employed`, `ext_source_1..3`). Unknown keys are dropped. `documents[]` is `{name, kind, text}`.
- `POST /applications/{id}/reply` takes `{answer, corrections}` while status is `needs_info`. `corrections` holds corrected field values (for example `{"annuity": 2500}`). Returns `202`; `409` if the application is not waiting.
- `POST /applications/{id}/decision` takes `{reviewer_id, action, final_decision?, reason?}`. `action` is `approve`, `reject` or `override`. `reason` is required for reject and override; `final_decision` (`approve` or `reject`) is required for override only. Approving a decline, or rejecting an approve, must be an override. Returns `409` if the case is not awaiting a decision.

Table changes in `db/schema.sql` the web app should know about: `applications.input`, `human_question` (shown to the applicant while `needs_info`), `final_decision`, `decision_reason`, `decided_by`, and `override_log.reviewer_id`.

## Run everything locally (demo)

Three processes, all on one machine. The database is the hosted Supabase project from `.env`.

1. **Model.** Download a llama.cpp build for your OS from https://github.com/ggml-org/llama.cpp/releases (on Windows, the `win-vulkan-x64` zip works on any GPU) and run it on the fine-tuned `.gguf`:
   ```
   llama-server -m Qwen2.5-3B-Instruct.Q4_K_M.gguf --alias cosign --host 127.0.0.1 --port 8081 -c 4096 --parallel 2 -ngl 99 --chat-template chatml
   ```
   Drop `-ngl 99` to run on CPU. Check it with `curl http://127.0.0.1:8081/health`.
2. **API.** In `.env` set `USE_FAKES=false`, `MODEL_BASE_URL=http://127.0.0.1:8081/v1`, `MODEL_NAME=cosign`, `MODEL_API_KEY=local`, `CORS_ORIGINS=http://localhost:3000`, plus the Supabase values. Then from `api/` with the venv active: `uvicorn app.main:app --port 8000`.
3. **Web.** In `.env` set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` and the two `NEXT_PUBLIC_SUPABASE_*` values. Then from `web/`: `npm run dev`. Open http://localhost:3000.

With a GTX 1060 the model answers in about 2 seconds once warm. The first request after startup is slower.

## Deployment checklist

Target platform: Alternate Clouds (https://clouds.alternatefutures.ai, docs at https://docs.alternatefutures.ai). It deploys container images with the `acc` CLI, gives each service an automatic `https://<slug>-app.alternatefutures.ai` URL, and has a $5 trial credit. It does not build from a Dockerfile or compose file for Docker services, so the API image is built and pushed to a registry first. `docker-compose.yml` is for running the API locally only.

**1. Database (done once)**
- [ ] Run `db/schema.sql` in the Supabase SQL editor.
- [ ] Confirm `applications` is in the `supabase_realtime` publication.
- [ ] Add a read-only row-level-security policy for the anon role on `applications`, so the web app can read the queue.
- [ ] Rotate the service role key if it was ever pasted into a chat or committed.

**2. Model**
- [ ] Download the best checkpoint or `final_adapter` from Kaggle and check `eval_results.json`: `valid_json_rate` near 1.0 and `policy_agreement` above 0.9.
- [ ] Run the export notebook (`ml/export_gguf.py`) and download the `.gguf` and `Modelfile` from its output.
- [ ] Serve it with Ollama: `ollama create cosign -f Modelfile`, then `ollama serve`. Test with `curl http://localhost:11434/v1/chat/completions`.
- [ ] Deploy the model as its own GPU service on the platform: bake the `.gguf` into an Ollama image and push it, as described in "Serve the model on Alternate Clouds" in `ml/README.md`. To test locally first, run `ollama create cosign -f Modelfile` and point `MODEL_BASE_URL` at `http://localhost:11434/v1`.
- [ ] Fallback: point the three model variables at any OpenAI-compatible API model. The prompt is the same.
- [ ] The fine-tune was trained only on the reasoner task. Extraction uses the same model variables, so with the fine-tune it may fail to return fields and the API falls back to form values only; income-mismatch checks then do not run. Use a prompted model if documents matter in the demo.

**3. Build and publish the API image**
- [ ] Push a version tag: `git tag v0.1.0 && git push origin v0.1.0`. The workflow in `.github/workflows/api-image.yml` runs lint, types and tests, then publishes `ghcr.io/<owner>/cosign-api:0.1.0`.
- [ ] Make the package public (GitHub -> Packages -> cosign-api -> Package settings -> Change visibility). The platform cannot pull private images. The image contains no secrets: `.env` is excluded and every setting comes from environment variables.
- [ ] Always deploy a versioned tag. The platform refuses `latest` and `main`.
- [ ] To build by hand instead: `docker build -t ghcr.io/<owner>/cosign-api:0.1.0 api` and `docker push` it.

**4. Deploy on Alternate Clouds**
- [ ] `npm install -g @alternatefutures/acc`, then `acc login` and `acc projects create --name cosign`.
- [ ] Create the service. Replace the values; `MODEL_BASE_URL` ends in `/v1`:
  ```
  acc services create --kind docker --image ghcr.io/<owner>/cosign-api:0.1.0 --port 8000 --name cosign-api \
    --env USE_FAKES=false \
    --env SUPABASE_URL=https://<project>.supabase.co \
    --env SUPABASE_KEY=<service role key> \
    --env MODEL_BASE_URL=<model url>/v1 --env MODEL_NAME=cosign --env MODEL_API_KEY=ollama \
    --env CORS_ORIGINS=https://<web-slug>-app.alternatefutures.ai \
    -y
  ```
- [ ] Add `--confidential` to run on a TEE. Services run on third-party providers, who start the container with your environment variables, so the Supabase service role key is visible to them. Use `--confidential` if your plan allows it, and rotate the key after the demo.
- [ ] `acc services list` shows the status and public URL. `acc services logs cosign-api --tail 100` shows logs.
- [ ] `curl https://<slug>-app.alternatefutures.ai/health` returns `{"status":"ok"}`.
- [ ] To change a variable: `acc services env set cosign-api KEY VALUE`, then `acc services deploy`. To ship a new version: `acc services deploy --image ghcr.io/<owner>/cosign-api:0.1.1`.
- [ ] Submit one demo applicant from `api/seed/demo_applicants.json` to `POST /applications` and watch it move through the statuses in Supabase.
- [ ] If a deployment does not start within about 25 minutes the platform marks it failed and does not charge. Check `acc deployments --service <id> --status failed` and `acc regions`, and try another region.

**5. Web app** (friend)
- [ ] Deploy it the same way as an image. Set its API base URL to the API's public URL and use the Supabase URL and anon key. Never give it the service role key.
- [ ] Put the web app's public origin in the API's `CORS_ORIGINS`, then redeploy the API.

**Deploy one service per commit.** Alternate Clouds names a build-from-GitHub image after the repo and the commit only, not the service or folder. If two services (api, web, model) build from the same commit they overwrite each other's image, and a service can end up running another service's app (the API once served the Next.js app, so `/health` returned 502). Give each service its own commit before deploying it: push a small commit, deploy one service, then repeat. Deploy one service at a time, because two simultaneous deployments can fail with an on-chain "code 32" error; retrying fixes it.

**6. Before the demo**
- [ ] Make sure the account has credit for at least one hour of running cost; the platform will not place a deployment without it.
- [ ] Delete test rows from `applications` if you want a clean queue. The audit and override logs are append-only by design and cannot be cleared.
- [ ] Run each demo applicant once and confirm the expected status.
- [ ] Have the prompted-model fallback values ready in case the model server is down.

## Known limits

- Documents are accepted as text. PDF and image upload with OCR is not built.
- Protected attributes are dropped from the form and from prompts, but document text is passed to the extraction model as written, so a document that mentions age or gender reaches that one call. The extraction output is filtered to the allowed fields, and the reasoner never sees document text.
- Auto-cleared applications stay in `auto_cleared`; nothing moves them to `decided` unless a reviewer acts.
- The risk policy (`POLICY.md`) is frozen as percentiles of the Home Credit sample. Payment-to-income is about 2 for a typical real applicant, so ratio cutoffs must stay percentile-based.
