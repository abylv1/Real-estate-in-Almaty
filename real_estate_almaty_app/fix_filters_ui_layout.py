# -*- coding: utf-8 -*-
"""
fix_filters_ui_layout.py

Улучшает визуальный интерфейс блока "Фильтры недвижимости":
- делает панель выше и просторнее;
- разделяет фильтры на понятные строки;
- увеличивает ширину ComboBox и SpinBox;
- добавляет подписи "от / до";
- делает кнопки и чекбоксы аккуратнее;
- НЕ меняет саму логику фильтрации.

Запускать из корня проекта:
python fix_filters_ui_layout.py
"""

from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("Не найден main.py. Запусти patch из корня проекта real_estate_almaty_app.")

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

backup = Path("main.py.backup_filters_ui_layout")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)


def ensure_imports(s: str) -> str:
    if "QGridLayout" not in s:
        s = s.replace(
            "QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,",
            "QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,"
        )
    return s


new_build_filters_panel = """    def _build_filters_panel(self) -> QGroupBox:
        \"""
        Просторная и читаемая панель фильтров.
        Логика фильтрации остаётся прежней: все элементы подключены к _apply_filters.
        \"""
        group = QGroupBox("🔎 Фильтры недвижимости")
        group.setObjectName("filtersBox")
        group.setMinimumHeight(245)
        group.setMaximumHeight(285)

        outer = QVBoxLayout(group)
        outer.setContentsMargins(14, 16, 14, 12)
        outer.setSpacing(10)

        # Верхняя строка: статус + кнопки
        header = QHBoxLayout()
        header.setSpacing(10)

        title = QLabel("Настрой параметры поиска квартир")
        title.setStyleSheet("color:#0f172a;font-size:14px;font-weight:800;background:transparent;")
        header.addWidget(title)

        header.addStretch()

        self.filter_result_label = QLabel("Показаны все объекты")
        self.filter_result_label.setMinimumWidth(190)
        self.filter_result_label.setStyleSheet(
            "background:#eef2ff;color:#1e293b;border:1px solid #c7d2fe;"
            "border-radius:10px;padding:6px 12px;font-size:12px;font-weight:bold;"
        )
        header.addWidget(self.filter_result_label)

        self.btn_apply_filters = QPushButton("Применить")
        self.btn_apply_filters.setMinimumWidth(110)
        self.btn_apply_filters.clicked.connect(self._apply_filters)
        header.addWidget(self.btn_apply_filters)

        btn_reset = QPushButton("Сбросить")
        btn_reset.setObjectName("resetBtn")
        btn_reset.setMinimumWidth(100)
        btn_reset.clicked.connect(self._reset_filters)
        header.addWidget(btn_reset)

        outer.addLayout(header)

        # Основная сетка
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        outer.addLayout(grid)

        def make_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("color:#334155;font-size:12px;font-weight:700;background:transparent;")
            lbl.setMinimumHeight(18)
            return lbl

        def make_range_box(left_widget, right_widget, left_text="от", right_text="до"):
            box = QHBoxLayout()
            box.setSpacing(6)

            l1 = QLabel(left_text)
            l1.setStyleSheet("color:#64748b;font-size:11px;")
            l1.setMinimumWidth(18)
            box.addWidget(l1)

            left_widget.setMinimumWidth(92)
            left_widget.setMaximumWidth(125)
            box.addWidget(left_widget)

            l2 = QLabel(right_text)
            l2.setStyleSheet("color:#64748b;font-size:11px;")
            l2.setMinimumWidth(18)
            box.addWidget(l2)

            right_widget.setMinimumWidth(92)
            right_widget.setMaximumWidth(125)
            box.addWidget(right_widget)

            box.addStretch()
            return box

        # ====================================================
        # 1-я строка: район / микрорайон / категория
        # ====================================================
        grid.addWidget(make_label("Район"), 0, 0)
        self.filter_district = QComboBox()
        self.filter_district.addItem("Все районы")
        self.filter_district.setMinimumWidth(190)
        self.filter_district.setMinimumHeight(32)
        self.filter_district.currentTextChanged.connect(self._apply_filters)
        grid.addWidget(self.filter_district, 1, 0)

        grid.addWidget(make_label("Микрорайон"), 0, 1)
        self.filter_microdistrict = QComboBox()
        self.filter_microdistrict.addItem("Все микрорайоны")
        self.filter_microdistrict.setMinimumWidth(210)
        self.filter_microdistrict.setMinimumHeight(32)
        self.filter_microdistrict.currentTextChanged.connect(self._apply_filters)
        grid.addWidget(self.filter_microdistrict, 1, 1)

        grid.addWidget(make_label("Категория цены за м²"), 0, 2)
        self.filter_price_category = QComboBox()
        self.filter_price_category.addItems([
            "Все категории",
            "🔴 ≥ 1 000 000 ₸/м²",
            "🟠 700 000–1 000 000 ₸/м²",
            "🟡 500 000–700 000 ₸/м²",
            "🟢 300 000–500 000 ₸/м²",
            "🔵 < 300 000 ₸/м²",
        ])
        self.filter_price_category.setMinimumWidth(220)
        self.filter_price_category.setMinimumHeight(32)
        self.filter_price_category.currentTextChanged.connect(self._apply_filters)
        grid.addWidget(self.filter_price_category, 1, 2)

        # ====================================================
        # 2-я строка: цена квартиры / цена за м²
        # ====================================================
        grid.addWidget(make_label("Цена квартиры, млн ₸"), 2, 0)
        self.filter_price_min = QDoubleSpinBox()
        self.filter_price_min.setRange(0, 5000)
        self.filter_price_min.setDecimals(1)
        self.filter_price_min.setSingleStep(1)
        self.filter_price_min.valueChanged.connect(self._apply_filters)

        self.filter_price_max = QDoubleSpinBox()
        self.filter_price_max.setRange(0, 5000)
        self.filter_price_max.setDecimals(1)
        self.filter_price_max.setSingleStep(1)
        self.filter_price_max.valueChanged.connect(self._apply_filters)

        grid.addLayout(make_range_box(self.filter_price_min, self.filter_price_max), 3, 0)

        grid.addWidget(make_label("Цена за м², тыс ₸"), 2, 1)
        self.filter_ppm2_min = QSpinBox()
        self.filter_ppm2_min.setRange(0, 5000)
        self.filter_ppm2_min.setSingleStep(50)
        self.filter_ppm2_min.valueChanged.connect(self._apply_filters)

        self.filter_ppm2_max = QSpinBox()
        self.filter_ppm2_max.setRange(0, 5000)
        self.filter_ppm2_max.setSingleStep(50)
        self.filter_ppm2_max.valueChanged.connect(self._apply_filters)

        grid.addLayout(make_range_box(self.filter_ppm2_min, self.filter_ppm2_max), 3, 1)

        # ====================================================
        # 3-я строка: комнаты / год / площадь
        # ====================================================
        grid.addWidget(make_label("Комнаты"), 4, 0)
        self.filter_rooms_min = QSpinBox()
        self.filter_rooms_min.setRange(0, 20)
        self.filter_rooms_min.valueChanged.connect(self._apply_filters)

        self.filter_rooms_max = QSpinBox()
        self.filter_rooms_max.setRange(0, 20)
        self.filter_rooms_max.valueChanged.connect(self._apply_filters)

        grid.addLayout(make_range_box(self.filter_rooms_min, self.filter_rooms_max), 5, 0)

        grid.addWidget(make_label("Год постройки"), 4, 1)
        self.filter_year_min = QSpinBox()
        self.filter_year_min.setRange(1900, 2035)
        self.filter_year_min.valueChanged.connect(self._apply_filters)

        self.filter_year_max = QSpinBox()
        self.filter_year_max.setRange(1900, 2035)
        self.filter_year_max.valueChanged.connect(self._apply_filters)

        grid.addLayout(make_range_box(self.filter_year_min, self.filter_year_max), 5, 1)

        grid.addWidget(make_label("Площадь, м²"), 4, 2)
        self.filter_sq_min = QSpinBox()
        self.filter_sq_min.setRange(0, 10000)
        self.filter_sq_min.valueChanged.connect(self._apply_filters)

        self.filter_sq_max = QSpinBox()
        self.filter_sq_max.setRange(0, 10000)
        self.filter_sq_max.valueChanged.connect(self._apply_filters)

        grid.addLayout(make_range_box(self.filter_sq_min, self.filter_sq_max), 5, 2)

        # Растяжение колонок
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # Чекбоксы отдельной строкой
        checks = QHBoxLayout()
        checks.setSpacing(18)

        self.chk_expensive = QCheckBox("Только дорогие 🔴")
        self.chk_expensive.stateChanged.connect(self._apply_filters)
        checks.addWidget(self.chk_expensive)

        self.chk_heatmap = QCheckBox("Тепловая карта")
        self.chk_heatmap.stateChanged.connect(self._on_heatmap_changed)
        checks.addWidget(self.chk_heatmap)

        self.chk_clusters = QCheckBox("Кластеры")
        self.chk_clusters.stateChanged.connect(self._on_clusters_changed)
        checks.addWidget(self.chk_clusters)

        self.chk_suspicious = QCheckBox("Показывать вне Алматы")
        self.chk_suspicious.stateChanged.connect(self._apply_filters)
        checks.addWidget(self.chk_suspicious)

        checks.addStretch()
        outer.addLayout(checks)

        return group
"""


def replace_method(source: str, name: str, new_code: str) -> str:
    pattern = rf"\n    def {re.escape(name)}\([^\n]*\):[\s\S]*?(?=\n    def |\n# ============================================================|\Z)"
    source2, count = re.subn(pattern, "\n" + new_code.rstrip() + "\n", source, count=1)
    if count == 0:
        raise RuntimeError(f"Не найден метод {name} в main.py")
    print(f"OK: replaced {name}")
    return source2


text = ensure_imports(text)

# Добавляем улучшенные стили фильтров
style_marker = "/* filters-ui-layout-fix */"
if style_marker not in text:
    css = """
/* filters-ui-layout-fix */
QGroupBox#filtersBox {
    background:#ffffff;
    border:1px solid #d8dee9;
    border-radius:14px;
    margin-top:8px;
    padding:12px;
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
    border-radius:7px;
    padding:4px 8px;
    min-height:28px;
    font-size:12px;
}
QGroupBox#filtersBox QComboBox QAbstractItemView {
    background:#ffffff;
    color:#111827;
    selection-background-color:#1976d2;
    selection-color:#ffffff;
}
QGroupBox#filtersBox QLabel {
    color:#111827;
}
QGroupBox#filtersBox QCheckBox {
    color:#111827;
    font-size:12px;
    background:transparent;
}
"""
    # Пытаемся вставить внутрь STYLE_SHEET перед последними тройными кавычками
    idx = text.find('STYLE_SHEET = """')
    if idx != -1:
        end = text.find('"""', idx + len('STYLE_SHEET = """'))
        if end != -1:
            text = text[:end] + css + "\n" + text[end:]
            print("OK: filter CSS added")
        else:
            print("NOTE: STYLE_SHEET end not found")
    else:
        print("NOTE: STYLE_SHEET not found")

text = replace_method(text, "_build_filters_panel", new_build_filters_panel)

MAIN_PATH.write_text(text, encoding="utf-8")
print("DONE. Now run: python main.py")
