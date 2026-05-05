# -*- coding: utf-8 -*-
"""
diagnose_openai_connection_v2.py

Исправленная диагностика OpenAI API.
В первой версии max_output_tokens был 10, а API требует минимум 16.
Здесь стоит 32.

Запуск:
python diagnose_openai_connection_v2.py
"""

from pathlib import Path
import os
import sys
import traceback

def read_env_file():
    env_path = Path(".env")
    data = {}
    if not env_path.exists():
        return data

    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data

print("=" * 70)
print("OPENAI API DIAGNOSTIC V2")
print("=" * 70)

print("Python:", sys.executable)
print("Project folder:", Path.cwd())

env_file = read_env_file()
key = os.getenv("OPENAI_API_KEY") or env_file.get("OPENAI_API_KEY", "")
model = os.getenv("OPENAI_MODEL") or env_file.get("OPENAI_MODEL", "gpt-5.4-mini")

print("OPENAI_API_KEY found:", bool(key))
if key:
    print("Key preview:", key[:7] + "..." + key[-4:])
else:
    print("Key preview: NO KEY")

print("OPENAI_MODEL:", model)

try:
    import openai
    print("openai package:", getattr(openai, "__version__", "installed"))
except Exception:
    print("openai package: NOT INSTALLED")
    print("Install command: pip install openai")
    raise SystemExit(1)

try:
    from openai import OpenAI

    if not key:
        print("\nRESULT: NO KEY")
        print('Fix in PowerShell:')
        print('$env:OPENAI_API_KEY="paste_your_key_here"')
        print('$env:OPENAI_MODEL="gpt-5.4-mini"')
        raise SystemExit(1)

    client = OpenAI(api_key=key)

    print("\nSending tiny test request to Responses API...")
    response = client.responses.create(
        model=model,
        instructions="Reply with exactly: OK",
        input="Test",
        max_output_tokens=32,
    )

    text = getattr(response, "output_text", "")
    print("API response:", repr(text))
    print("\nRESULT: SUCCESS ✅")
    print("OpenAI API works in this terminal.")
    print("Now run: python main.py")

except Exception as e:
    print("\nRESULT: API ERROR ❌")
    print("Error type:", type(e).__name__)
    print("Error message:", str(e))

    Path("logs").mkdir(exist_ok=True)
    Path("logs/openai_diagnostic_error_v2.txt").write_text(
        traceback.format_exc(),
        encoding="utf-8"
    )
    print("\nFull error saved to: logs/openai_diagnostic_error_v2.txt")

    msg = str(e).lower()
    if "401" in msg or "api key" in msg or "unauthorized" in msg:
        print("\nLikely reason: wrong API key or key is not visible to this terminal.")
    elif "403" in msg or "permission" in msg or "restricted" in msg:
        print("\nLikely reason: key permissions. Set Responses: Write and List models: Read.")
    elif "404" in msg or ("model" in msg and "not" in msg):
        print("\nLikely reason: model not available for your project. Try another model name.")
    elif "quota" in msg or "billing" in msg or "insufficient" in msg:
        print("\nLikely reason: no API billing/credits.")
    else:
        print("\nUnknown reason. Send me Error type and Error message, but DO NOT send your API key.")
