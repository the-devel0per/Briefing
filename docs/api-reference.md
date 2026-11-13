# API reference
Base: API Gateway URL. JSON in/out. Auth: `Authorization: Bearer <token>` from `POST /api/session`. Errors: `{"error":{"code","message","requestId"}}`.

| Method & path | Auth | Description |
|---|---|---|
| `GET /api/health` | no | last ingestion + per-source status |
| `POST /api/session` | no | issue anonymous token (rate-limited per hashed IP/day) → `201 {token}` |
| `GET /api/briefing/today` | yes | today's briefing: `articles[]`, `fetchMore{used,max,remaining,canFetchMore,exhausted}`, `categoryCounts`, `activeCategories`, `preferences`, `notice` |
| `GET /api/news?category=&offset=&limit=` | yes | paginated list of stories **already delivered** to this user (max limit 30) |
| `GET /api/news/{articleId}` | yes | one article (404 if unknown/expired) |
| `POST /api/news/fetch-more` | yes | requires `Idempotency-Key` (8–64 chars). Up to 10 new unique stories from the reserve pool. 2nd extra batch is the last; then `429 FETCH_MORE_LIMIT_REACHED`. Replaying a key returns the same batch without using quota. If the reserve is empty it returns `[]` and does not consume quota. |
| `POST /api/news/{articleId}/rewrite` | yes | body `{mode}`; cached per article+tone; per-user daily quota (`429 REWRITE_QUOTA_REACHED`); `503 AI_UNAVAILABLE` if Gemini/budget fails (UI keeps original) |
| `GET/POST/PUT /api/preferences` | yes | `{mutedCategories:[technology|government|crypto|stocks], humourMode:witty|roast|sarcastic|deadpan|genz|unhinged}`; ≥1 category must stay active |
| `DELETE /api/preferences` | yes | reset preferences (usage/quota rows are kept so the quota cannot be reset this way) |

Article object: `id, category, originalTitle, aiHeadline|null, aiMode|null, publisher, publishedAt, summary|null, url, coverage, alsoReportedBy[], image{url,source,attribution,alt,status}|null`.
Codes: 400 `INVALID_REQUEST`, 401 `UNAUTHORIZED`, 404 `NOT_FOUND`, 409 `CONFLICT`, 429, 503 `AI_UNAVAILABLE`, 500 `INTERNAL_ERROR`.
