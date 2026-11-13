# Cost and resource control

**Services that can incur charges**: Lambda (requests, duration), API Gateway HTTP API (requests), DynamoDB on-demand (reads/writes/storage), CloudFront (requests/egress), S3 (storage/requests), CloudWatch (logs, alarms), SNS email (negligible), SSM standard parameters (no charge), AWS Budgets (first budgets free), and **Gemini API** (billed by Google, separate from AWS). Check current pricing and free-tier eligibility for your account/region before deploying; this project does not assume permanent credits.

**Built-in controls**
- Ingestion is one scheduled Lambda (`IngestSchedule`, default hourly), reserved concurrency 1, 120 s timeout; users never trigger RSS fetches. Conditional GET (ETag/Last-Modified) where publishers support it.
- API Lambda: reserved concurrency 10, 15 s timeout, 256 MB; HTTP API throttle 10 rps / burst 20.
- DynamoDB: on-demand, no scans, TTL on all expiring data, in-Lambda 60 s pool cache, small items.
- Gemini: one batched call per 10 headlines, default tone only at ingestion, cached per article+tone, `GEMINI_DAILY_CALL_CAP` (atomic global counter), per-run cap, per-user rewrite quota, token limit, timeout, fail-fast.
- Alarms + monthly **AWS Budget alerts** (80% forecast, 100% actual). **Budgets only notify; they are not a hard cap.**

## Emergency shutdown
1. `./scripts/emergency-shutdown.sh` sets reserved concurrency to 0 on all functions (API, ingestion, backfill, cleanup): traffic and Gemini spend stop within seconds; data is kept.
2. Revoke/rotate the Gemini key in Google AI Studio if abuse is suspected; optionally `aws events disable-rule` / delete the stack (`aws cloudformation delete-stack`, after emptying the site bucket).
3. Resume with `./scripts/emergency-shutdown.sh restore`, then `sam deploy` to re-apply template limits.
