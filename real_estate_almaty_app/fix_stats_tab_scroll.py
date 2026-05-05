# -*- coding: utf-8 -*-
"""
fix_stats_tab_scroll.py

Исправляет вкладку "Статистика":
- убирает неудобную вложенную прокрутку;
- делает QTextEdit главным скроллируемым блоком;
- добавляет кнопки "Наверх" и "Вниз";
- включает постоянную вертикальную прокрутку;
- делает текст читаемым на белом фоне.

Запускать из корня проекта:
python fix_stats_tab_scroll.py
"""

from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("Не найден main.py. Запусти patch из корня проекта real_estate_almaty_app.")

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

backup = Path("main.py.backup_stats_scroll")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)


new_build_stats_tab = """    def _build_stats_tab(self) -> QWidget:
        \"""
        Вкладка статистики без вложенной прокрутки.
        Раньше внутри QScrollArea лежал QTextEdit, из-за этого прокрутка работала неудобно.
        Теперь QTextEdit сам является главным прокручиваемым блоком.
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
        self.stats_display.setMinimumHeight(500)
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
                min-height:30px;
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

        hint = QLabel("Подсказка: используй колесо мыши внутри этого блока или кнопки «Наверх / Вниз».")
        hint.setStyleSheet("color:#64748b;font-size:11px;background:#ffffff;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return widget
"""


def replace_method(source: str, method_name: str, new_code: str) -> str:
    pattern = rf"\\n    def {re.escape(method_name)}\\([^\\n]*\\):[\\s\\S]*?(?=\\n    def |\\n# ============================================================|\\Z)"
    source2, count = re.subn(pattern, "\\n" + new_code.rstrip() + "\\n", source, count=1)
    if count == 0:
        raise RuntimeError(f"Не найден метод {method_name} в main.py")
    print(f"OK: replaced {method_name}")
    return source2


text = replace_method(text, "_build_stats_tab", new_build_stats_tab)

# Дополнительно усиливаем читаемость HTML-статистики перед setHtml.
if "/* stats-readability-fix */" not in text:
    text = text.replace(
        "        self.stats_display.setHtml(html)",
        """        if isinstance(html, str):
            html = (
                "<style>/* stats-readability-fix */ "
                "body, div, p, td, th, span, li { color:#111827; } "
                "body { background:#ffffff; } "
                "table { width:100%; border-collapse:collapse; } "
                "td, th { padding:6px 8px; border-bottom:1px solid #e5e7eb; } "
                "h1, h2, h3 { color:#1a237e; } "
                "</style>" + html
            )
        self.stats_display.setHtml(html)"""
    )
    print("OK: added stats readability CSS before setHtml")

MAIN_PATH.write_text(text, encoding="utf-8")
print("DONE. Now run: python main.py")
