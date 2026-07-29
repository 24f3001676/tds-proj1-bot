from flask import Flask, send_from_directory
from pathlib import Path

app = Flask(__name__)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


@app.route("/logs/<path:filename>")
def serve_log(filename):
    return send_from_directory(LOG_DIR, filename, mimetype="application/x-ndjson")


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)