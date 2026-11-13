# Architecture

```mermaid
flowchart LR
  EB[EventBridge schedule] --> ING[Ingestion Lambda]
  ING -->|fetch RSS, bounded concurrency| RSS[(Google News + publisher RSS)]
  ING -->|conditional puts, scores| ART[(Articles table + PoolByScore GSI)]
  ING -->|batched rewrites, daily budget| GEM[Gemini API]
  ING --> ART
  EB2[Daily schedule] --> CLN[Cleanup Lambda] --> ART
  FE[React app on CloudFront + S3] --> APIGW[HTTP API: throttled] --> API[API Lambda]
  API --> ART
  API --> USR[(Users table: prefs, usage, quotas)]
  API -->|on-demand tone rewrite, quota+budget| GEM
  SSM[SSM SecureString: Gemini key, session secret] -.-> API
  SSM -.-> ING
  CW[CloudWatch alarms + AWS Budget] --> SNS[Email]
```

**Principles**: ingestion never depends on user traffic; users only read the shared pool; Gemini output is cached once per article+tone;
every external dependency can fail without breaking the feed.

## Code map (`backend/shared`)
`ingestion/` rss, dedupe, ranking, fetcher, og, pipeline · `briefing/` selection (pure), service (use-cases) · `ai/` gemini client, guardrails, personalities, headlines ·
`repositories/` dynamo + memory (identical semantics) · `config/` settings, categories, publishers, sources.json · `validation.py` · `secrets.py`.

## Ranking
score = 0.30 recency (12h half-life) + 0.20 publisher credibility + 0.20 cross-publisher coverage (distinct publishers, log-scaled) + 0.20 impact keywords + 0.10 category relevance.
Near-duplicate headlines (token Jaccard/overlap ≥ 0.6) merge into the most credible version; others become `alsoReportedBy`.

## Selection
Each active category gets its default slots (3/2/3/2); unfilled slots (muted or thin categories) go to the best remaining stories from any active category.
Fewer than 10 qualifying stories → fewer are returned with an explanation; nothing is fabricated.
