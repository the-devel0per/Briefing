"""Daily maintenance. TTL removes expired items lazily (up to ~48h late); this function removes
stale pool days eagerly (articles + their rewrites) so storage stays bounded even if TTL lags."""
from datetime import date, timedelta

from shared.ai.personalities import MODES
from shared.config import Settings
from shared.repositories.dynamo import DynamoRepository
from shared.utils import briefing_day, log, utcnow


def cleanup(repo, settings, now):
    today = date.fromisoformat(briefing_day(now, settings.timezone))
    removed = 0
    for offset in range(settings.retention_days + 1, settings.retention_days + 4):
        day = (today - timedelta(days=offset)).isoformat()
        for a in repo.query_pool(day, 500):
            repo.delete_article_cascade(a["id"], list(MODES))
            removed += 1
    log("info", "cleanup_done", removedArticles=removed)
    return {"removedArticles": removed}


def handler(event, context):
    s = Settings.from_env()
    return cleanup(DynamoRepository(s.articles_table, s.users_table), s, utcnow())
