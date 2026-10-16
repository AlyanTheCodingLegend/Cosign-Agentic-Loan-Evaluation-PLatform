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

## Known limits
