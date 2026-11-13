# Daily Briefing — AI-powered personalized news

> Less noise. More important stories. A little intelligence and a little humour.

A curated daily top-10 news briefing (Technology, Government & Policy, Crypto, Stocks & Markets) with per-user
category muting, ranked and de-duplicated stories, publisher images, Gemini-written witty headlines (the original is always shown),
and a server-enforced **Fetch More** limit (2 extra batches of 10 → max 30 stories/day).

```
frontend/        React + TS + Vite + Tailwind (Apple News-inspired editorial UI, dark/light)
backend/         Python 3.12 Lambda code: shared/ (logic), functions/ (handlers), tests/, local/ (dev server)
infrastructure/  AWS SAM template (DynamoDB x2, Lambda x4, HTTP API, EventBridge, S3+CloudFront, alarms, budget)
scripts/         deploy.sh, emergency-shutdown.sh
docs/            architecture, database, API, deployment (+Gemini setup, env vars, sources), cost control
```

## Quick start (local, no AWS)
```bash
cd backend && GEMINI_API_KEY=optional python -m local.server        # API on :8787, real RSS ingestion at startup
cd frontend && cp .env.example .env && npm install && npm run dev   # http://localhost:5173
```
Run tests: `cd backend && python -m unittest discover -s tests -t .` and `cd frontend && npm test`.
Deploy to AWS: see `docs/deployment.md`.

## Honest status — what was and was not verified
| Area | Status |
|---|---|
| Backend logic (RSS parsing, dedupe, ranking, allocation/muting, Fetch More quota incl. 12-thread race, idempotency, TTL filtering, Gemini retry/guardrails/budget, API, ingestion with failing source) | **39 tests, 37 pass, 2 skipped** (DynamoDB integration test needs `boto3`+`moto`, not installable in the build sandbox) |
| `DynamoRepository`, `template.yaml`, deploy scripts | **Written, not executed** (no AWS access / network). Expressions mirror the tested in-memory repository. Run the integration test with moto before deploying. |
| Frontend | **Written, not built or tested** (no npm registry access in the build sandbox). A TypeScript syntax pass found no syntax errors; type-checking, vitest suites (20+ tests written) and Lighthouse must be run by you: `npm install && npm run build && npm test`. Mobile layout is untested (jsdom can't verify layout). |
| Live RSS URLs, Gemini model name/pricing | **Not verified** (no network). Check `/api/health` after the first ingestion; set `GEMINI_MODEL` to a model your key can use. |

## Decisions worth knowing
- **HTTP API (v2)** instead of REST API: cheaper, same REST-style routes, built-in CORS/throttling.
- **Identity**: anonymous HMAC-signed bearer token (not authentication). Settings sync across devices through a secret "sync code"
  (the token). Swap in Cognito if you need real accounts.
- **Briefing pool** is the per-day DynamoDB GSI (`day`, `score`) rather than a separate DailyBriefings table: ranking is computed at ingestion,
  per-user selection is a pure function over the cached pool (first 10 = briefing, rest = reserve), per-user delivery state lives in `USAGE#<day>`.
- **Google News RSS has no images or real summaries.** Images/summaries come from direct publisher feeds (media tags); Google items give
  coverage/credibility signals and merge into the same story. Images are hotlinked (never copied), flagged `unverified`, and the UI falls back cleanly on load errors.
  Optional Open Graph lookup (`ENABLE_OG_FETCH=true`) is off by default (robots.txt + SSRF-guarded).
- A Gemini AI Pro subscription does **not** include API quota. Get an API key and check its pricing/free tier in Google AI Studio; the app caps calls with `GEMINI_DAILY_CALL_CAP` and works with no key (original headlines).
- After a user's first Fetch More, muting a category hides its already-delivered stories but does not refill them (it would silently spend the quota).
