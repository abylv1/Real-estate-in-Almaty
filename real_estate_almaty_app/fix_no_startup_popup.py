# -*- coding: utf-8 -*-
"""
fix_no_startup_popup.py

Убирает всплывающее "ошибочное/предупреждающее" окно при запуске,
когда после закрытия крестиком программа всё равно нормально открывается.

Что делает:
1) _show_warnings больше не показывает QMessageBox.
2) Отключает QTimer.singleShot(..., self._show_warnings), который вызывал окно после загрузки.
3) Оставляет настоящие критические ошибки загрузки данных, чтобы не скрывать реальные проблемы.
4) Ставит QtWebEngine flags в начале main.py, чтобы запуск был стабильнее через python main.py.

Запуск:
python fix_no_startup_popup.py
"""

from pathlib import Path
import re
import shutil
import py_compile

MAIN_PATH = Path("main.py")
if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти этот файл из папки проекта.")

backup = Path("main.py.backup_no_startup_popup")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

ENV_BLOCK = "\n# ============================================================\n# Stable QtWebEngine startup flags\n# Must be before PySide6 / QWebEngine imports\n# ============================================================\nos.environ.setdefault(\"QT_OPENGL\", \"software\")\nos.environ.setdefault(\"QTWEBENGINE_DISABLE_SANDBOX\", \"1\")\nos.environ.setdefault(\n    \"QTWEBENGINE_CHROMIUM_FLAGS\",\n    \"--disable-gpu --disable-gpu-compositing --disable-logging --log-level=3 \"\n    \"--ignore-certificate-errors --no-sandbox --disable-features=VizDisplayCompositor\"\n)\nos.environ.setdefault(\n    \"QT_LOGGING_RULES\",\n    \"qt.webenginecontext.debug=false;qt.webenginecontext.warning=false;qt.qpa.*=false\"\n)\n# ============================================================\n\n"
NEW_SHOW_WARNINGS = "    def _show_warnings(self):\n        \"\"\"\n        Без всплывающего окна при запуске.\n        Раньше QMessageBox.warning выглядел как ошибка, хотя программа потом работала.\n        Теперь предупреждения только в status bar и терминале.\n        \"\"\"\n        try:\n            count = len(self._warnings) if getattr(self, \"_warnings\", None) else 0\n            if count:\n                self.status_bar.showMessage(\n                    f\"Данные загружены с предупреждениями: {count}. Программа работает.\",\n                    8000\n                )\n                print(\"\\n[Предупреждения при загрузке данных]\")\n                for w in self._warnings:\n                    print(\" -\", w)\n                print()\n        except Exception:\n            pass\n"

# ------------------------------------------------------------
# 1) Put stable QtWebEngine environment before PySide imports
# ------------------------------------------------------------

# Remove older inserted copies if they exist
text = re.sub(
    r"\n# ============================================================\n# Stable QtWebEngine startup flags[\s\S]*?# ============================================================\n\n",
    "\n",
    text,
    count=1,
)

text = re.sub(
    r"\n# ============================================================\n# QtWebEngine GPU/log noise fix[\s\S]*?# ============================================================\n\n",
    "\n",
    text,
    count=1,
)

if "import os\n" in text:
    text = text.replace("import os\n", "import os\n" + ENV_BLOCK, 1)
    print("OK: stable QtWebEngine flags inserted after import os")
else:
    text = "import os\n" + ENV_BLOCK + text
    print("OK: import os and stable QtWebEngine flags inserted")

# ------------------------------------------------------------
# 2) Replace _show_warnings with non-popup method
# ------------------------------------------------------------

def method_bounds(source: str, method_name: str):
    matches = list(re.finditer(rf"(?m)^    def {re.escape(method_name)}\s*\(", source))
    if not matches:
        return None
    m = matches[0]
    next_m = re.search(r"(?m)^    def \w+\s*\(", source[m.end():])
    end = m.end() + next_m.start() if next_m else len(source)
    return m.start(), end

bounds = method_bounds(text, "_show_warnings")
if bounds:
    start, end = bounds
    text = text[:start] + NEW_SHOW_WARNINGS.rstrip() + "\n" + text[end:]
    print("OK: _show_warnings replaced with non-popup version")
else:
    print("WARNING: _show_warnings method not found")

# ------------------------------------------------------------
# 3) Disable delayed popup call after loading
# ------------------------------------------------------------

patterns = [
    r"QTimer\.singleShot\(\s*1000\s*,\s*self\._show_warnings\s*\)",
    r"QTimer\.singleShot\(\s*\d+\s*,\s*self\._show_warnings\s*\)",
]

replaced_total = 0
for pat in patterns:
    text, n = re.subn(pat, "lambda: None  # startup warning popup disabled", text)
    replaced_total += n

print("Disabled QTimer _show_warnings calls:", replaced_total)

# Clean useless block if it exists
text = re.sub(
    r"\n\s*if self\._warnings:\s*\n\s*lambda:\s*None\s*# startup warning popup disabled\s*\n",
    "\n            # startup warning popup disabled\n",
    text,
    count=1,
)

MAIN_PATH.write_text(text, encoding="utf-8")

py_compile.compile(str(MAIN_PATH), doraise=True)
print("OK: main.py syntax is valid")
print("DONE: startup popup disabled.")
print("Run: python main.py")
