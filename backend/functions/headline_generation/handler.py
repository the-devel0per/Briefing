"""Manual/backfill entry point: invoke to (re)generate default-tone rewrites for today's top stories
without waiting for the next ingestion run. Obeys the same daily Gemini budget as everything else."""
from shared.ai.gemini import GeminiClient
from shared.ai.headlines import generate_default_rewrites
from shared.config import Settings
from shared.repositories.dynamo import DynamoRepository
from shared.secrets import resolve
from shared.utils import briefing_day, utcnow


def handler(event, context):
    s, now = Settings.from_env(), utcnow()
    key = resolve(s.gemini_api_key, s.gemini_key_param)
    if not key:
        return {"skipped": "no Gemini key configured"}
    repo = DynamoRepository(s.articles_table, s.users_table)
    top = repo.query_pool(briefing_day(now, s.timezone), s.rewrite_top_n)
    client = GeminiClient(key, s.gemini_model, s.gemini_timeout, s.gemini_max_output_tokens,
                          s.gemini_temperature, s.gemini_thinking_budget)
    return generate_default_rewrites(repo, client, top, s, now)
