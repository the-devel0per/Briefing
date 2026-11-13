# Database design (DynamoDB, on-demand)

**Articles table** — `pk` (S). GSI `PoolByScore`: `day` (S) + `score` (N). TTL attribute `expiresAt`.
| pk | Content | Retention |
|---|---|---|
| `A#<id>` | article (id = sha1(canonical url)[:16]), category, title, publisher, url, publishedAt, summary, image{url,source,attribution,status}, coverage, alsoReportedBy, score, day, expiresAt | 7 days |
| `R#<id>#<mode>` | cached AI headline per article+tone | 7 days |
| `S#<feedId>` | source health: lastSuccess, consecutiveFailures, etag/lastModified (conditional GET) | none (tiny) |
| `M#last_ingest` | last ingestion summary | none |

**Users table** — `userId` (S) + `sk` (S). TTL `expiresAt`.
| userId / sk | Content | Retention |
|---|---|---|
| `<uid>` / `PREF` | mutedCategories, humourMode | until user deletes (`DELETE /api/preferences`) |
| `<uid>` / `USAGE#<day>` | fetchMoreCount, delivered[] (ordered ids), requests{idempotencyKey→ids} | 3 days |
| `<uid>` / `RW#<day>` | per-user rewrite counter | 3 days |
| `Q#gemini` / `<day>` | global daily Gemini call counter | 3 days |
| `Q#session` / `<ipHash>#<day>` | sessions created per (HMAC-hashed) IP | 3 days |

**Access patterns** (no scans): pool = `Query PoolByScore day=<d> ScanIndexForward=false`; article/rewrite/source = `GetItem`/`BatchGetItem`; user state = `GetItem`.
**Atomic Fetch More**: `UpdateItem` with `ConditionExpression: fetchMoreCount = :expected AND fetchMoreCount < :max AND attribute_not_exists(requests.#key)`.
Racing requests cannot both pass; the loser re-reads and retries; the cap is re-checked inside the same write.
**TTL is lazy** (can lag ~48h): every read path also filters `expiresAt <= now`, and the cleanup Lambda deletes stale pool days eagerly.
