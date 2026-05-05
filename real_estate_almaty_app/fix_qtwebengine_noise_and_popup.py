# -*- coding: utf-8 -*-
"""
fix_qtwebengine_noise_and_popup.py

Чинит две вещи:
1) Убирает/прячет GPU-шум QtWebEngine в терминале.
2) Убирает всплывающее окно "Предупреждения при загрузке", которое надо закрывать крестиком.

После запуска этого patch запускай программу через:
python run_app_clean.py
или
.\run_app.ps1
"""

from pathlib import Path
import re
import shutil
import py_compile

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти этот файл из папки проекта.")

backup = Path("main.py.backup_qtwebengine_noise_popup")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

EARLY_BLOCK = "\n# ============================================================\n# QtWebEngine GPU/log noise fix\n# ВАЖНО: этот блок должен стоять ДО import PySide6 и ДО src.map_view.\n# ============================================================\nos.environ[\"QT_OPENGL\"] = \"software\"\nos.environ[\"QTWEBENGINE_DISABLE_SANDBOX\"] = \"1\"\nos.environ[\"QTWEBENGINE_CHROMIUM_FLAGS\"] = (\n    \"--disable-gpu \"\n    \"--disable-gpu-compositing \"\n    \"--disable-logging \"\n    \"--log-level=3 \"\n    \"--ignore-certificate-errors \"\n    \"--no-sandbox \"\n    \"--disable-features=VizDisplayCompositor\"\n)\nos.environ[\"QT_LOGGING_RULES\"] = (\n    \"qt.webenginecontext.debug=false;\"\n    \"qt.webenginecontext.warning=false;\"\n    \"qt.qpa.*=false\"\n)\n# ============================================================\n\n"
NEW_SHOW_WARNINGS = "    def _show_warnings(self):\n        \"\"\"\n        Не показываем модальное окно предупреждений при запуске.\n        Раньше оно выглядело как ошибка: пользователь закрывал его крестиком,\n        и только потом видел основное окно.\n        Теперь предупреждения идут только в status bar и терминал.\n        \"\"\"\n        if self._warnings:\n            short_msg = f\"Данные загружены с предупреждениями: {len(self._warnings)} шт. Программа работает.\"\n            try:\n                self.status_bar.showMessage(short_msg, 10000)\n            except Exception:\n                pass\n\n            try:\n                print(\"\\n[Предупреждения при загрузке данных]\")\n                for w in self._warnings:\n                    print(\" -\", w)\n                print()\n            except Exception:\n                pass\n"
RUN_CLEAN = "# -*- coding: utf-8 -*-\n\"\"\"\nClean launcher for the Almaty real estate app.\n\nIt redirects native QtWebEngine/Chromium GPU messages from terminal\nto logs/qtwebengine_stderr.log and starts main.py.\n\nRun:\npython run_app_clean.py\n\"\"\"\n\nimport os\nimport sys\nfrom pathlib import Path\nimport traceback\n\n# Must be set before importing main.py / PySide6 / QWebEngine\nos.environ[\"QT_OPENGL\"] = \"software\"\nos.environ[\"QTWEBENGINE_DISABLE_SANDBOX\"] = \"1\"\nos.environ[\"QTWEBENGINE_CHROMIUM_FLAGS\"] = (\n    \"--disable-gpu \"\n    \"--disable-gpu-compositing \"\n    \"--disable-logging \"\n    \"--log-level=3 \"\n    \"--ignore-certificate-errors \"\n    \"--no-sandbox \"\n    \"--disable-features=VizDisplayCompositor\"\n)\nos.environ[\"QT_LOGGING_RULES\"] = (\n    \"qt.webenginecontext.debug=false;\"\n    \"qt.webenginecontext.warning=false;\"\n    \"qt.qpa.*=false\"\n)\n\nPath(\"logs\").mkdir(exist_ok=True)\nlog_path = Path(\"logs\") / \"qtwebengine_stderr.log\"\n\n# Redirect low-level stderr (file descriptor 2), where Chromium writes GPU messages.\ntry:\n    _stderr_file = open(log_path, \"ab\", buffering=0)\n    os.dup2(_stderr_file.fileno(), 2)\nexcept Exception:\n    _stderr_file = None\n\ntry:\n    import main\n    main.main()\nexcept SystemExit:\n    raise\nexcept Exception:\n    # Print real Python errors to stdout so user still sees them.\n    print(\"\\n[PYTHON ERROR]\")\n    traceback.print_exc(file=sys.stdout)\n    print(f\"\\nQtWebEngine native logs are saved here: {log_path}\")\n    input(\"Press Enter to close...\")\n"
RUN_PS1 = "$env:QT_OPENGL=\"software\"\n$env:QTWEBENGINE_DISABLE_SANDBOX=\"1\"\n$env:QTWEBENGINE_CHROMIUM_FLAGS=\"--disable-gpu --disable-gpu-compositing --disable-logging --log-level=3 --ignore-certificate-errors --no-sandbox --disable-features=VizDisplayCompositor\"\n$env:QT_LOGGING_RULES=\"qt.webenginecontext.debug=false;qt.webenginecontext.warning=false;qt.qpa.*=false\"\npython run_app_clean.py\n"

# ------------------------------------------------------------
# 1) Early QtWebEngine environment variables
# ------------------------------------------------------------

# Remove old copy if already inserted
text = re.sub(
    r"\n# ============================================================\n# QtWebEngine GPU/log noise fix[\s\S]*?# ============================================================\n\n",
    "\n",
    text,
    count=1,
)

# Insert after import os
if "import os\n" in text:
    text = text.replace("import os\n", "import os\n" + EARLY_BLOCK, 1)
    print("OK: early QtWebEngine env block inserted after import os")
else:
    text = EARLY_BLOCK + text
    print("OK: early QtWebEngine env block inserted at top")

# Remove/neutralize late setdefault in main(), because it can conflict
text = re.sub(
    r'\n\s*# Включаем OpenGL software rendering для совместимости\s*\n\s*os\.environ\.setdefault\("QTWEBENGINE_CHROMIUM_FLAGS",\s*"[^"]*"\)\s*\n',
    "\n    # QtWebEngine flags are configured at the top of the file before PySide imports.\n",
    text,
    count=1,
)
text = re.sub(
    r'\n\s*os\.environ\.setdefault\("QTWEBENGINE_CHROMIUM_FLAGS",\s*"[^"]*"\)\s*\n',
    "\n    # QtWebEngine flags are configured at the top of the file before PySide imports.\n",
    text,
    count=1,
)

# ------------------------------------------------------------
# 2) Replace _show_warnings to non-modal version
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
    print("WARNING: _show_warnings not found")

MAIN_PATH.write_text(text, encoding="utf-8")

# ------------------------------------------------------------
# 3) Create clean launchers
# ------------------------------------------------------------

Path("run_app_clean.py").write_text(RUN_CLEAN, encoding="utf-8")
print("OK: run_app_clean.py created")

Path("run_app.ps1").write_text(RUN_PS1, encoding="utf-8")
print("OK: run_app.ps1 created")

# ------------------------------------------------------------
# 4) Syntax check
# ------------------------------------------------------------
py_compile.compile(str(MAIN_PATH), doraise=True)
py_compile.compile("run_app_clean.py", doraise=True)

print("DONE.")
print("Теперь запускай так:")
print("python run_app_clean.py")
print("или так:")
print(".\\run_app.ps1")
