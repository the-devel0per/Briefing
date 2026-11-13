"""All tunable limits live here and are read from environment variables,
so cost/resource controls can be changed without a code deploy."""
import os
from dataclasses import dataclass


def _int(name, default):
    return int(os.environ.get(name, default))


def _bool(name, default):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    articles_table: str
    users_table: str
    timezone: str
    retention_days: int
    max_article_age_hours: int
    min_score: float
    briefing_size: int
    fetch_more_size: int
    max_fetch_more: int
    pool_limit: int
    feed_timeout: int
    feed_retries: int
    ingest_workers: int
    rewrite_top_n: int
    rewrite_batch_size: int
    gemini_model: str
    gemini_timeout: int
    gemini_max_output_tokens: int
    gemini_temperature: float
    gemini_thinking_budget: str
    gemini_daily_call_cap: int
    gemini_calls_per_run: int
    rewrite_user_daily_limit: int
    sessions_per_ip_daily: int
    enable_og_fetch: bool
    og_fetch_per_run: int
    allowed_origins: tuple
    gemini_api_key: str
    gemini_key_param: str
    session_secret: str
    session_secret_param: str

    @classmethod
    def from_env(cls):
        e = os.environ.get
        return cls(
            articles_table=e("ARTICLES_TABLE", "news-articles"),
            users_table=e("USERS_TABLE", "news-users"),
            timezone=e("BRIEFING_TIMEZONE", "UTC"),
            retention_days=_int("RETENTION_DAYS", 7),
            max_article_age_hours=_int("MAX_ARTICLE_AGE_HOURS", 30),
            min_score=float(e("MIN_STORY_SCORE", "0.15")),
            briefing_size=_int("BRIEFING_SIZE", 10),
            fetch_more_size=_int("FETCH_MORE_SIZE", 10),
            max_fetch_more=_int("MAX_FETCH_MORE", 2),
            pool_limit=_int("POOL_LIMIT", 120),
            feed_timeout=_int("FEED_TIMEOUT_SECONDS", 8),
            feed_retries=_int("FEED_RETRIES", 3),
            ingest_workers=_int("INGEST_WORKERS", 12),
            rewrite_top_n=_int("REWRITE_TOP_N", 30),
            rewrite_batch_size=_int("REWRITE_BATCH_SIZE", 10),
            gemini_model=e("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            gemini_timeout=_int("GEMINI_TIMEOUT_SECONDS", 12),
            gemini_max_output_tokens=_int("GEMINI_MAX_OUTPUT_TOKENS", 800),
            gemini_temperature=float(e("GEMINI_TEMPERATURE", "0.9")),
            gemini_thinking_budget=e("GEMINI_THINKING_BUDGET", "0"),
            gemini_daily_call_cap=_int("GEMINI_DAILY_CALL_CAP", 150),
            gemini_calls_per_run=_int("GEMINI_CALLS_PER_RUN", 3),
            rewrite_user_daily_limit=_int("REWRITE_USER_DAILY_LIMIT", 20),
            sessions_per_ip_daily=_int("SESSIONS_PER_IP_DAILY", 20),
            enable_og_fetch=_bool("ENABLE_OG_FETCH", False),
            og_fetch_per_run=_int("OG_FETCH_PER_RUN", 15),
            allowed_origins=tuple(o for o in e("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o),
            gemini_api_key=e("GEMINI_API_KEY", ""),
            gemini_key_param=e("GEMINI_KEY_PARAM", ""),
            session_secret=e("SESSION_SECRET", ""),
            session_secret_param=e("SESSION_SECRET_PARAM", ""),
        )
