from shared.ai.gemini import GeminiClient
from shared.config import Settings, load_feeds
from shared.ingestion.og import fetch_og_image
from shared.ingestion.pipeline import run_ingestion
from shared.repositories.dynamo import DynamoRepository
from shared.secrets import resolve
from shared.utils import utcnow


def handler(event, context):
    s = Settings.from_env()
    key = resolve(s.gemini_api_key, s.gemini_key_param)
    gemini = GeminiClient(key, s.gemini_model, s.gemini_timeout, s.gemini_max_output_tokens,
                          s.gemini_temperature, s.gemini_thinking_budget) if key else None
    repo = DynamoRepository(s.articles_table, s.users_table)
    return run_ingestion(repo, load_feeds(), s, utcnow(), gemini=gemini, og_fetch=fetch_og_image)
