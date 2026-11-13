from shared.ai.gemini import GeminiClient
from shared.config import Settings
from shared.repositories.dynamo import DynamoRepository
from shared.secrets import resolve

from .app import App

_app = None


def _build():
    s = Settings.from_env()

    def gemini():
        key = resolve(s.gemini_api_key, s.gemini_key_param)
        return GeminiClient(key, s.gemini_model, s.gemini_timeout, s.gemini_max_output_tokens,
                            s.gemini_temperature, s.gemini_thinking_budget) if key else None

    return App(DynamoRepository(s.articles_table, s.users_table), s, gemini)


def handler(event, context):
    global _app
    if _app is None:  # reused across warm invocations: boto3 clients and caches survive
        _app = _build()
    return _app.handle(event)
