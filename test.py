import os
from openai import OpenAI

client = OpenAI(
    base_url="https://aipipe.org/openai/v1",
    api_key="eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjI0ZjMwMDE2NzZAZHMuc3R1ZHkuaWl0bS5hYy5pbiIsImlhdCI6MTc4NTM0ODA2MSwiaXNzIjoiaHR0cHM6Ly9haXBpcGUub3JnIiwiYXVkIjoiYWlwaXBlLWFwaSIsImV4cCI6MTc4NTk1Mjg2MX0.nmtXGmYuzZTcdf5yYIZAhrTynOlc94JTr2JIYtEqhQ0",
)

MODELS = [
    "gpt-4o-mini",
    "gpt-4.1-nano",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-3.5-turbo",
]

for model in MODELS:
    print(f"Trying {model:20s} ... ", end="", flush=True)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with one word: hello"}],
            temperature=0,
            max_tokens=20,
        )
        text = resp.choices[0].message.content.strip()
        print(f'✅ SUCCESS → "{text}"')
    except Exception as e:
        print(f"❌ {str(e)[:80]}")