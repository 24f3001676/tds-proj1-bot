FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose log server
EXPOSE 8080

# Start both the bot and the log server
CMD ["sh", "-c", "python log_server.py & python bot.py"]