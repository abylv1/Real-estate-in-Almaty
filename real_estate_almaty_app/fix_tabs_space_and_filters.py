# -*- coding: utf-8 -*-
from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")
if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py not found. Run this file from the project folder.")

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

backup = Path("main.py.backup_tabs_space_fix")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

FILTERS_METHOD = '    def _build_filters_panel(self) -> QGroupBox:\n        # Compact filter panel: no "Дополнительно" card, more space for right tabs below.\n        group = QGroupBox("🔎 Фильтры недвижимости")\n        group.setObjectName("filtersBox")\n        group.setFixedHeight(245)\n\n        outer = QVBoxLayout(group)\n        outer.setContentsMargins(14, 16, 14, 10)\n        outer.setSpacing(8)\n\n        # Header\n        header = QHBoxLayout()\n        header.setSpacing(10)\n\n        self.filter_result_label = QLabel("Показаны все объекты")\n        self.filter_result_label.setMinimumWidth(220)\n        self.filter_result_label.setStyleSheet(\n            "background:#eef2ff;color:#1e293b;border:1px solid #c7d2fe;"\n            "border-radius:10px;padding:7px 12px;font-size:12px;font-weight:bold;"\n        )\n        header.addWidget(self.filter_result_label)\n\n        header.addStretch()\n\n        self.chk_expensive = QCheckBox("Только дорогие 🔴")\n        self.chk_expensive.stateChanged.connect(self._apply_filters)\n        header.addWidget(self.chk_expensive)\n\n        self.chk_heatmap = QCheckBox("Тепловая карта")\n        self.chk_heatmap.stateChanged.connect(self._on_heatmap_changed)\n        header.addWidget(self.chk_heatmap)\n\n        self.chk_clusters = QCheckBox("Кластеры")\n        self.chk_clusters.stateChanged.connect(self._on_clusters_changed)\n        header.addWidget(self.chk_clusters)\n\n        self.chk_suspicious = QCheckBox("Вне Алматы")\n        self.chk_suspicious.stateChanged.connect(self._apply_filters)\n        header.addWidget(self.chk_suspicious)\n\n        self.btn_apply_filters = QPushButton("Применить")\n        self.btn_apply_filters.setMinimumSize(115, 34)\n        self.btn_apply_filters.clicked.connect(self._apply_filters)\n        header.addWidget(self.btn_apply_filters)\n\n        btn_reset = QPushButton("Сбросить")\n        btn_reset.setObjectName("resetBtn")\n        btn_reset.setMinimumSize(105, 34)\n        btn_reset.clicked.connect(self._reset_filters)\n        header.addWidget(btn_reset)\n\n        outer.addLayout(header)\n\n        def make_card(title_text):\n            card = QWidget()\n            card.setObjectName("filterCard")\n            card.setMinimumHeight(62)\n            card.setStyleSheet(\n                "QWidget#filterCard { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; }"\n                "QWidget#filterCard QLabel { background:transparent; border:none; color:#334155; }"\n            )\n            box = QVBoxLayout(card)\n            box.setContentsMargins(10, 6, 10, 8)\n            box.setSpacing(4)\n            title = QLabel(title_text)\n            title.setStyleSheet("font-size:12px;font-weight:800;color:#334155;background:transparent;border:none;")\n            box.addWidget(title)\n            return card, box\n\n        def setup_input(widget, min_width=100):\n            widget.setMinimumHeight(32)\n            widget.setMinimumWidth(min_width)\n            return widget\n\n        def add_combo(parent_layout, title, combo, min_width=200):\n            card, box = make_card(title)\n            setup_input(combo, min_width)\n            box.addWidget(combo)\n            parent_layout.addWidget(card, stretch=1)\n\n        def add_range(parent_layout, title, left_widget, right_widget, min_width=86):\n            card, box = make_card(title)\n            row = QHBoxLayout()\n            row.setSpacing(5)\n\n            lbl_from = QLabel("от")\n            lbl_from.setFixedWidth(18)\n            lbl_from.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")\n            row.addWidget(lbl_from)\n\n            setup_input(left_widget, min_width)\n            row.addWidget(left_widget)\n\n            lbl_to = QLabel("до")\n            lbl_to.setFixedWidth(18)\n            lbl_to.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")\n            row.addWidget(lbl_to)\n\n            setup_input(right_widget, min_width)\n            row.addWidget(right_widget)\n\n            row.addStretch()\n            box.addLayout(row)\n            parent_layout.addWidget(card, stretch=1)\n\n        # Row 1\n        row1 = QHBoxLayout()\n        row1.setSpacing(10)\n\n        self.filter_district = QComboBox()\n        self.filter_district.addItem("Все районы")\n        self.filter_district.currentTextChanged.connect(self._apply_filters)\n        add_combo(row1, "Район", self.filter_district, 210)\n\n        self.filter_microdistrict = QComboBox()\n        self.filter_microdistrict.addItem("Все микрорайоны")\n        self.filter_microdistrict.currentTextChanged.connect(self._apply_filters)\n        add_combo(row1, "Микрорайон", self.filter_microdistrict, 230)\n\n        self.filter_price_category = QComboBox()\n        self.filter_price_category.addItems([\n            "Все категории",\n            "🔴 ≥ 1 000 000 ₸/м²",\n            "🟠 700 000–1 000 000 ₸/м²",\n            "🟡 500 000–700 000 ₸/м²",\n            "🟢 300 000–500 000 ₸/м²",\n            "🔵 < 300 000 ₸/м²",\n        ])\n        self.filter_price_category.currentTextChanged.connect(self._apply_filters)\n        add_combo(row1, "Категория цены за м²", self.filter_price_category, 230)\n\n        outer.addLayout(row1)\n\n        # Row 2: all ranges in one line\n        row2 = QHBoxLayout()\n        row2.setSpacing(10)\n\n        self.filter_price_min = QDoubleSpinBox()\n        self.filter_price_min.setRange(0, 5000)\n        self.filter_price_min.setDecimals(1)\n        self.filter_price_min.setSingleStep(1)\n        self.filter_price_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_price_max = QDoubleSpinBox()\n        self.filter_price_max.setRange(0, 5000)\n        self.filter_price_max.setDecimals(1)\n        self.filter_price_max.setSingleStep(1)\n        self.filter_price_max.valueChanged.connect(self._apply_filters)\n        add_range(row2, "Цена квартиры, млн ₸", self.filter_price_min, self.filter_price_max, 84)\n\n        self.filter_ppm2_min = QSpinBox()\n        self.filter_ppm2_min.setRange(0, 5000)\n        self.filter_ppm2_min.setSingleStep(50)\n        self.filter_ppm2_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_ppm2_max = QSpinBox()\n        self.filter_ppm2_max.setRange(0, 5000)\n        self.filter_ppm2_max.setSingleStep(50)\n        self.filter_ppm2_max.valueChanged.connect(self._apply_filters)\n        add_range(row2, "Цена за м², тыс ₸", self.filter_ppm2_min, self.filter_ppm2_max, 84)\n\n        self.filter_rooms_min = QSpinBox()\n        self.filter_rooms_min.setRange(0, 20)\n        self.filter_rooms_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_rooms_max = QSpinBox()\n        self.filter_rooms_max.setRange(0, 20)\n        self.filter_rooms_max.valueChanged.connect(self._apply_filters)\n        add_range(row2, "Комнаты", self.filter_rooms_min, self.filter_rooms_max, 70)\n\n        self.filter_year_min = QSpinBox()\n        self.filter_year_min.setRange(1900, 2035)\n        self.filter_year_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_year_max = QSpinBox()\n        self.filter_year_max.setRange(1900, 2035)\n        self.filter_year_max.valueChanged.connect(self._apply_filters)\n        add_range(row2, "Год постройки", self.filter_year_min, self.filter_year_max, 78)\n\n        self.filter_sq_min = QSpinBox()\n        self.filter_sq_min.setRange(0, 10000)\n        self.filter_sq_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_sq_max = QSpinBox()\n        self.filter_sq_max.setRange(0, 10000)\n        self.filter_sq_max.valueChanged.connect(self._apply_filters)\n        add_range(row2, "Площадь, м²", self.filter_sq_min, self.filter_sq_max, 78)\n\n        outer.addLayout(row2)\n\n        return group\n'
STATS_METHOD = '    def _build_stats_tab(self) -> QWidget:\n        # Statistics tab with full vertical space. No bottom hint.\n        widget = QWidget()\n        widget.setStyleSheet("background:#ffffff;color:#111827;")\n\n        layout = QVBoxLayout(widget)\n        layout.setContentsMargins(8, 8, 8, 8)\n        layout.setSpacing(6)\n\n        header = QHBoxLayout()\n        title = QLabel("📊 Статистика по недвижимости")\n        title.setObjectName("sectionLabel")\n        title.setStyleSheet("color:#1a237e;font-size:14px;font-weight:800;background:#ffffff;")\n        header.addWidget(title)\n        header.addStretch()\n\n        btn_top = QPushButton("Наверх")\n        btn_top.setMaximumWidth(90)\n        btn_top.clicked.connect(lambda: self.stats_display.verticalScrollBar().setValue(0))\n        header.addWidget(btn_top)\n\n        btn_bottom = QPushButton("Вниз")\n        btn_bottom.setMaximumWidth(80)\n        btn_bottom.clicked.connect(\n            lambda: self.stats_display.verticalScrollBar().setValue(\n                self.stats_display.verticalScrollBar().maximum()\n            )\n        )\n        header.addWidget(btn_bottom)\n\n        layout.addLayout(header)\n\n        self.stats_display = QTextEdit()\n        self.stats_display.setReadOnly(True)\n        self.stats_display.setAcceptRichText(True)\n        self.stats_display.setLineWrapMode(QTextEdit.WidgetWidth)\n        self.stats_display.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)\n        self.stats_display.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)\n        self.stats_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)\n        self.stats_display.setStyleSheet(\n            "QTextEdit { background:#ffffff; color:#111827; border:1px solid #d8dee9; "\n            "border-radius:10px; padding:10px; font-size:12px; }"\n            "QScrollBar:vertical { background:#f1f5f9; width:14px; border-radius:7px; }"\n            "QScrollBar::handle:vertical { background:#94a3b8; border-radius:7px; min-height:35px; }"\n        )\n        self.stats_display.setHtml(\n            "<div style=\'font-family:Segoe UI,sans-serif;color:#111827;background:#ffffff;\'>"\n            "<p style=\'color:#64748b\'>Загрузка статистики...</p></div>"\n        )\n        layout.addWidget(self.stats_display, stretch=1)\n\n        return widget\n'
AI_METHOD = '    def _build_ai_tab(self) -> QWidget:\n        # Compact AI assistant tab with maximum response space.\n        widget = QWidget()\n        widget.setStyleSheet("background:#ffffff;color:#111827;")\n\n        layout = QVBoxLayout(widget)\n        layout.setContentsMargins(8, 8, 8, 8)\n        layout.setSpacing(6)\n\n        title = QLabel("🤖 ИИ-ассистент по недвижимости")\n        title.setObjectName("sectionLabel")\n        title.setStyleSheet("color:#1a237e;font-size:14px;font-weight:800;background:#ffffff;")\n        layout.addWidget(title)\n\n        self.ai_context_label = QLabel("Сначала выберите объект на карте")\n        self.ai_context_label.setWordWrap(True)\n        self.ai_context_label.setMaximumHeight(62)\n        self.ai_context_label.setStyleSheet(\n            "background:#eef2ff;color:#111827;border:1px solid #c7d2fe;"\n            "border-radius:8px;padding:7px;font-size:12px;"\n        )\n        layout.addWidget(self.ai_context_label)\n\n        quick_row = QHBoxLayout()\n        quick_row.setSpacing(6)\n\n        def ask_text(text):\n            self.ai_input.setText(text)\n            if hasattr(self, "_ask_ai_question"):\n                self._ask_ai_question()\n\n        quick_questions = [\n            "Почему здесь такая цена?",\n            "Дорого это для района?",\n            "Что рядом влияет на цену?",\n        ]\n\n        for q in quick_questions:\n            btn = QPushButton(q)\n            btn.setMinimumHeight(30)\n            btn.setStyleSheet("font-size:11px;padding:4px 8px;")\n            btn.clicked.connect(lambda checked=False, text=q: ask_text(text))\n            quick_row.addWidget(btn)\n\n        layout.addLayout(quick_row)\n\n        input_row = QHBoxLayout()\n        input_row.setSpacing(6)\n\n        self.ai_input = QLineEdit()\n        self.ai_input.setPlaceholderText("Задайте вопрос только про выбранную недвижимость, цену, район или инфраструктуру...")\n        self.ai_input.setMinimumHeight(34)\n        self.ai_input.returnPressed.connect(lambda: self._ask_ai_question() if hasattr(self, "_ask_ai_question") else None)\n        input_row.addWidget(self.ai_input, stretch=1)\n\n        btn_ask = QPushButton("Спросить")\n        btn_ask.setMinimumHeight(34)\n        btn_ask.setMinimumWidth(95)\n        btn_ask.clicked.connect(lambda: self._ask_ai_question() if hasattr(self, "_ask_ai_question") else None)\n        input_row.addWidget(btn_ask)\n\n        layout.addLayout(input_row)\n\n        self.ai_response = QTextEdit()\n        self.ai_response.setReadOnly(True)\n        self.ai_response.setAcceptRichText(True)\n        self.ai_response.setLineWrapMode(QTextEdit.WidgetWidth)\n        self.ai_response.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)\n        self.ai_response.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)\n        self.ai_response.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)\n        self.ai_response.setStyleSheet(\n            "QTextEdit { background:#ffffff; color:#111827; border:1px solid #d8dee9; "\n            "border-radius:10px; padding:10px; font-size:12px; }"\n            "QScrollBar:vertical { background:#f1f5f9; width:14px; border-radius:7px; }"\n            "QScrollBar::handle:vertical { background:#94a3b8; border-radius:7px; min-height:35px; }"\n        )\n        self.ai_response.setHtml(\n            "<div style=\'font-family:Segoe UI,sans-serif;color:#111827;background:#ffffff;\'>"\n            "<p style=\'color:#64748b\'>Выберите объект на карте и задайте вопрос о цене, районе или инфраструктуре.</p>"\n            "</div>"\n        )\n        layout.addWidget(self.ai_response, stretch=1)\n\n        return widget\n'

CSS = """
/* tabs-space-filter-compact-fix */
QGroupBox#filtersBox {
    background:#ffffff;
    border:1px solid #d8dee9;
    border-radius:14px;
    margin-top:6px;
    padding:10px;
    color:#111827;
}
QGroupBox#filtersBox::title {
    color:#1a237e;
    font-size:14px;
    font-weight:800;
    padding:0 8px;
    background:#ffffff;
}
QGroupBox#filtersBox QComboBox,
QGroupBox#filtersBox QSpinBox,
QGroupBox#filtersBox QDoubleSpinBox {
    background:#ffffff;
    color:#111827;
    border:1px solid #cbd5e1;
    border-radius:8px;
    padding:3px 7px;
    min-height:30px;
    font-size:12px;
}
QGroupBox#filtersBox QCheckBox {
    color:#111827;
    font-size:12px;
    background:transparent;
}
"""

def ensure_qsizepolicy_import(s):
    if "QSizePolicy" in s:
        return s
    candidates = ["QProgressBar,", "QTextEdit,", "QScrollArea,", "QFrame,"]
    for c in candidates:
        if c in s:
            return s.replace(c, c + " QSizePolicy,", 1)
    return s

def method_bounds(s, name):
    matches = list(re.finditer(rf"(?m)^    def {re.escape(name)}\s*\(", s))
    bounds = []
    for m in matches:
        next_m = re.search(r"(?m)^    def \w+\s*\(", s[m.end():])
        end = m.end() + next_m.start() if next_m else len(s)
        bounds.append((m.start(), end))
    return bounds

def replace_all_methods(s, name, new_method, insert_before):
    bounds = method_bounds(s, name)
    print(f"Found {name}:", len(bounds))
    for start, end in reversed(bounds):
        s = s[:start] + s[end:]

    marker = "\n    def " + insert_before
    if marker not in s:
        raise RuntimeError(f"Cannot find insertion point: {insert_before}")
    return s.replace(marker, "\n" + new_method.rstrip() + "\n" + marker, 1)

def add_css(s):
    if "/* tabs-space-filter-compact-fix */" in s:
        return s
    marker = 'STYLE_SHEET = ' + chr(34) * 3
    idx = s.find(marker)
    if idx != -1:
        end = s.find(chr(34) * 3, idx + len(marker))
        if end != -1:
            print("OK: CSS inserted")
            return s[:end] + CSS + "\n" + s[end:]
    print("WARNING: STYLE_SHEET not found")
    return s

text = ensure_qsizepolicy_import(text)

# Replace duplicated/old UI methods with one clean version each.
text = replace_all_methods(text, "_build_filters_panel", FILTERS_METHOD, "_init_filter_ranges")
text = replace_all_methods(text, "_build_stats_tab", STATS_METHOD, "_build_ai_tab")
text = replace_all_methods(text, "_build_ai_tab", AI_METHOD, "_update_ai_context_panel" if "def _update_ai_context_panel" in text else "_ask_ai_question")

text = add_css(text)

MAIN_PATH.write_text(text, encoding="utf-8")

print("DONE: removed 'Дополнительно' filter card and expanded tabs space.")
print("Now run: python main.py")
