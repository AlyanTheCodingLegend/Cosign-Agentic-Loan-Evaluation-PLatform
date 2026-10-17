# web

Owner: Friend.

Next.js 16 (App Router, TypeScript strict, Tailwind v4) for the applicant portal and the reviewer queue.

## Screens

| Route | Who | What |
| --- | --- | --- |
| `/` | everyone | Landing page and pipeline overview |
| `/apply` | applicant | Loan form, `POST /applications` |
| `/applications/[id]` | applicant | Live status, answers a `human_question` via `POST /applications/{id}/reply` |
| `/review` | loan officer | Realtime queue with tabs per status |
| `/review/[id]` | loan officer | Recommendation, metrics, fields, audit trail, approve/reject via `POST /applications/{id}/decision` |

## Data

- `lib/types.ts` mirrors `api/app/models/status.py`, `contract.py` and `db/schema.sql`. Change them together.
- `lib/data.ts` picks the data source. `lib/live.ts` reads Supabase (realtime on `applications`) and writes through the API.
- `lib/demo.ts` is an in-memory store with the seeded demo paths. It is used when `NEXT_PUBLIC_API_URL`,
  `NEXT_PUBLIC_SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_ANON_KEY` is missing, and a banner says so.
- Env vars are read from the repo-root `.env` (see `next.config.ts` and `.env.example`).

## Commands

```
npm run dev
npm run lint && npm run typecheck
npm run build
```
