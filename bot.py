import os
import json
import asyncio
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
)
from agent import solve
from logger import new_run, log_step

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
LOG_BASE_URL = os.environ.get("LOG_BASE_URL", "http://localhost:8080/logs")
PORT = int(os.environ.get("PORT", 8080))

# ── Multi-turn buffer ───────────────────────────────────────────
_pending: dict[int, asyncio.Task] = {}
BUFFER_SECONDS = 6


# ── Tiny health + log HTTP server ───────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._respond(200, '{"status":"ok"}', "application/json")
        elif self.path.startswith("/logs/"):
            filename = self.path[len("/logs/"):]
            filepath = LOG_DIR / filename
            if filepath.exists() and filepath.suffix == ".jsonl":
                content = filepath.read_text(encoding="utf-8")
                self._respond(200, content, "application/x-ndjson")
            else:
                self._respond(404, '{"error":"not found"}', "application/json")
        else:
            self._respond(404, '{"error":"not found"}', "application/json")

    def _respond(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # silence


def start_http_server():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"✅ HTTP server on :{PORT}  (/health  /logs/<file>.jsonl)")
    server.serve_forever()


# ── Telegram handlers ───────────────────────────────────────────
async def _delayed_reply(chat_id: int, question: str, app):
    await asyncio.sleep(BUFFER_SECONDS)

    run_id, log_path = new_run()
    try:
        result = solve(question, log_path)
    except Exception as e:
        log_step(log_path, {"event": "error", "error": str(e)})
        result = {"answer": None, "log_url": "PLACEHOLDER"}

    result["log_url"] = f"{LOG_BASE_URL}/{log_path.name}"

    await app.bot.send_message(
        chat_id=chat_id,
        text=json.dumps(result, ensure_ascii=False),
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    question = update.message.text.strip()

    if chat_id in _pending:
        _pending[chat_id].cancel()

    _pending[chat_id] = asyncio.create_task(
        _delayed_reply(chat_id, question, ctx.application)
    )


# ── Main ────────────────────────────────────────────────────────
def main():
    # Start HTTP server in background thread
    t = threading.Thread(target=start_http_server, daemon=True)
    t.start()

    # Start Telegram bot (blocks)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    print("✅ Bot is polling …")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()