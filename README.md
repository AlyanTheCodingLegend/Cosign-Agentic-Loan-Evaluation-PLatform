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

## Deployment checklist

Everything runs on one host: the API, the web app and (optionally) the model server. Supabase is hosted.

**1. Database (done once)**
- [ ] Run `db/schema.sql` in the Supabase SQL editor.
- [ ] Confirm `applications` is in the `supabase_realtime` publication.
- [ ] Rotate the service role key if it was ever pasted into a chat or committed, then use the new one below.

**2. Model**
- [ ] Download the best checkpoint or `final_adapter` from Kaggle (or from your Hugging Face repo) and check `eval_results.json`: `valid_json_rate` near 1.0 and `policy_agreement` above 0.9.
- [ ] Export it: in the Kaggle session run `ml/export_gguf.py`, then download the `.gguf` file and `Modelfile` from `/kaggle/working/gguf/`.
- [ ] Serve it with Ollama on the laptop or host: `ollama create cosign -f Modelfile`, then `ollama serve`. Test with `curl http://localhost:11434/v1/chat/completions`.
- [ ] Expose it over HTTPS if the API is on another machine (for example a Cloudflare tunnel or Tailscale Funnel). Note the public URL.
- [ ] Fallback if the fine-tune is not ready or misbehaves: point the three model variables at any OpenAI-compatible API model instead. The prompt is the same, so nothing else changes.
- [ ] The fine-tune was trained only on the reasoner task. Extraction uses the same model variables, so with the fine-tune it may fail to return fields and the API falls back to form values only; income-mismatch checks then do not run. Use a prompted model if documents matter in the demo.

**3. API environment** (in `.env` at the repo root; it is git-ignored and not copied into the image)
- [ ] `USE_FAKES=false`
- [ ] `SUPABASE_URL` and `SUPABASE_KEY` (service role key; keep it server-side only)
- [ ] `MODEL_BASE_URL` (ends in `/v1`), `MODEL_NAME` (for example `cosign`) and `MODEL_API_KEY` (any non-empty text for Ollama)
- [ ] `CORS_ORIGINS` set to the web app's public origin, for example `https://app.example.com` (comma separated for more than one)

**4. Run the API**
- [ ] `docker compose up --build -d` from the repo root.
- [ ] `curl http://localhost:8000/health` returns `{"status":"ok"}`.
- [ ] From `api/` with the venv active, run `python scripts/smoke_supabase.py`. It checks the database path with the fake model.
- [ ] Submit one demo applicant from `api/seed/demo_applicants.json` to `POST /applications` and watch it move through the statuses in Supabase.
- [ ] Put HTTPS in front of port 8000 (reverse proxy or the host's own TLS) so the browser can call it from an HTTPS page.

**5. Web app** (friend)
- [ ] Set its API base URL and the Supabase URL and anon key. Never give it the service role key.
- [ ] Add the `applications` table to Supabase row-level security policies for the anon role (read only), since the queue reads directly from Supabase.

**6. Before the demo**
- [ ] Delete test rows from `applications` if you want a clean queue. The audit and override logs are append-only by design and cannot be cleared.
- [ ] Run each demo applicant once and confirm the expected status.
- [ ] Have the prompted-model fallback values ready in case the model server is down.

## Known limits

- Documents are accepted as text. PDF and image upload with OCR is not built.
- Protected attributes are dropped from the form and from prompts, but document text is passed to the extraction model as written, so a document that mentions age or gender reaches that one call. The extraction output is filtered to the allowed fields, and the reasoner never sees document text.
- Auto-cleared applications stay in `auto_cleared`; nothing moves them to `decided` unless a reviewer acts.
- The risk policy (`POLICY.md`) is frozen as percentiles of the Home Credit sample. Payment-to-income is about 2 for a typical real applicant, so ratio cutoffs must stay percentile-based.
