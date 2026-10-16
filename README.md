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

## Known limits

- Documents are accepted as text. PDF and image upload with OCR is not built.
- Protected attributes are dropped from the form and from prompts, but document text is passed to the extraction model as written, so a document that mentions age or gender reaches that one call. The extraction output is filtered to the allowed fields, and the reasoner never sees document text.
- Auto-cleared applications stay in `auto_cleared`; nothing moves them to `decided` unless a reviewer acts.
- `HIGH_LOAN_AMOUNT_CUTOFF` is a placeholder until `api/seed/prepare_home_credit.py` has been run on `application_train.csv` to read off the percentile.
