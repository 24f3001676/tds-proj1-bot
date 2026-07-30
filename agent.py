import os
import json
import subprocess
import tempfile
import textwrap
import re
from openai import OpenAI

# ── AI Pipe → OpenAI-compatible endpoint ────────────────────────
AIPIPE_KEY = os.environ["AIPIPE_API_KEY"]
AIPIPE_BASE = os.environ.get("AIPIPE_BASE_URL", "https://aipipe.org/openai/v1")
MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

client = OpenAI(
    api_key=AIPIPE_KEY,
    base_url=AIPIPE_BASE,
)

SYSTEM_PROMPT = textwrap.dedent("""\
You are a rigorous data-analysis agent.

Rules:
1. If data is embedded inline in the question, parse it exactly as given.
2. If the question references a public dataset (MOSPI, data.gov.in, Census,
   RBI, etc.), FETCH it with requests + pandas and compute from the real data.
3. Write a short Python script that computes the answer and prints it as JSON
   to stdout. The script will be executed; use its real output.
4. NEVER invent placeholder values like "State D", "REPLACE_ME", "XYZ", or
   made-up names. Every value in your answer must come from actual data you
   parsed or fetched. If you genuinely cannot determine it, still give the
   best data-backed answer — do not fabricate.
5. Reply with EXACTLY one JSON object and nothing else, with two keys:
   - "answer": the answer in the EXACT shape the question requests.
   - "log_url": the string "PLACEHOLDER" (replaced later).
6. No markdown, no prose, no code fences in the final reply — just the JSON.

When you need to run code, put it in a ```python ... ``` block first.
""")


def solve(question: str, log_path) -> dict:
    from logger import log_step

    log_step(log_path, {"event": "start", "question": question})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for i in range(6):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0,
                max_tokens=4096,
            )
        except Exception as e:
            log_step(log_path, {"event": "llm_error", "error": str(e)})
            return {"answer": None, "log_url": "PLACEHOLDER"}

        content = resp.choices[0].message.content.strip()
        log_step(log_path, {"event": f"llm_turn_{i}", "content": content})

        parsed = _try_parse_json(content)
        if parsed and "answer" in parsed:
            log_step(log_path, {"event": "final_answer", "result": parsed})
            return parsed

        code = _extract_code(content)
        if code:
            log_step(log_path, {"event": "code_exec", "code": code})
            output = _run_code(code)
            log_step(log_path, {"event": "code_output", "output": output[:4000]})
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": (
                    f"Here is the output of your code:\n\n{output[:3000]}\n\n"
                    "Now produce the FINAL answer as a single JSON object "
                    'with keys "answer" and "log_url". '
                    'Set "log_url" to "PLACEHOLDER". '
                    "Reply with ONLY the JSON, nothing else."
                ),
            })
        else:
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": (
                    "Reply with ONLY the final JSON object. "
                    'Keys: "answer" and "log_url". '
                    'Set "log_url" to "PLACEHOLDER". No other text.'
                ),
            })

    log_step(log_path, {"event": "max_iterations_reached"})
    return {"answer": None, "log_url": "PLACEHOLDER"}


def _try_parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _extract_code(text: str):
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


def _run_code(code: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        fname = f.name
    try:
        r = subprocess.run(
            ["python", fname],
            capture_output=True, text=True, timeout=60,
        )
        out = r.stdout
        if r.stderr:
            out += "\n[STDERR]\n" + r.stderr
        return out[:5000]
    except subprocess.TimeoutExpired:
        return "TIMEOUT: code took >60 s"
    except Exception as e:
        return f"EXEC ERROR: {e}"
    finally:
        os.unlink(fname)