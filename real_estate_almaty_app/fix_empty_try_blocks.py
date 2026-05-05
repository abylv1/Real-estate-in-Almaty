# -*- coding: utf-8 -*-
"""
fix_empty_try_blocks.py

Исправляет ошибку:
IndentationError: expected an indented block after 'try' statement

Причина: в main.py остался блок:
    try:
        # app.setAttribute(...)
        # app.setAttribute(...)
    except AttributeError:
        pass

Когда внутри try только комментарии, Python считает блок пустым.
Скрипт вставляет:
        pass

Запуск:
python fix_empty_try_blocks.py
"""

from pathlib import Path
import py_compile
import shutil
import re

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти файл из папки проекта real_estate_almaty_app.")

backup = Path("main.py.backup_empty_try_blocks")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines(True)


def indent_len(s: str) -> int:
    return len(s) - len(s.lstrip(" \t"))


def leading_ws(s: str) -> str:
    return s[:indent_len(s)]


def is_blank_or_comment(s: str) -> bool:
    stripped = s.strip()
    return stripped == "" or stripped.startswith("#")


inserted = 0
i = 0

while i < len(lines):
    stripped = lines[i].strip()

    if stripped == "try:":
        base_indent = indent_len(lines[i])
        body_indent = leading_ws(lines[i]) + "    "

        j = i + 1
        # пропускаем пустые строки и комментарии
        while j < len(lines) and is_blank_or_comment(lines[j]):
            j += 1

        # Если сразу except/finally/else того же уровня — try пустой
        if j < len(lines):
            next_stripped = lines[j].strip()
            next_indent = indent_len(lines[j])

            if next_indent == base_indent and (
                next_stripped.startswith("except")
                or next_stripped.startswith("finally")
                or next_stripped.startswith("else:")
            ):
                # вставляем pass сразу после try, перед комментариями
                lines.insert(i + 1, body_indent + "pass  # inserted by fix_empty_try_blocks.py\n")
                inserted += 1
                print(f"Inserted pass after empty try at line {i + 1}")
                i += 2
                continue

        # Если после try вообще ничего нет — тоже вставляем
        else:
            lines.insert(i + 1, body_indent + "pass  # inserted by fix_empty_try_blocks.py\n")
            inserted += 1
            print(f"Inserted pass after empty try at line {i + 1}")
            i += 2
            continue

    i += 1

MAIN_PATH.write_text("".join(lines), encoding="utf-8")
print("Inserted pass count:", inserted)

try:
    py_compile.compile(str(MAIN_PATH), doraise=True)
    print("OK: main.py syntax fixed")
    print("Now run:")
    print('$env:QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --disable-gpu-compositing --ignore-certificate-errors --no-sandbox"; python main.py')
except Exception as e:
    print("Still has syntax error.")
    print(e)

    # Показываем контекст ошибки
    lineno = getattr(e, "lineno", None)
    if lineno is None and hasattr(e, "exc_value"):
        lineno = getattr(e.exc_value, "lineno", None)

    if lineno:
        current = MAIN_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        a = max(1, lineno - 8)
        b = min(len(current), lineno + 8)
        print("Context:")
        for num in range(a, b + 1):
            marker = ">>>" if num == lineno else "   "
            print(f"{marker} {num}: {current[num - 1]}")

    raise
