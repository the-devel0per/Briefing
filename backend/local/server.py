"""Local dev API on http://localhost:8787 using the in-memory repository (no AWS needed).
Runs one real ingestion at startup (needs internet) and every 30 min after.
Usage (from backend/):  GEMINI_API_KEY=... python -m local.server"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

os.environ.setdefault("SESSION_SECRET", "local-dev-secret-change-me")

from functions.api.app import App
from shared.ai.gemini import GeminiClient
from shared.config import Settings, load_feeds
from shared.ingestion.pipeline import run_ingestion
from shared.repositories.memory import MemoryRepository
from shared.utils import utcnow

S = Settings.from_env()
REPO = MemoryRepository()


def gemini():
    return GeminiClient(S.gemini_api_key, S.gemini_model, S.gemini_timeout, S.gemini_max_output_tokens,
                        S.gemini_temperature, S.gemini_thinking_budget) if S.gemini_api_key else None


APP = App(REPO, S, gemini)


def ingest_loop():
    while True:
        time.sleep(1800)
        try:
            run_ingestion(REPO, load_feeds(), S, utcnow(), gemini=gemini())
        except Exception as exc:  # keep the dev server alive
            print("ingestion error:", exc)


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in S.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "authorization,content-type,idempotency-key")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _serve(self, method):
        path, _, qs = self.path.partition("?")
        length = int(self.headers.get("Content-Length") or 0)
        event = {"rawPath": path, "headers": dict(self.headers), "body": self.rfile.read(length).decode() or None,
                 "queryStringParameters": dict(p.split("=", 1) for p in qs.split("&") if "=" in p) or None,
                 "requestContext": {"requestId": "local", "http": {"method": method, "sourceIp": self.client_address[0]}}}
        r = APP.handle(event)
        self.send_response(r["statusCode"])
        for k, v in r["headers"].items():
            self.send_header(k, v)
        self._cors()
        self.end_headers()
        self.wfile.write(r["body"].encode())

    do_GET = lambda self: self._serve("GET")
    do_POST = lambda self: self._serve("POST")
    do_PUT = lambda self: self._serve("PUT")
    do_DELETE = lambda self: self._serve("DELETE")


if __name__ == "__main__":
    print("Ingesting initial stories from news sources...")
    try:
        run_ingestion(REPO, load_feeds(), S, utcnow(), gemini=gemini())
        print(f"Ingestion complete: {len(REPO.items)} articles ready.")
    except Exception as exc:
        print("Initial ingestion error:", exc)
    threading.Thread(target=ingest_loop, daemon=True).start()
    print("API on http://localhost:8787")
    ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()
