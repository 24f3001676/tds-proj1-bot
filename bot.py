import os
import json
import asyncio
from pathlib import Path
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

# ── Multi-turn buffer ───────────────────────────────────────────
# If the grader sends several messages quickly, we wait a few
# seconds and answer only the LAST one.
_pending: dict[int, asyncio.Task] = {}
BUFFER_SECONDS = 6


async def _delayed_reply(chat_id: int, question: str, app):
    """Wait BUFFER_SECONDS, then solve & reply."""
    await asyncio.sleep(BUFFER_SECONDS)

    run_id, log_path = new_run()
    try:
        result = solve(question, log_path)
    except Exception as e:
        log_step(log_path, {"event": "error", "error": str(e)})
        result = {"answer": None, "log_url": "PLACEHOLDER"}

    # Inject real log URL
    result["log_url"] = f"{LOG_BASE_URL}/{log_path.name}"

    # Send exactly one JSON object
    await app.bot.send_message(
        chat_id=chat_id,
        text=json.dumps(result, ensure_ascii=False),
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    question = update.message.text.strip()

    # Cancel any pending reply for this chat (multi-turn: keep last)
    if chat_id in _pending:
        _pending[chat_id].cancel()

    _pending[chat_id] = asyncio.create_task(
        _delayed_reply(chat_id, question, ctx.application)
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    print("✅ Bot is polling …")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()