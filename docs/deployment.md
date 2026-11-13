# Deployment, configuration and local development

## Prerequisites
AWS account + CLI configured, AWS SAM CLI, Node 20+, Python 3.12, a Gemini API key.

## 1. Gemini API setup
A Gemini AI Pro/Google One subscription does **not** grant API usage. Create a key in Google AI Studio, check that project's free-tier limits / billing and pricing for your chosen model, then:
```bash
aws ssm put-parameter --name /news/gemini-api-key --type SecureString --value '<KEY>'
aws ssm put-parameter --name /news/session-secret --type SecureString --value "$(openssl rand -hex 32)"
```
Model and limits are configurable (`GEMINI_MODEL`, `GEMINI_DAILY_CALL_CAP`, …). No key → the product works with original headlines only.

## 2. Deploy
```bash
./scripts/deploy.sh you@example.com                      # builds, deploys stack, uploads frontend
ALLOWED_ORIGIN=https://<cloudfront-domain> ./scripts/deploy.sh you@example.com   # 2nd run: lock CORS to the site
```
Confirm the SNS email subscription. Trigger the first ingestion: `aws lambda invoke --function-name <IngestionFunction> /dev/null`, then open `GET /api/health`.

## 3. Environment variables (Lambda; defaults in `shared/config/settings.py`)
| Variable | Default | Purpose |
|---|---|---|
| ARTICLES_TABLE / USERS_TABLE | set by template | table names |
| BRIEFING_TIMEZONE | UTC | defines the daily cycle (e.g. `Asia/Kolkata`) |
| BRIEFING_SIZE / FETCH_MORE_SIZE / MAX_FETCH_MORE | 10 / 10 / 2 | story counts and Fetch More cap |
| RETENTION_DAYS | 7 | article/rewrite TTL |
| MAX_ARTICLE_AGE_HOURS / MIN_STORY_SCORE | 30 / 0.15 | freshness and quality floor |
| POOL_LIMIT | 120 | stories read per day pool |
| FEED_TIMEOUT_SECONDS / FEED_RETRIES / INGEST_WORKERS | 8 / 3 / 4 | ingestion bounds |
| GEMINI_MODEL / GEMINI_KEY_PARAM / GEMINI_API_KEY | gemini-2.5-flash / SSM name / (local only) | model and key |
| GEMINI_DAILY_CALL_CAP / GEMINI_CALLS_PER_RUN / REWRITE_TOP_N / REWRITE_BATCH_SIZE | 150 / 3 / 30 / 10 | Gemini budget |
| GEMINI_MAX_OUTPUT_TOKENS / GEMINI_TEMPERATURE / GEMINI_TIMEOUT_SECONDS / GEMINI_THINKING_BUDGET | 800 / 0.9 / 12 / 0 (empty = omit) | generation settings |
| REWRITE_USER_DAILY_LIMIT / SESSIONS_PER_IP_DAILY | 20 / 20 | abuse limits |
| ENABLE_OG_FETCH / OG_FETCH_PER_RUN | false / 15 | optional Open Graph image lookup |
| ALLOWED_ORIGINS / SESSION_SECRET(_PARAM) | origin / SSM name | CORS (also at API Gateway) and token signing |
Frontend: `VITE_API_BASE_URL`.

## 4. News source configuration
Edit `backend/shared/config/sources.json` (id, `type` google|direct, `category`, `publisher` for direct feeds, `url` https RSS 2.0). Credibility priors live in `config/publishers.py`.
Feed URLs were not verified from the build sandbox: check `/api/health` for sources with `status: error`. Atom-only feeds are not supported. Only allow-listed feeds in this file are ever fetched (no user-supplied URLs → no SSRF surface).

## 5. Local development
`python -m local.server` (in-memory repo, real ingestion every 30 min, dev session secret) + `npm run dev`. Backend tests need only the stdlib; add `boto3 moto` to run the DynamoDB integration test.

## 6. Operations
Logs are JSON in CloudWatch (`ingestion_done`, `feed_failed`, `gemini_failed`, `gemini_budget_stop`). Alarms: API errors/throttles, ingestion errors, DynamoDB throttles.
