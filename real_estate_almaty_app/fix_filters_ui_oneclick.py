# -*- coding: utf-8 -*-
from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py not found. Run this file from the project folder.")

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

backup = Path("main.py.backup_filters_ui_oneclick")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

NEW_METHOD = '    def _build_filters_panel(self) -> QGroupBox:\n        # Clean spacious filter panel.\n        group = QGroupBox("🔎 Фильтры недвижимости")\n        group.setObjectName("filtersBox")\n        group.setFixedHeight(360)\n\n        outer = QVBoxLayout(group)\n        outer.setContentsMargins(18, 20, 18, 14)\n        outer.setSpacing(10)\n\n        header = QHBoxLayout()\n        header.setSpacing(10)\n\n        self.filter_result_label = QLabel("Показаны все объекты")\n        self.filter_result_label.setMinimumWidth(245)\n        self.filter_result_label.setStyleSheet(\n            "background:#eef2ff;color:#1e293b;border:1px solid #c7d2fe;"\n            "border-radius:10px;padding:8px 12px;font-size:12px;font-weight:bold;"\n        )\n        header.addWidget(self.filter_result_label)\n\n        hint = QLabel("Выбери параметры — карта покажет только подходящие квартиры")\n        hint.setStyleSheet("color:#475569;font-size:12px;background:transparent;")\n        header.addWidget(hint, stretch=1)\n\n        self.btn_apply_filters = QPushButton("Применить")\n        self.btn_apply_filters.setMinimumWidth(125)\n        self.btn_apply_filters.setMinimumHeight(36)\n        self.btn_apply_filters.clicked.connect(self._apply_filters)\n        header.addWidget(self.btn_apply_filters)\n\n        btn_reset = QPushButton("Сбросить")\n        btn_reset.setObjectName("resetBtn")\n        btn_reset.setMinimumWidth(115)\n        btn_reset.setMinimumHeight(36)\n        btn_reset.clicked.connect(self._reset_filters)\n        header.addWidget(btn_reset)\n\n        outer.addLayout(header)\n\n        def make_card(title_text):\n            card = QWidget()\n            card.setObjectName("filterCard")\n            card.setMinimumHeight(70)\n            card.setStyleSheet(\n                "QWidget#filterCard { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; }"\n                "QWidget#filterCard QLabel { background:transparent; border:none; color:#334155; }"\n            )\n            box = QVBoxLayout(card)\n            box.setContentsMargins(12, 8, 12, 10)\n            box.setSpacing(6)\n\n            title = QLabel(title_text)\n            title.setStyleSheet("font-size:12px;font-weight:800;color:#334155;background:transparent;border:none;")\n            box.addWidget(title)\n\n            return card, box\n\n        def setup_input(widget, min_width=120):\n            widget.setMinimumHeight(34)\n            widget.setMinimumWidth(min_width)\n            return widget\n\n        def add_combo(parent_layout, title, combo, min_width=230):\n            card, box = make_card(title)\n            setup_input(combo, min_width)\n            box.addWidget(combo)\n            parent_layout.addWidget(card, stretch=1)\n\n        def add_range(parent_layout, title, left_widget, right_widget, min_width=105):\n            card, box = make_card(title)\n            row = QHBoxLayout()\n            row.setSpacing(7)\n\n            lbl_from = QLabel("от")\n            lbl_from.setFixedWidth(20)\n            lbl_from.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")\n            row.addWidget(lbl_from)\n\n            setup_input(left_widget, min_width)\n            row.addWidget(left_widget)\n\n            lbl_to = QLabel("до")\n            lbl_to.setFixedWidth(20)\n            lbl_to.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")\n            row.addWidget(lbl_to)\n\n            setup_input(right_widget, min_width)\n            row.addWidget(right_widget)\n\n            row.addStretch()\n            box.addLayout(row)\n            parent_layout.addWidget(card, stretch=1)\n\n        row1 = QHBoxLayout()\n        row1.setSpacing(12)\n\n        self.filter_district = QComboBox()\n        self.filter_district.addItem("Все районы")\n        self.filter_district.currentTextChanged.connect(self._apply_filters)\n        add_combo(row1, "Район", self.filter_district, 230)\n\n        self.filter_microdistrict = QComboBox()\n        self.filter_microdistrict.addItem("Все микрорайоны")\n        self.filter_microdistrict.currentTextChanged.connect(self._apply_filters)\n        add_combo(row1, "Микрорайон", self.filter_microdistrict, 260)\n\n        self.filter_price_category = QComboBox()\n        self.filter_price_category.addItems([\n            "Все категории",\n            "🔴 ≥ 1 000 000 ₸/м²",\n            "🟠 700 000–1 000 000 ₸/м²",\n            "🟡 500 000–700 000 ₸/м²",\n            "🟢 300 000–500 000 ₸/м²",\n            "🔵 < 300 000 ₸/м²",\n        ])\n        self.filter_price_category.currentTextChanged.connect(self._apply_filters)\n        add_combo(row1, "Категория цены за м²", self.filter_price_category, 270)\n\n        outer.addLayout(row1)\n\n        row2 = QHBoxLayout()\n        row2.setSpacing(12)\n\n        self.filter_price_min = QDoubleSpinBox()\n        self.filter_price_min.setRange(0, 5000)\n        self.filter_price_min.setDecimals(1)\n        self.filter_price_min.setSingleStep(1)\n        self.filter_price_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_price_max = QDoubleSpinBox()\n        self.filter_price_max.setRange(0, 5000)\n        self.filter_price_max.setDecimals(1)\n        self.filter_price_max.setSingleStep(1)\n        self.filter_price_max.valueChanged.connect(self._apply_filters)\n\n        add_range(row2, "Цена квартиры, млн ₸", self.filter_price_min, self.filter_price_max, 110)\n\n        self.filter_ppm2_min = QSpinBox()\n        self.filter_ppm2_min.setRange(0, 5000)\n        self.filter_ppm2_min.setSingleStep(50)\n        self.filter_ppm2_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_ppm2_max = QSpinBox()\n        self.filter_ppm2_max.setRange(0, 5000)\n        self.filter_ppm2_max.setSingleStep(50)\n        self.filter_ppm2_max.valueChanged.connect(self._apply_filters)\n\n        add_range(row2, "Цена за м², тыс ₸", self.filter_ppm2_min, self.filter_ppm2_max, 110)\n\n        self.filter_sq_min = QSpinBox()\n        self.filter_sq_min.setRange(0, 10000)\n        self.filter_sq_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_sq_max = QSpinBox()\n        self.filter_sq_max.setRange(0, 10000)\n        self.filter_sq_max.valueChanged.connect(self._apply_filters)\n\n        add_range(row2, "Площадь, м²", self.filter_sq_min, self.filter_sq_max, 110)\n\n        outer.addLayout(row2)\n\n        row3 = QHBoxLayout()\n        row3.setSpacing(12)\n\n        self.filter_rooms_min = QSpinBox()\n        self.filter_rooms_min.setRange(0, 20)\n        self.filter_rooms_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_rooms_max = QSpinBox()\n        self.filter_rooms_max.setRange(0, 20)\n        self.filter_rooms_max.valueChanged.connect(self._apply_filters)\n\n        add_range(row3, "Комнаты", self.filter_rooms_min, self.filter_rooms_max, 110)\n\n        self.filter_year_min = QSpinBox()\n        self.filter_year_min.setRange(1900, 2035)\n        self.filter_year_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_year_max = QSpinBox()\n        self.filter_year_max.setRange(1900, 2035)\n        self.filter_year_max.valueChanged.connect(self._apply_filters)\n\n        add_range(row3, "Год постройки", self.filter_year_min, self.filter_year_max, 110)\n\n        card, box = make_card("Дополнительно")\n        options = QHBoxLayout()\n        options.setSpacing(12)\n\n        self.chk_expensive = QCheckBox("Только дорогие 🔴")\n        self.chk_expensive.stateChanged.connect(self._apply_filters)\n        options.addWidget(self.chk_expensive)\n\n        self.chk_heatmap = QCheckBox("Тепловая карта")\n        self.chk_heatmap.stateChanged.connect(self._on_heatmap_changed)\n        options.addWidget(self.chk_heatmap)\n\n        self.chk_clusters = QCheckBox("Кластеры")\n        self.chk_clusters.stateChanged.connect(self._on_clusters_changed)\n        options.addWidget(self.chk_clusters)\n\n        self.chk_suspicious = QCheckBox("Вне Алматы")\n        self.chk_suspicious.stateChanged.connect(self._apply_filters)\n        options.addWidget(self.chk_suspicious)\n\n        options.addStretch()\n        box.addLayout(options)\n        row3.addWidget(card, stretch=1)\n\n        outer.addLayout(row3)\n\n        return group\n'
CSS = '\n/* filters-ui-oneclick-fix */\nQGroupBox#filtersBox {\n    background:#ffffff;\n    border:1px solid #d8dee9;\n    border-radius:16px;\n    margin-top:8px;\n    padding:12px;\n    color:#111827;\n}\nQGroupBox#filtersBox::title {\n    color:#1a237e;\n    font-size:14px;\n    font-weight:800;\n    padding:0 8px;\n    background:#ffffff;\n}\nQGroupBox#filtersBox QComboBox,\nQGroupBox#filtersBox QSpinBox,\nQGroupBox#filtersBox QDoubleSpinBox {\n    background:#ffffff;\n    color:#111827;\n    border:1px solid #cbd5e1;\n    border-radius:8px;\n    padding:4px 8px;\n    min-height:32px;\n    font-size:12px;\n}\nQGroupBox#filtersBox QComboBox QAbstractItemView {\n    background:#ffffff;\n    color:#111827;\n    selection-background-color:#1976d2;\n    selection-color:#ffffff;\n}\nQGroupBox#filtersBox QLabel {\n    color:#111827;\n}\nQGroupBox#filtersBox QCheckBox {\n    color:#111827;\n    font-size:12px;\n    background:transparent;\n}\n'

def add_css(s: str) -> str:
    if "/* filters-ui-oneclick-fix */" in s:
        print("CSS already exists")
        return s

    marker = 'STYLE_SHEET = ' + chr(34) * 3
    idx = s.find(marker)
    if idx != -1:
        end = s.find(chr(34) * 3, idx + len(marker))
        if end != -1:
            print("OK: CSS inserted into STYLE_SHEET")
            return s[:end] + CSS + "\n" + s[end:]

    print("WARNING: STYLE_SHEET not found; CSS not inserted")
    return s

def method_bounds(s: str, name: str):
    matches = list(re.finditer(rf"(?m)^    def {re.escape(name)}\s*\(", s))
    bounds = []
    for m in matches:
        next_m = re.search(r"(?m)^    def \w+\s*\(", s[m.end():])
        end = m.end() + next_m.start() if next_m else len(s)
        bounds.append((m.start(), end))
    return bounds

bounds = method_bounds(text, "_build_filters_panel")
print("Found _build_filters_panel:", len(bounds))

for start, end in reversed(bounds):
    text = text[:start] + text[end:]

marker = "\n    def _init_filter_ranges"
if marker not in text:
    marker = "\n    def _build_right_panel"

if marker not in text:
    raise RuntimeError("Cannot find insertion point: _init_filter_ranges or _build_right_panel")

text = text.replace(marker, "\n" + NEW_METHOD.rstrip() + "\n" + marker, 1)
text = add_css(text)

MAIN_PATH.write_text(text, encoding="utf-8")

print("DONE: filters panel replaced with one clean version.")
print("Now run: python main.py")
