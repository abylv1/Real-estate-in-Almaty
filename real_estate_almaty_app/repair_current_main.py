# -*- coding: utf-8 -*-
"""
repair_current_main.py

Чинит текущий сломанный main.py:
1) восстанавливает _load_data;
2) исправляет пустой try в main();
3) чинит вкладку ИИ, чтобы self.ai_ask_btn существовал;
4) проверяет main.py через py_compile.

Запускать из папки проекта:
python repair_current_main.py
"""

from pathlib import Path
import re
import shutil
import py_compile

MAIN_PATH = Path("main.py")
if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти скрипт из папки real_estate_almaty_app.")

backup = Path("main.py.backup_before_repair_current_main")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

NEW_LOAD_DATA = '    def _load_data(self):\n        """Загружает CSV, считает район, статистику и показывает объекты на карте."""\n        try:\n            loaded = load_data()\n\n            # load_data() в разных версиях проекта может вернуть либо df, либо (df, warnings)\n            if isinstance(loaded, tuple):\n                df = loaded[0]\n                warnings = loaded[1] if len(loaded) > 1 else []\n            else:\n                df = loaded\n                warnings = []\n\n            if df is None or len(df) == 0:\n                raise ValueError("CSV загрузился пустым. Проверь data/cleaned_almaty_only.csv")\n\n            self._warnings = warnings or []\n\n            # Район определяем локально по координатам, без сетевых запросов\n            lat_col = "map_lat" if "map_lat" in df.columns else "latitude"\n            lon_col = "map_lon" if "map_lon" in df.columns else "longitude"\n\n            if lat_col not in df.columns or lon_col not in df.columns:\n                raise ValueError("В данных нет колонок координат map_lat/map_lon или latitude/longitude.")\n\n            df["district"] = df.apply(\n                lambda r: str(determine_district(float(r[lat_col]), float(r[lon_col]))).replace(" (приближённо)", "").strip(),\n                axis=1\n            )\n\n            # Не считаем microdistrict для всех строк при запуске, иначе программа может долго не открываться.\n            # Микрорайон будет определяться при клике на объект или при выборе микрорайона в фильтре.\n            if "microdistrict" not in df.columns:\n                df["microdistrict"] = "Не определён"\n            else:\n                df["microdistrict"] = (\n                    df["microdistrict"]\n                    .fillna("Не определён")\n                    .astype(str)\n                    .replace({"nan": "Не определён", "None": "Не определён", "": "Не определён"})\n                )\n\n            self.df = df\n            self.filtered_df = df.copy()\n\n            self.global_stats = compute_global_stats(df)\n            self.district_stats = compute_district_stats(df)\n\n            # Заполняем фильтры. В конце _init_filter_ranges() сам вызовет _apply_filters()\n            self._init_filter_ranges()\n\n            # Обновляем статистику\n            self._update_stats_panel()\n\n            total = self.global_stats.get("total", len(df))\n            valid = self.global_stats.get("total_valid", len(df))\n            susp = total - valid if isinstance(total, (int, float)) and isinstance(valid, (int, float)) else 0\n\n            self.status_bar.showMessage(\n                f"Загружено объектов: {total}  |  В границах Алматы: {valid}  |  Вне Алматы: {susp}"\n            )\n\n            if self._warnings:\n                QTimer.singleShot(1000, self._show_warnings)\n\n        except FileNotFoundError as e:\n            QMessageBox.critical(\n                self,\n                "Файл не найден",\n                str(e),\n                QMessageBox.Ok\n            )\n        except Exception as e:\n            QMessageBox.critical(\n                self,\n                "Ошибка загрузки данных",\n                f"Не удалось загрузить данные:\\n{str(e)}",\n                QMessageBox.Ok\n            )\n'
NEW_AI_TAB = '    def _build_ai_tab(self) -> QWidget:\n        """Вкладка ИИ-ассистента. Исправленная версия: кнопка сохраняется как self.ai_ask_btn."""\n        widget = QWidget()\n        widget.setStyleSheet("background:#ffffff;color:#111827;")\n\n        layout = QVBoxLayout(widget)\n        layout.setContentsMargins(8, 8, 8, 8)\n        layout.setSpacing(6)\n\n        title = QLabel("🤖 ИИ-ассистент по недвижимости")\n        title.setObjectName("sectionLabel")\n        title.setStyleSheet("color:#1a237e;font-size:14px;font-weight:800;background:#ffffff;")\n        layout.addWidget(title)\n\n        self.ai_context_label = QLabel("Сначала выберите объект на карте")\n        self.ai_context_label.setWordWrap(True)\n        self.ai_context_label.setMaximumHeight(62)\n        self.ai_context_label.setStyleSheet(\n            "background:#eef2ff;color:#111827;border:1px solid #c7d2fe;"\n            "border-radius:8px;padding:7px;font-size:12px;"\n        )\n        layout.addWidget(self.ai_context_label)\n\n        quick_row = QHBoxLayout()\n        quick_row.setSpacing(6)\n\n        quick_questions = [\n            "Почему здесь такая цена?",\n            "Дорого это для района?",\n            "Что рядом влияет на цену?",\n        ]\n\n        for question in quick_questions:\n            btn = QPushButton(question)\n            btn.setMinimumHeight(30)\n            btn.setStyleSheet("font-size:11px;padding:4px 8px;")\n            btn.clicked.connect(lambda checked=False, text=question: self._quick_question(text))\n            quick_row.addWidget(btn)\n\n        layout.addLayout(quick_row)\n\n        input_row = QHBoxLayout()\n        input_row.setSpacing(6)\n\n        self.ai_input = QLineEdit()\n        self.ai_input.setPlaceholderText("Вопрос про выбранную недвижимость, цену, район или инфраструктуру...")\n        self.ai_input.setMinimumHeight(34)\n        self.ai_input.returnPressed.connect(self._ask_ai)\n        input_row.addWidget(self.ai_input, stretch=1)\n\n        self.ai_ask_btn = QPushButton("Спросить ИИ")\n        self.ai_ask_btn.setMinimumHeight(34)\n        self.ai_ask_btn.setMinimumWidth(95)\n        self.ai_ask_btn.clicked.connect(self._ask_ai)\n        input_row.addWidget(self.ai_ask_btn)\n\n        layout.addLayout(input_row)\n\n        self.ai_response = QTextEdit()\n        self.ai_response.setReadOnly(True)\n        self.ai_response.setAcceptRichText(True)\n        self.ai_response.setLineWrapMode(QTextEdit.WidgetWidth)\n        self.ai_response.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)\n        self.ai_response.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)\n        self.ai_response.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)\n        self.ai_response.setStyleSheet(\n            "QTextEdit { background:#ffffff; color:#111827; border:1px solid #d8dee9; "\n            "border-radius:10px; padding:10px; font-size:12px; }"\n            "QScrollBar:vertical { background:#f1f5f9; width:14px; border-radius:7px; }"\n            "QScrollBar::handle:vertical { background:#94a3b8; border-radius:7px; min-height:35px; }"\n        )\n        self.ai_response.setHtml(\n            "<div style=\'font-family:Segoe UI,sans-serif;color:#111827;background:#ffffff;\'>"\n            "<p style=\'color:#64748b\'>Выберите объект на карте и задайте вопрос о цене, районе или инфраструктуре.</p>"\n            "</div>"\n        )\n        layout.addWidget(self.ai_response, stretch=1)\n\n        return widget\n'
NEW_MAIN_FUNC = 'def main():\n    # Включаем совместимые флаги QtWebEngine\n    os.environ.setdefault(\n        "QTWEBENGINE_CHROMIUM_FLAGS",\n        "--disable-gpu --disable-gpu-compositing --ignore-certificate-errors --no-sandbox"\n    )\n\n    app = QApplication(sys.argv)\n    app.setApplicationName(APP_TITLE)\n    app.setApplicationVersion(APP_VERSION)\n    app.setStyle("Fusion")\n\n    window = MainWindow()\n    window.show()\n    sys.exit(app.exec())\n'

def method_bounds(source: str, method_name: str):
    matches = list(re.finditer(rf"(?m)^    def {re.escape(method_name)}\s*\(", source))
    if not matches:
        return None
    m = matches[0]
    next_m = re.search(r"(?m)^    def \w+\s*\(", source[m.end():])
    end = m.end() + next_m.start() if next_m else len(source)
    return m.start(), end

def replace_method(source: str, method_name: str, new_method: str) -> str:
    bounds = method_bounds(source, method_name)
    if not bounds:
        raise RuntimeError(f"Не найден метод {method_name}")
    start, end = bounds
    print(f"Replaced method: {method_name}")
    return source[:start] + new_method.rstrip() + "\n" + source[end:]

text = replace_method(text, "_load_data", NEW_LOAD_DATA)
text = replace_method(text, "_build_ai_tab", NEW_AI_TAB)

# Исправляем main() полностью
m = re.search(r"(?m)^def main\(\):", text)
if not m:
    raise RuntimeError("Не найден def main()")

end_marker = '\nif __name__ == "__main__":'
end = text.find(end_marker, m.start())
if end == -1:
    raise RuntimeError('Не найден блок if __name__ == "__main__"')

text = text[:m.start()] + NEW_MAIN_FUNC.rstrip() + "\n" + text[end:]
print("Replaced function: main")

# Дополнительная страховка: если где-то остался пустой try из-за комментариев, вставим pass.
lines = text.splitlines(True)

def indent_len(s):
    return len(s) - len(s.lstrip(" \t"))

def is_blank_or_comment(s):
    stripped = s.strip()
    return stripped == "" or stripped.startswith("#")

i = 0
inserted = 0
while i < len(lines):
    if lines[i].strip() == "try:":
        base = indent_len(lines[i])
        body_indent = lines[i][:base] + "    "
        j = i + 1
        while j < len(lines) and is_blank_or_comment(lines[j]):
            j += 1
        if j < len(lines):
            st = lines[j].strip()
            if indent_len(lines[j]) == base and (st.startswith("except") or st.startswith("finally") or st.startswith("else:")):
                lines.insert(i + 1, body_indent + "pass  # inserted repair\n")
                inserted += 1
                i += 2
                continue
    i += 1

if inserted:
    print("Inserted pass into empty try blocks:", inserted)

text = "".join(lines)
MAIN_PATH.write_text(text, encoding="utf-8")

try:
    py_compile.compile(str(MAIN_PATH), doraise=True)
    print("OK: main.py syntax fixed")
except Exception as e:
    print("Still has syntax error:", e)
    # показываем контекст
    lineno = getattr(e, "lineno", None)
    if lineno is None and hasattr(e, "exc_value"):
        lineno = getattr(e.exc_value, "lineno", None)
    if lineno:
        arr = MAIN_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        a = max(1, lineno - 8)
        b = min(len(arr), lineno + 8)
        print("Context:")
        for num in range(a, b + 1):
            marker = ">>>" if num == lineno else "   "
            print(f"{marker} {num}: {arr[num-1]}")
    raise

print("DONE. Run:")
print('$env:QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --disable-gpu-compositing --ignore-certificate-errors --no-sandbox"; python main.py')
