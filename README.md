# TDS Project 1 – Data-Analyst Telegram Bot

LLM-powered agent that answers data-analysis questions via Telegram.

## How it works
1. Receives a plain-text question on Telegram
2. LLM (GPT-4o-mini via AI Pipe) reasons about the question
3. Writes & executes Python code (pandas, requests) if needed
4. Replies with exactly one JSON object: `{"answer": ..., "log_url": ...}`

## Run locally
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="..."
export AIPIPE_API_KEY="..."
export AIPIPE_BASE_URL="https://aipipe.org/openai/v1"
export LLM_MODEL="gpt-4o-mini"
export LOG_BASE_URL="http://localhost:8080/logs"
python bot.py