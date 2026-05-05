# -*- coding: utf-8 -*-
"""
fix_filters_ui_layout_v3.py

Полностью исправляет визуальный интерфейс блока "Фильтры недвижимости".
Запускать из корня проекта:
python fix_filters_ui_layout_v3.py
"""

from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("Не найден main.py. Запусти файл из корня проекта.")

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

backup = Path("main.py.backup_filters_ui_layout_v3")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

NEW_METHOD = '    def _build_filters_panel(self) -> QGroupBox:\n        """\n        Просторная панель фильтров без наложения текста и полей.\n        Логика фильтрации остаётся прежней: все элементы подключены к _apply_filters.\n        """\n        group = QGroupBox("🔎 Фильтры недвижимости")\n        group.setObjectName("filtersBox")\n        group.setFixedHeight(315)\n\n        outer = QVBoxLayout(group)\n        outer.setContentsMargins(16, 18, 16, 12)\n        outer.setSpacing(9)\n\n        # Верхняя строка: статус и кнопки\n        header = QHBoxLayout()\n        header.setSpacing(10)\n\n        self.filter_result_label = QLabel("Показаны все объекты")\n        self.filter_result_label.setMinimumWidth(230)\n        self.filter_result_label.setStyleSheet(\n            "background:#eef2ff;color:#1e293b;border:1px solid #c7d2fe;"\n            "border-radius:10px;padding:7px 12px;font-size:12px;font-weight:bold;"\n        )\n        header.addWidget(self.filter_result_label)\n\n        hint = QLabel("Выбери район, цену, комнаты, год или площадь — карта обновится по этим условиям")\n        hint.setStyleSheet("color:#475569;font-size:12px;background:transparent;")\n        header.addWidget(hint, stretch=1)\n\n        self.btn_apply_filters = QPushButton("Применить")\n        self.btn_apply_filters.setMinimumWidth(120)\n        self.btn_apply_filters.setMinimumHeight(34)\n        self.btn_apply_filters.clicked.connect(self._apply_filters)\n        header.addWidget(self.btn_apply_filters)\n\n        btn_reset = QPushButton("Сбросить")\n        btn_reset.setObjectName("resetBtn")\n        btn_reset.setMinimumWidth(110)\n        btn_reset.setMinimumHeight(34)\n        btn_reset.clicked.connect(self._reset_filters)\n        header.addWidget(btn_reset)\n\n        outer.addLayout(header)\n\n        def create_card(title_text):\n            card = QWidget()\n            card.setStyleSheet(\n                "QWidget { background:#f8fafc; border:1px solid #e2e8f0; "\n                "border-radius:10px; }"\n                "QLabel { border:none; background:transparent; color:#334155; }"\n            )\n            box = QVBoxLayout(card)\n            box.setContentsMargins(10, 7, 10, 9)\n            box.setSpacing(5)\n\n            title = QLabel(title_text)\n            title.setStyleSheet(\n                "color:#334155;font-size:12px;font-weight:700;background:transparent;border:none;"\n            )\n            box.addWidget(title)\n            return card, box\n\n        def setup_widget(w, min_width=150):\n            w.setMinimumHeight(34)\n            w.setMinimumWidth(min_width)\n            return w\n\n        def add_combo_card(row_layout, title_text, combo, min_width=210):\n            card, box = create_card(title_text)\n            setup_widget(combo, min_width)\n            box.addWidget(combo)\n            row_layout.addWidget(card, stretch=1)\n\n        def add_range_card(row_layout, title_text, left_widget, right_widget, min_width=95):\n            card, box = create_card(title_text)\n\n            range_row = QHBoxLayout()\n            range_row.setSpacing(7)\n\n            lbl_from = QLabel("от")\n            lbl_from.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")\n            lbl_from.setFixedWidth(18)\n            range_row.addWidget(lbl_from)\n\n            setup_widget(left_widget, min_width)\n            range_row.addWidget(left_widget)\n\n            lbl_to = QLabel("до")\n            lbl_to.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")\n            lbl_to.setFixedWidth(18)\n            range_row.addWidget(lbl_to)\n\n            setup_widget(right_widget, min_width)\n            range_row.addWidget(right_widget)\n\n            box.addLayout(range_row)\n            row_layout.addWidget(card, stretch=1)\n\n        # Строка 1: район / микрорайон / категория\n        row1 = QHBoxLayout()\n        row1.setSpacing(10)\n\n        self.filter_district = QComboBox()\n        self.filter_district.addItem("Все районы")\n        self.filter_district.currentTextChanged.connect(self._apply_filters)\n        add_combo_card(row1, "Район", self.filter_district, 220)\n\n        self.filter_microdistrict = QComboBox()\n        self.filter_microdistrict.addItem("Все микрорайоны")\n        self.filter_microdistrict.currentTextChanged.connect(self._apply_filters)\n        add_combo_card(row1, "Микрорайон", self.filter_microdistrict, 240)\n\n        self.filter_price_category = QComboBox()\n        self.filter_price_category.addItems([\n            "Все категории",\n            "🔴 ≥ 1 000 000 ₸/м²",\n            "🟠 700 000–1 000 000 ₸/м²",\n            "🟡 500 000–700 000 ₸/м²",\n            "🟢 300 000–500 000 ₸/м²",\n            "🔵 < 300 000 ₸/м²",\n        ])\n        self.filter_price_category.currentTextChanged.connect(self._apply_filters)\n        add_combo_card(row1, "Категория цены за м²", self.filter_price_category, 250)\n\n        outer.addLayout(row1)\n\n        # Строка 2: цена квартиры / цена за м² / площадь\n        row2 = QHBoxLayout()\n        row2.setSpacing(10)\n\n        self.filter_price_min = QDoubleSpinBox()\n        self.filter_price_min.setRange(0, 5000)\n        self.filter_price_min.setDecimals(1)\n        self.filter_price_min.setSingleStep(1)\n        self.filter_price_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_price_max = QDoubleSpinBox()\n        self.filter_price_max.setRange(0, 5000)\n        self.filter_price_max.setDecimals(1)\n        self.filter_price_max.setSingleStep(1)\n        self.filter_price_max.valueChanged.connect(self._apply_filters)\n\n        add_range_card(row2, "Цена квартиры, млн ₸", self.filter_price_min, self.filter_price_max, 95)\n\n        self.filter_ppm2_min = QSpinBox()\n        self.filter_ppm2_min.setRange(0, 5000)\n        self.filter_ppm2_min.setSingleStep(50)\n        self.filter_ppm2_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_ppm2_max = QSpinBox()\n        self.filter_ppm2_max.setRange(0, 5000)\n        self.filter_ppm2_max.setSingleStep(50)\n        self.filter_ppm2_max.valueChanged.connect(self._apply_filters)\n\n        add_range_card(row2, "Цена за м², тыс ₸", self.filter_ppm2_min, self.filter_ppm2_max, 95)\n\n        self.filter_sq_min = QSpinBox()\n        self.filter_sq_min.setRange(0, 10000)\n        self.filter_sq_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_sq_max = QSpinBox()\n        self.filter_sq_max.setRange(0, 10000)\n        self.filter_sq_max.valueChanged.connect(self._apply_filters)\n\n        add_range_card(row2, "Площадь, м²", self.filter_sq_min, self.filter_sq_max, 95)\n\n        outer.addLayout(row2)\n\n        # Строка 3: комнаты / год / режимы карты\n        row3 = QHBoxLayout()\n        row3.setSpacing(10)\n\n        self.filter_rooms_min = QSpinBox()\n        self.filter_rooms_min.setRange(0, 20)\n        self.filter_rooms_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_rooms_max = QSpinBox()\n        self.filter_rooms_max.setRange(0, 20)\n        self.filter_rooms_max.valueChanged.connect(self._apply_filters)\n\n        add_range_card(row3, "Комнаты", self.filter_rooms_min, self.filter_rooms_max, 95)\n\n        self.filter_year_min = QSpinBox()\n        self.filter_year_min.setRange(1900, 2035)\n        self.filter_year_min.valueChanged.connect(self._apply_filters)\n\n        self.filter_year_max = QSpinBox()\n        self.filter_year_max.setRange(1900, 2035)\n        self.filter_year_max.valueChanged.connect(self._apply_filters)\n\n        add_range_card(row3, "Год постройки", self.filter_year_min, self.filter_year_max, 95)\n\n        mode_card, mode_box = create_card("Дополнительно")\n        mode_row = QHBoxLayout()\n        mode_row.setSpacing(14)\n\n        self.chk_expensive = QCheckBox("Только дорогие 🔴")\n        self.chk_expensive.stateChanged.connect(self._apply_filters)\n        mode_row.addWidget(self.chk_expensive)\n\n        self.chk_heatmap = QCheckBox("Тепловая карта")\n        self.chk_heatmap.stateChanged.connect(self._on_heatmap_changed)\n        mode_row.addWidget(self.chk_heatmap)\n\n        self.chk_clusters = QCheckBox("Кластеры")\n        self.chk_clusters.stateChanged.connect(self._on_clusters_changed)\n        mode_row.addWidget(self.chk_clusters)\n\n        self.chk_suspicious = QCheckBox("Вне Алматы")\n        self.chk_suspicious.stateChanged.connect(self._apply_filters)\n        mode_row.addWidget(self.chk_suspicious)\n\n        mode_row.addStretch()\n        mode_box.addLayout(mode_row)\n\n        row3.addWidget(mode_card, stretch=1)\n        outer.addLayout(row3)\n\n        return group\n'
CSS = '\n/* filters-ui-layout-fix-v3 */\nQGroupBox#filtersBox {\n    background:#ffffff;\n    border:1px solid #d8dee9;\n    border-radius:14px;\n    margin-top:8px;\n    padding:12px;\n    color:#111827;\n}\nQGroupBox#filtersBox::title {\n    color:#1a237e;\n    font-size:14px;\n    font-weight:800;\n    padding:0 8px;\n    background:#ffffff;\n}\nQGroupBox#filtersBox QComboBox,\nQGroupBox#filtersBox QSpinBox,\nQGroupBox#filtersBox QDoubleSpinBox {\n    background:#ffffff;\n    color:#111827;\n    border:1px solid #cbd5e1;\n    border-radius:7px;\n    padding:4px 8px;\n    min-height:30px;\n    font-size:12px;\n}\nQGroupBox#filtersBox QComboBox QAbstractItemView {\n    background:#ffffff;\n    color:#111827;\n    selection-background-color:#1976d2;\n    selection-color:#ffffff;\n}\nQGroupBox#filtersBox QLabel {\n    color:#111827;\n}\nQGroupBox#filtersBox QCheckBox {\n    color:#111827;\n    font-size:12px;\n    background:transparent;\n}\n'


def find_method_bounds(s: str, method_name: str):
    m = re.search(rf"(?m)^([ \t]+)def {re.escape(method_name)}\s*\(", s)
    if not m:
        return None

    indent = m.group(1)
    start = m.start()
    rest = s[m.end():]

    next_m = re.search(rf"(?m)^{re.escape(indent)}def \w+\s*\(", rest)
    if next_m:
        end = m.end() + next_m.start()
    else:
        comment_m = re.search(rf"(?m)^# =+", rest)
        end = m.end() + comment_m.start() if comment_m else len(s)

    return start, end


def replace_or_insert_method(s: str) -> str:
    bounds = find_method_bounds(s, "_build_filters_panel")
    if bounds:
        start, end = bounds
        print("OK: found existing _build_filters_panel, replacing it")
        return s[:start] + NEW_METHOD.rstrip() + "\n" + s[end:]

    print("WARNING: _build_filters_panel not found. Inserting before _init_filter_ranges.")
    marker = "\n    def _init_filter_ranges"
    if marker in s:
        return s.replace(marker, "\n" + NEW_METHOD.rstrip() + "\n" + marker, 1)

    raise RuntimeError("Не удалось найти _build_filters_panel или _init_filter_ranges в main.py")


def add_css(s: str) -> str:
    if "/* filters-ui-layout-fix-v3 */" in s:
        print("CSS already exists")
        return s

    idx = s.find('STYLE_SHEET = """')
    if idx != -1:
        end = s.find('"""', idx + len('STYLE_SHEET = """'))
        if end != -1:
            print("OK: CSS inserted into STYLE_SHEET")
            return s[:end] + CSS + "\n" + s[end:]

    print("NOTE: STYLE_SHEET not found, CSS not inserted")
    return s


text = add_css(text)
text = replace_or_insert_method(text)

MAIN_PATH.write_text(text, encoding="utf-8")
print("DONE: filters UI layout updated")
print("Now run: python main.py")
