# -*- coding: utf-8 -*-
"""
fix_syntax_after_fast_start.py

Исправляет SyntaxError:
expected 'except' or 'finally' block
вокруг строки:
df["microdistrict"] = "Не определён"  # будет определяться по клику

Запускать из корня проекта:
python fix_syntax_after_fast_start.py
"""

from pathlib import Path
import shutil
import py_compile
import traceback

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти файл из корня проекта.")

backup = Path("main.py.backup_before_syntax_fix")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines(True)


def indent_len(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def leading_ws(line: str) -> str:
    return line[:indent_len(line)]


def is_micro_line(line: str) -> bool:
    return (
        "будет определяться по клику" in line
        or "Fast start: do not calculate microdistrict" in line
        or "df[\"microdistrict\"]" in line and "determine_microdistrict" in line
    )


def find_block_end(lines, start, base_indent):
    """
    Ищем конец try/except блока, который сломался.
    Берём до следующей строки с отступом <= base_indent после except/finally.
    """
    n = len(lines)
    except_idx = None

    for k in range(start + 1, min(n, start + 80)):
        s = lines[k].strip()
        if indent_len(lines[k]) == base_indent and (
            s.startswith("except") or s.startswith("finally") or s.startswith("else:")
        ):
            except_idx = k
            break

    if except_idx is None:
        # Нет except — берём маленький блок до следующей нормальной строки того же уровня.
        for k in range(start + 1, min(n, start + 50)):
            s = lines[k].strip()
            if k > start + 2 and s and indent_len(lines[k]) <= base_indent and not s.startswith("#"):
                return k
        return min(n, start + 12)

    k = except_idx + 1
    while k < n:
        s = lines[k].strip()
        ind = indent_len(lines[k])
        if s and ind <= base_indent and not s.startswith("#") and not s.startswith("except") and not s.startswith("finally") and not s.startswith("else:"):
            return k
        k += 1

    return k


changed = False
i = 0

while i < len(lines):
    line = lines[i]

    if "будет определяться по клику" in line or "Fast start: do not calculate microdistrict" in line:
        # Ищем ближайший try сверху. Важно: только рядом, чтобы не удалить большой try загрузки.
        start = None
        for j in range(i, max(-1, i - 18), -1):
            if lines[j].strip() == "try:":
                # Между try и текущей строкой должен быть microdistrict, иначе не трогаем
                segment = "".join(lines[j:i+1])
                if "microdistrict" in segment:
                    start = j
                    break

        if start is not None:
            base_indent = indent_len(lines[start])
            ws = leading_ws(lines[start])
            end = find_block_end(lines, start, base_indent)

            replacement = [
                f'{ws}# Fast start: не считаем microdistrict для всех строк при запуске.\\n',
                f'{ws}# Микрорайон будет определяться при выборе объекта или фильтра.\\n',
                f'{ws}if "microdistrict" not in df.columns:\\n',
                f'{ws}    df["microdistrict"] = "Не определён"\\n',
                '\\n',
            ]

            print(f"Fixed broken microdistrict try-block: lines {start+1}-{end}")
            lines[start:end] = replacement
            changed = True
            i = start + len(replacement)
            continue

    i += 1

if not changed:
    print("Broken microdistrict try-block was not found by pattern.")
    print("Trying direct indentation fix around the known comment...")

    for idx, line in enumerate(lines):
        if "будет определяться по клику" in line:
            # Если строка стоит не внутри except, удаляем её, потому что уже есть безопасная замена.
            print("Removed suspicious line:", idx + 1)
            lines[idx] = ""
            changed = True

new_text = "".join(lines)

# Дополнительно убираем предупреждения Qt, если они вернулись
new_text = new_text.replace(
    "    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)",
    "    # app.setAttribute(Qt.AA_EnableHighDpiScaling, True)"
)
new_text = new_text.replace(
    "    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)",
    "    # app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)"
)

MAIN_PATH.write_text(new_text, encoding="utf-8")

try:
    py_compile.compile(str(MAIN_PATH), doraise=True)
    print("OK: main.py syntax is fixed")
    print("Now run: python main.py")
except Exception:
    print("Still has syntax error. Context:")
    try:
        import sys
        exc = sys.exc_info()[1]
        lineno = getattr(exc, "lineno", None)
        if lineno:
            current = MAIN_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
            a = max(1, lineno - 8)
            b = min(len(current), lineno + 8)
            for num in range(a, b + 1):
                marker = ">>>" if num == lineno else "   "
                print(f"{marker} {num}: {current[num-1]}")
    except Exception:
        pass
    raise
