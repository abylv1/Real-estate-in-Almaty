# -*- coding: utf-8 -*-
"""
fix_ai_chat_meta_questions.py

Исправляет ситуацию, когда ИИ блокирует фразы:
- Что ты еще умеешь?
- Что ты можешь?
- Какие у тебя функции?
- Какие вопросы можно задавать?
- Как пользоваться?

Запуск:
python fix_ai_chat_meta_questions.py
"""

from pathlib import Path
import re
import shutil
import py_compile

AI_PATH = Path("src/ai_assistant.py")
if not AI_PATH.exists():
    raise FileNotFoundError("src/ai_assistant.py не найден. Запусти из папки проекта.")

backup = Path("src/ai_assistant.py.backup_chat_meta_questions")
if not backup.exists():
    shutil.copyfile(AI_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = AI_PATH.read_text(encoding="utf-8", errors="replace")

NEW_CHAT_FUNC = "def _ore_v3_is_chat(question: str) -> bool:\n    \"\"\"\n    Улучшенная проверка чат/мета-вопросов к ассистенту.\n\n    Теперь проходят:\n    - Что ты умеешь?\n    - Что ты еще умеешь?\n    - Что ты можешь?\n    - Какие у тебя функции?\n    - Как пользоваться?\n    - Какие вопросы можно задавать?\n    \"\"\"\n    import re\n\n    q = _ore_v3_norm(question)\n\n    exact_words = [\n        \"привет\", \"салам\", \"здравствуй\", \"здравствуйте\", \"hello\", \"hi\",\n        \"помощь\", \"help\", \"начать\"\n    ]\n    if any(x == q or q.startswith(x + \" \") for x in exact_words):\n        return True\n\n    # Мета-вопросы про самого ассистента\n    patterns = [\n        r\"кто\\s+ты\",\n        r\"ты\\s+кто\",\n        r\"что\\s+ты\\s+.*умеешь\",\n        r\"что\\s+еще\\s+ты\\s+.*умеешь\",\n        r\"что\\s+ты\\s+.*можешь\",\n        r\"что\\s+еще\\s+ты\\s+.*можешь\",\n        r\"какие\\s+у\\s+тебя\\s+.*функц\",\n        r\"твои\\s+.*функц\",\n        r\"твои\\s+.*возможн\",\n        r\"что\\s+можно\\s+спросить\",\n        r\"какие\\s+вопросы\\s+.*зад\",\n        r\"как\\s+пользоваться\",\n        r\"как\\s+работать\",\n        r\"как\\s+мне\\s+.*пользоваться\",\n        r\"объясни\\s+себя\",\n        r\"ассистент\",\n    ]\n    if any(re.search(p, q) for p in patterns):\n        return True\n\n    # Только отдельное слово \"ии\" или \"ai\", а не часть другого слова.\n    # Например \"Венгрии\" больше НЕ считается словом \"ИИ\".\n    if re.search(r\"(^|\\s)(ии|ai)(\\s|$)\", q):\n        return True\n\n    return False\n"

pattern = r"def _ore_v3_is_chat\(question: str\) -> bool:\n[\s\S]*?\n\ndef _ore_v3_is_real_estate\("
m = re.search(pattern, text)
if not m:
    raise RuntimeError("Не найден def _ore_v3_is_chat(...) в src/ai_assistant.py")

replacement = NEW_CHAT_FUNC.rstrip() + "\n\n\ndef _ore_v3_is_real_estate("
text = text[:m.start()] + replacement + text[m.end():]

AI_PATH.write_text(text, encoding="utf-8")
py_compile.compile(str(AI_PATH), doraise=True)

print("OK: AI now understands assistant/meta questions like 'Что ты еще умеешь?'")
print("Run: python main.py")
