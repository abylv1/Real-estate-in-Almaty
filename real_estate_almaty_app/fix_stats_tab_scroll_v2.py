# -*- coding: utf-8 -*-
"""
fix_stats_tab_scroll_v2.py

Исправляет вкладку "Статистика":
- делает нормальную прокрутку;
- добавляет кнопки "Наверх" и "Вниз";
- делает текст читаемым;
- работает даже если предыдущий patch-файл не нашёл _build_stats_tab.

Запускать из корня проекта:
python fix_stats_tab_scroll_v2.py
"""

from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("Не найден main.py. Запусти patch из корня проекта real_estate_almaty_app.")

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

backup = Path("main.py.backup_stats_scroll_v2")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)


def ensure_imports(s: str) -> str:
    # Qt уже должен быть импортирован. QSizePolicy тоже обычно есть.
    # Если QTextEdit / QLabel / QPushButton уже используются, ничего не трогаем.
    if "QSizePolicy" not in s:
        s = s.replace(
            "QProgressBar,",
            "QProgressBar, QSizePolicy,"
        )
    return s


new_build_stats_tab = """    def _build_stats_tab(self) -> QWidget:
        \"""
        Исправленная вкладка статистики.
        Здесь QTextEdit сам отвечает за прокрутку, поэтому можно нормально
        спускаться вниз и читать весь текст.
        \"""
        widget = QWidget()
        widget.setStyleSheet("background:#ffffff;color:#111827;")

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()

        title = QLabel("📊 Статистика по недвижимости")
        title.setObjectName("sectionLabel")
        title.setStyleSheet("color:#1a237e;font-size:14px;font-weight:800;background:#ffffff;")
        header.addWidget(title)

        header.addStretch()

        btn_top = QPushButton("Наверх")
        btn_top.setMaximumWidth(90)
        btn_top.clicked.connect(lambda: self.stats_display.verticalScrollBar().setValue(0))
        header.addWidget(btn_top)

        btn_bottom = QPushButton("Вниз")
        btn_bottom.setMaximumWidth(80)
        btn_bottom.clicked.connect(
            lambda: self.stats_display.verticalScrollBar().setValue(
                self.stats_display.verticalScrollBar().maximum()
            )
        )
        header.addWidget(btn_bottom)

        layout.addLayout(header)

        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setAcceptRichText(True)
        self.stats_display.setLineWrapMode(QTextEdit.WidgetWidth)
        self.stats_display.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.stats_display.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.stats_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stats_display.setMinimumHeight(520)

        self.stats_display.setStyleSheet(\"\"\"
            QTextEdit {
                background:#ffffff;
                color:#111827;
                border:1px solid #d8dee9;
                border-radius:10px;
                padding:10px;
                font-size:12px;
                selection-background-color:#1976d2;
                selection-color:#ffffff;
            }
            QScrollBar:vertical {
                background:#f1f5f9;
                width:14px;
                border-radius:7px;
                margin:0;
            }
            QScrollBar::handle:vertical {
                background:#94a3b8;
                border-radius:7px;
                min-height:35px;
            }
            QScrollBar::handle:vertical:hover {
                background:#64748b;
            }
        \"\"\")

        self.stats_display.setHtml(
            "<div style='font-family:Segoe UI,sans-serif;color:#111827;background:#ffffff;'>"
            "<p style='color:#64748b'>Загрузка статистики...</p>"
            "</div>"
        )

        layout.addWidget(self.stats_display, stretch=1)

        hint = QLabel("Подсказка: прокручивай колесом мыши внутри блока статистики или нажми «Вниз».")
        hint.setStyleSheet("color:#64748b;font-size:11px;background:#ffffff;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return widget
"""


def replace_method(s: str, method_name: str, new_code: str):
    # Правильный шаблон: ищем настоящий перенос строки, а не символы "\\n".
    pattern = rf"\n    def {re.escape(method_name)}\([^\n]*\):[\s\S]*?(?=\n    def |\n# ============================================================|\Z)"
    s2, count = re.subn(pattern, "\n" + new_code.rstrip() + "\n", s, count=1)
    return s2, count


text = ensure_imports(text)

text2, count = replace_method(text, "_build_stats_tab", new_build_stats_tab)

if count == 0:
    print("Метод _build_stats_tab не найден. Пробую найти место, где создаётся вкладка статистики...")

    # Если метода нет, добавляем его перед _build_ai_tab или перед блоком ИИ.
    insert_markers = [
        "\n    def _build_ai_tab",
        "\n    # --------------------------------------------------------\n    # ИИ-ассистент",
        "\n    def _update_stats_panel",
    ]

    inserted = False
    for marker in insert_markers:
        if marker in text:
            text2 = text.replace(marker, "\n" + new_build_stats_tab.rstrip() + "\n" + marker, 1)
            inserted = True
            print("OK: _build_stats_tab добавлен заново.")
            break

    if not inserted:
        raise RuntimeError("Не смог найти место для вставки _build_stats_tab. Отправь мне кусок main.py с _build_right_panel.")
else:
    print("OK: _build_stats_tab заменён.")

text = text2

# Убедимся, что _build_right_panel вызывает именно _build_stats_tab()
if "self.tabs.addTab(self._build_stats_tab(), \"📊 Статистика\")" not in text:
    # Иногда название вкладки без эмодзи или другой текст. Меняем строку со Статистика.
    text, count2 = re.subn(
        r'self\.tabs\.addTab\([^,\n]*stats[^,\n]*,\s*"[^"]*Статистика[^"]*"\)',
        'self.tabs.addTab(self._build_stats_tab(), "📊 Статистика")',
        text,
        count=1,
        flags=re.IGNORECASE
    )
    if count2:
        print("OK: вызов вкладки статистики исправлен.")

# Усиливаем читаемость перед setHtml(html), если ещё не добавляли.
if "/* stats-readability-fix-v2 */" not in text:
    text = text.replace(
        "        self.stats_display.setHtml(html)",
        """        if isinstance(html, str):
            html = (
                "<style>/* stats-readability-fix-v2 */ "
                "body, div, p, td, th, span, li { color:#111827; } "
                "body { background:#ffffff; } "
                "table { width:100%; border-collapse:collapse; } "
                "td, th { padding:6px 8px; border-bottom:1px solid #e5e7eb; } "
                "h1, h2, h3 { color:#1a237e; } "
                "</style>" + html
            )
        self.stats_display.setHtml(html)"""
    )
    print("OK: добавлен CSS для читаемости статистики.")

MAIN_PATH.write_text(text, encoding="utf-8")
print("DONE. Now run: python main.py")
