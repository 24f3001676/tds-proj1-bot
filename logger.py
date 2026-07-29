import json
import time
import uuid
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def new_run():
    run_id = str(uuid.uuid4())[:8]
    path = LOG_DIR / f"{run_id}.jsonl"
    return run_id, path


def log_step(path, step: dict):
    step["ts"] = time.time()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(step, ensure_ascii=False) + "\n")