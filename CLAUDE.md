# Loan Approval Agent (human in the loop)

Hackathon project. Theme: human-in-the-loop agents. Time budget is a few hours, so favor simple, correct, testable code over clever or general code.

## What this is

An AI analyst does the underwriting legwork on a loan application, and a human loan officer steps in only where judgment is needed. The agent extracts applicant data, computes affordability ratios in code, and recommends `approve`, `decline` or `refer`, with every reason tied to a field or metric. A rule-based router then decides whether the case auto-clears, goes back to the applicant for missing information, or lands in a reviewer's queue.

A person is pulled in for: missing or conflicting data, borderline risk, loan amounts above a threshold, and every decline. Nothing is ever auto-rejected.

Every action is written to an audit log. Every reviewer override is stored with its reason in an override log. We log overrides but do not retrain on them in this build.

## Pipeline

```
submit -> extraction (LLM) -> completeness check (code) -> metrics (code) -> reasoner (LLM) -> router (rules)
                                     |                                                                |
                                     missing field -> needs_info                                      |
                          needs_info <- applicant replies -> analyzing again
                          pending_review -> reviewer approves / rejects / overrides -> decided
                          auto_cleared -> decided
```

The completeness check (`check_completeness` in `router.py`) runs right after extraction, before metrics. If any required field (`annual_income`, `loan_amount`, `annuity`, `goods_price`, listed in `REQUIRED_FIELDS` in `contract.py`) is missing, the pipeline sets `needs_info` with a `human_question` naming the missing fields and skips metrics and the reasoner. `ReasonerInput` also rejects incomplete fields as a safety net.

Allowed status transitions live in `ALLOWED_TRANSITIONS` in `status.py`; every change goes through `transition(current, new)`, which raises `InvalidTransition` on an illegal move. `decided` is terminal.

Status enum (single source of truth, see `api/app/models/status.py`):
`submitted`, `analyzing`, `needs_info`, `pending_review`, `auto_cleared`, `decided`.

Reasoner output contract (see `api/app/models/contract.py`):

```json
{
  "recommendation": "approve | decline | refer",
  "confidence": 0.0,
  "reasons": ["short reason citing a field or metric"],
  "needs_human": true,
  "human_question": "specific question, or null"
}
```

Validation rules, enforced by `ReasonerOutput` (model output that breaks them counts as invalid JSON under hard rule 7):

- `confidence` is between 0 and 1.
- `reasons` has at least one entry.
- `needs_human` must be true whenever `recommendation` is not `approve`.
- `human_question` must be null when `needs_human` is false.

Router rules, evaluated in this order:

1. Missing required field (caught by the completeness check before metrics), or stated income differs from the document by more than the tolerance: `needs_info`.
2. Loan amount above the high-amount cutoff: `pending_review`.
3. Recommendation is `decline` or `refer`: `pending_review`.
4. Confidence below the threshold: `pending_review`.
5. Otherwise: `auto_cleared`.

All thresholds live in one config module as named constants. No magic numbers in logic.

## Architecture and ownership

| Area | Stack | Owner |
| --- | --- | --- |
| Agent API | FastAPI, Pydantic, MCP server | Alyan |
| Schema, contract, status enum, seed data | Postgres (Supabase), SQL | Alyan |
| Frontend | Next.js, TypeScript, Supabase realtime | Friend |
| Fine-tuning, eval, model serving | Unsloth QLoRA, GGUF, OpenAI-compatible endpoint | Friend |
| Supabase project setup, deployment | clouds.alternatefutures.ai | Friend |

Do not change the JSON contract, the status enum or an endpoint shape without telling the other person first. Those are the only things we both depend on.

Endpoints:

- `POST /applications` creates an application and starts the pipeline.
- `POST /applications/{id}/reply` carries the applicant's answer to a `human_question`.
- `POST /applications/{id}/decision` carries approve, reject or override. A reason is required for reject and override.
- Queue and status reads go straight to Supabase realtime, not through the API.

MCP tools exposed by the agent: `get_application`, `compute_metrics`, `request_info`, `flag_for_review`, `log_event`.

## Repo layout

```
api/
  pyproject.toml       deps and ruff, mypy, pytest config
  app/
    main.py            FastAPI app and route registration
    config.py          settings from env, router thresholds
    routes/            thin HTTP handlers, no business logic
    agent/
      extraction.py    documents and form -> structured fields
      metrics.py       ratios, pure functions
      reasoner.py      the single function that calls the model
      router.py        routing rules, pure function
      pipeline.py      orchestrates the steps and status transitions
    mcp/server.py      MCP server and tool definitions (mcp 2.x, MCPServer)
    models/            contract.py (fields, metrics, reasoner I/O), status.py, application.py (raw input)
    db/                client.py (Supabase client), audit.py (event and override writers)
  tests/
  seed/                seeded demo applicants
  Dockerfile
web/                   Next.js app
ml/                    data prep, training, eval scripts
db/schema.sql
```

## Commands

API commands assume the venv in `api/.venv` is active. Env vars are read from `.env` at the repo root (see `.env.example`).

```
# API setup (once, from the repo root)
cd api
python -m venv .venv
.venv\Scripts\activate          # Windows; on macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

# API
cd api && uvicorn app.main:app --reload
cd api && pytest
cd api && ruff check . && ruff format --check . && mypy app

# Web
cd web && npm run dev
cd web && npm run lint && npm run typecheck
```

Run lint, types and tests before every commit. If a command above does not exist yet, add it rather than skipping the check.

## Hard rules

These come from the product, not from taste. Do not work around them.

1. Arithmetic is code, never the LLM. Ratios, sums and comparisons are computed in `metrics.py` and passed to the model as inputs.
2. The router is rules, not the model. Escalation must be explainable and testable. The model recommends, the router decides the path.
3. Never auto-reject. A `decline` recommendation always goes to `pending_review`.
4. Protected attributes never reach a prompt, a feature or a training row: gender, age or birth date, family status. Drop them in data prep and again at prompt-build time.
5. Every state change writes an audit event. The audit log is append-only: no updates, no deletes.
6. A reject or an override without a reason is a validation error.
7. If the model errors, times out or returns invalid JSON, retry once, then fall back to `refer` with `needs_human = true`. Never fall back to `approve`.
8. Secrets come from environment variables. Never commit keys or `.env`. Keep `.env.example` current.

## Code quality standards

### Python

- Type hints on every function signature. Code passes `mypy` with no ignores unless commented with the reason.
- Pydantic models for every boundary: request bodies, the reasoner contract, DB rows, MCP tool inputs. Validate LLM output with the contract model, never by poking at raw dicts.
- Keep functions small and single-purpose. `metrics.py` and `router.py` are pure functions with no I/O, so they are trivial to test.
- Route handlers stay thin: parse, call the pipeline, return. Business logic lives in `agent/`.
- Status transitions go through one function that rejects illegal moves (for example `decided` back to `analyzing`). Do not set status strings inline.
- All model access goes through `reasoner.py` using an OpenAI-compatible client configured by `base_url` and model name from env. Swapping the prompted API model for the fine-tune must be an env change only.
- Use `logging` with structured context (application id, status), not `print`. Never log full applicant documents or personal data.
- Raise specific exceptions and handle them at the route layer. No bare `except`, no swallowed errors.
- No dead code, no commented-out blocks, no TODOs without an owner and a reason.
- Format and lint with `ruff`. Do not hand-format around it.

### TypeScript (web)

- `strict` mode on. No `any`; use `unknown` and narrow.
- Types for the contract and status enum mirror the API models exactly. If one changes, change both in the same PR.
- Server state comes from Supabase realtime or typed fetchers, not scattered `fetch` calls in components.
- Show loading, empty and error states for every list and every action. The reviewer queue is what judges watch, so it must never look broken.

### Testing

- Unit tests are required for `metrics.py` and `router.py`: normal cases, boundaries, missing values.
- Contract tests: valid and invalid reasoner output, including the retry and fallback path.
- One end-to-end test per seeded demo applicant, asserting the final status and that the right events were logged.
- Fix the code, not the test, unless the test encoded a wrong requirement.

### Process

- Small commits with imperative messages (`Add payment-to-income metric`). One concern per commit.
- Do not touch the other person's area without asking. Open a short note instead.
- Prefer boring solutions. No new framework or orchestration library without a clear reason; the status column is the state machine.
- When something is cut for time, record it in the README under "Known limits" so the pitch stays honest.

## Domain notes (Home Credit data)

- Source: `application_train.csv` only. Sample 3k to 5k rows stratified on `TARGET`; train on about 2k labeled examples.
- `DAYS_EMPLOYED == 365243` is a sentinel for pensioners and the unemployed. Convert to null plus a flag.
- Day columns are negative (days before application). Flip the sign when converting to years.
- Payment-to-income is `AMT_ANNUITY / (AMT_INCOME_TOTAL / 12)`. The main table has no existing-debt figure, so this is payment-to-income, not true DTI. Say so in the pitch.
- Currency is unspecified. Write thresholds as ratios or percentiles, not absolute amounts.
- `EXT_SOURCE_1/2/3` are heavily null. Treat null as a real "needs more information" signal, not something to impute silently.
- Policy labels (approve, decline, refer) come from an explicit threshold function. Say plainly that the model learns a distilled policy, not real underwriter judgment.

## Working with Claude in this repo

- Read this file and the contract and status files before changing pipeline code.
- Before adding a feature, check it against the hard rules above. If it conflicts, say so instead of working around it.
- Prefer editing existing modules over adding new ones. Keep diffs small and reviewable.
- When asked to "make it work", fix the root cause. Do not loosen validation, catch-all exceptions or skip tests to get a green run.
- If a requirement is ambiguous and the answer changes the contract, status flow or router rules, ask. Otherwise pick the simplest option, say which, and continue.
