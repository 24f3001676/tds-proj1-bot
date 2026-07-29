import json
import time
import uuid
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def new_run():
    """Create a new run and return (run_id, log_file_path)."""
    run_id = str(uuid.uuid4())[:8]
    path = LOG_DIR / f"{run_id}.jsonl"
    return run_id, path


def log_step(path, step: dict):
    """Append one JSON line to the run log."""
    step["ts"] = time.time()
    with open(path, "a") as f:
        f.write(json.dumps(step, ensure_ascii=False) + "\n")