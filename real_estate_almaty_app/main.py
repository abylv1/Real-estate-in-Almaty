# -*- coding: utf-8 -*-
"""
Главный файл приложения: Анализ рынка недвижимости Алматы.
Запуск: python main.py
"""

import sys
import os

# ============================================================
# Stable QtWebEngine startup flags
# Must be before PySide6 / QWebEngine imports
# ============================================================
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-gpu-compositing --disable-logging --log-level=3 "
    "--ignore-certificate-errors --no-sandbox --disable-features=VizDisplayCompositor"
)
os.environ.setdefault(
    "QT_LOGGING_RULES",
    "qt.webenginecontext.debug=false;qt.webenginecontext.warning=false;qt.qpa.*=false"
)
# ============================================================


import json
import threading
import numpy as np
import pandas as pd

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QGroupBox,
    QScrollArea, QSplitter, QStatusBar, QMessageBox,
    QSlider, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QTabWidget, QFrame, QSizePolicy, QProgressBar,
)

from src.config import APP_TITLE, APP_VERSION, PRICE_COLORS
from src.data_loader import load_data, get_property_dict
from src.map_view import MapWidget
from src.geo_utils import determine_district, get_address, determine_microdistrict, get_nearby_places, get_all_microdistricts, get_microdistrict_center
from src.statistics import (
    compute_global_stats, compute_district_stats,
    get_property_percentile, get_district_avg, compare_to_average
)
from src.ai_assistant import answer_question

DISTRICT_FILTER_ITEMS = ['Алатауский', 'Алмалинский', 'Ауэзовский', 'Бостандыкский', 'Жетысуский', 'Медеуский', 'Наурызбайский', 'Турксибский']
# ============================================================
# Рабочий поток для геокодирования и Overpass (не блокирует UI)
# ============================================================

class GeoWorker(QObject):
    """Выполняет сетевые запросы в отдельном потоке."""

    finished = Signal(dict)  # Результат: {address, microdistrict, nearby}

    def __init__(self, prop: dict):
        super().__init__()
        self.prop = prop

    def run(self):
        result = {}
        lat = self.prop.get("lat")
        lon = self.prop.get("lon")

        try:
            addr_info = get_address(lat, lon)
            result["address"] = addr_info.get("address", "Точный адрес не найден")
            result["microdistrict"] = addr_info.get("microdistrict", "Не определён")
        except Exception:
            result["address"] = "Ошибка получения адреса"
            result["microdistrict"] = "Не определён"

        try:
            nearby = get_nearby_places(lat, lon)
            result["nearby"] = nearby
        except Exception:
            result["nearby"] = {"_error": "Данные об объектах рядом недоступны."}

        self.finished.emit(result)


class GeoThread(QThread):
    resultReady = Signal(dict)

    def __init__(self, prop: dict):
        super().__init__()
        self.prop = prop

    def run(self):
        worker = GeoWorker(self.prop)
        worker.finished.connect(self.resultReady)
        worker.run()


class AIThread(QThread):
    resultReady = Signal(str)

    def __init__(self, prop, question, d_stats, m_stats, nearby):
        super().__init__()
        self.prop = prop
        self.question = question
        self.d_stats = d_stats
        self.m_stats = m_stats
        self.nearby = nearby

    def run(self):
        try:
            answer = answer_question(self.prop, self.question, self.d_stats, self.m_stats, self.nearby)
        except Exception as e:
            answer = f"Ошибка ассистента: {str(e)}"
        self.resultReady.emit(answer)


# ============================================================
# Стиль приложения
# ============================================================

STYLE_SHEET = """
QMainWindow {
    background: #f0f2f5;
    color: #111827;
}

QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #111827;
    background-color: transparent;
}

QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #dde1e7;
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 8px;
    background: #ffffff;
    color: #111827;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #1a237e;
    background: #ffffff;
}

QLabel {
    color: #111827;
    background: transparent;
}

QPushButton {
    background: #1976d2;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background: #1565c0;
}

QPushButton:pressed {
    background: #0d47a1;
}

QPushButton:disabled {
    background: #b0bec5;
    color: #ffffff;
}

QPushButton#resetBtn {
    background: #546e7a;
}

QPushButton#resetBtn:hover {
    background: #455a64;
}

QLineEdit {
    border: 1px solid #b0bec5;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    background: #ffffff;
    color: #111827;
    selection-background-color: #1976d2;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border-color: #1976d2;
}

QTextEdit {
    border: 1px solid #dde1e7;
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
    background: #ffffff;
    color: #111827;
    selection-background-color: #1976d2;
    selection-color: #ffffff;
}

QTextEdit QWidget {
    background: #ffffff;
    color: #111827;
}

QTabWidget::pane {
    border: 1px solid #dde1e7;
    border-radius: 6px;
    background: #ffffff;
}

QTabBar::tab {
    padding: 7px 16px;
    font-size: 12px;
    border-radius: 4px 4px 0 0;
    background: #e8eaf6;
    margin-right: 2px;
    color: #111827;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #1a237e;
    font-weight: bold;
}

QTabBar::tab:hover {
    background: #dfe3fb;
    color: #1a237e;
}

QCheckBox {
    font-size: 12px;
    color: #111827;
    background: transparent;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QLabel#propLabel {
    font-size: 12px;
    color: #111827;
}

QLabel#sectionLabel {
    font-size: 13px;
    font-weight: bold;
    color: #1a237e;
}

QScrollArea {
    border: none;
    background: #ffffff;
}

QScrollArea QWidget {
    background: #ffffff;
    color: #111827;
}

QScrollBar:vertical {
    width: 8px;
    background: #f0f2f5;
}

QScrollBar::handle:vertical {
    background: #b0bec5;
    border-radius: 4px;
    min-height: 20px;
}

QStatusBar {
    background: #1a237e;
    color: #ffffff;
    font-size: 12px;
    padding: 4px 10px;
}

QStatusBar QLabel {
    color: #ffffff;
}

QComboBox {
    border: 1px solid #b0bec5;
    border-radius: 6px;
    padding: 5px 10px;
    background: #ffffff;
    color: #111827;
    font-size: 12px;
}

QComboBox QAbstractItemView {
    background: #ffffff;
    color: #111827;
    selection-background-color: #1976d2;
    selection-color: #ffffff;
}

QSpinBox, QDoubleSpinBox {
    border: 1px solid #b0bec5;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
    background: #ffffff;
    color: #111827;
}

QFrame#separator {
    background: #dde1e7;
    max-height: 1px;
}

/* filters-ui-layout-fix-v2 */
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
    min-height:30px;
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


/* filters-ui-layout-fix-v3 */
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
    min-height:30px;
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


/* filters-ui-oneclick-fix */
QGroupBox#filtersBox {
    background:#ffffff;
    border:1px solid #d8dee9;
    border-radius:16px;
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
    border-radius:8px;
    padding:4px 8px;
    min-height:32px;
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


/* tabs-space-filter-compact-fix-v2 */
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


/* clean-functional-filter-buttons */
QPushButton#applyFilterBtn {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
    color:#ffffff;
    border:none;
    border-radius:12px;
    padding:8px 16px;
    font-size:13px;
    font-weight:900;
}
QPushButton#applyFilterBtn:hover {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1d4ed8, stop:1 #1e40af);
}
QPushButton#applyFilterBtn:pressed {
    background:#1e3a8a;
}
QPushButton#resetFilterBtn {
    background:#f8fafc;
    color:#334155;
    border:1px solid #cbd5e1;
    border-radius:12px;
    padding:8px 16px;
    font-size:13px;
    font-weight:900;
}
QPushButton#resetFilterBtn:hover {
    background:#e2e8f0;
    color:#0f172a;
}
QPushButton#resetFilterBtn:pressed {
    background:#cbd5e1;
}

"""


# ============================================================
# Главное окно
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.setMinimumSize(1300, 750)
        self.resize(1500, 900)

        self.df = None
        self.filtered_df = None
        self.global_stats = {}
        self.district_stats = {}
        self.selected_prop = None
        self.pending_prop = None
        self.pending_prop_id = None
        self.nearby_places = {}
        self.nearby_show_all = False
        self.geo_thread = None
        self.ai_thread = None
        self._warnings = []

        self.setStyleSheet(STYLE_SHEET)
        self._setup_ui()
        self._load_data()

    # --------------------------------------------------------
    # Загрузка данных
    # --------------------------------------------------------

    def _load_data(self):
        """Загружает CSV, считает район, статистику и показывает объекты на карте."""
        try:
            loaded = load_data()

            # load_data() в разных версиях проекта может вернуть либо df, либо (df, warnings)
            if isinstance(loaded, tuple):
                df = loaded[0]
                warnings = loaded[1] if len(loaded) > 1 else []
            else:
                df = loaded
                warnings = []

            if df is None or len(df) == 0:
                raise ValueError("CSV загрузился пустым. Проверь data/cleaned_almaty_only.csv")

            self._warnings = warnings or []

            # Район определяем локально по координатам, без сетевых запросов
            lat_col = "map_lat" if "map_lat" in df.columns else "latitude"
            lon_col = "map_lon" if "map_lon" in df.columns else "longitude"

            if lat_col not in df.columns or lon_col not in df.columns:
                raise ValueError("В данных нет колонок координат map_lat/map_lon или latitude/longitude.")

            df["district"] = df.apply(
                lambda r: str(determine_district(float(r[lat_col]), float(r[lon_col]))).replace(" (приближённо)", "").strip(),
                axis=1
            )

            # Не считаем microdistrict для всех строк при запуске, иначе программа может долго не открываться.
            # Микрорайон будет определяться при клике на объект или при выборе микрорайона в фильтре.
            if "microdistrict" not in df.columns:
                df["microdistrict"] = "Не определён"
            else:
                df["microdistrict"] = (
                    df["microdistrict"]
                    .fillna("Не определён")
                    .astype(str)
                    .replace({"nan": "Не определён", "None": "Не определён", "": "Не определён"})
                )

            self.df = df
            self.filtered_df = df.copy()

            self.global_stats = compute_global_stats(df)
            self.district_stats = compute_district_stats(df)

            # Заполняем фильтры. В конце _init_filter_ranges() сам вызовет _apply_filters()
            self._init_filter_ranges()

            # Обновляем статистику
            self._update_stats_panel()

            total = self.global_stats.get("total", len(df))
            valid = self.global_stats.get("total_valid", len(df))
            susp = total - valid if isinstance(total, (int, float)) and isinstance(valid, (int, float)) else 0

            self.status_bar.showMessage(
                f"Загружено объектов: {total}  |  В границах Алматы: {valid}  |  Вне Алматы: {susp}"
            )
            # startup warning popup disabled
        except FileNotFoundError as e:
            QMessageBox.critical(
                self,
                "Файл не найден",
                str(e),
                QMessageBox.Ok
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка загрузки данных",
                f"Не удалось загрузить данные:\n{str(e)}",
                QMessageBox.Ok
            )
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # === Верхняя панель фильтров ===
        filters_group = self._build_filters_panel()
        main_layout.addWidget(filters_group)

        # === Основной сплиттер (карта | боковая панель) ===
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        main_layout.addWidget(splitter, stretch=1)

        # Левая часть: карта
        self.map_widget = MapWidget(self)
        self.map_widget.propertySelected.connect(self._on_property_selected)
        self.map_widget.setMinimumWidth(600)
        splitter.addWidget(self.map_widget)

        # Правая часть: вкладки (Объект | Статистика | ИИ)
        right_panel = self._build_right_panel()
        right_panel.setMinimumWidth(380)
        right_panel.setMaximumWidth(520)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        # === Статусная строка ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Загрузка данных...")

    # --------------------------------------------------------
    # Панель фильтров
    # --------------------------------------------------------

    def _build_filters_panel(self) -> QGroupBox:
        """
        Новая верхняя панель фильтров:
        - без чекбоксов "Только дорогие", "Тепловая карта", "Кластеры", "Вне Алматы";
        - фильтр применяется только кнопкой "Применить фильтр";
        - "Сбросить всё" возвращает все значения и карту к исходному состоянию.
        """
        group = QGroupBox("🔎 Фильтры недвижимости")
        group.setObjectName("filtersBox")
        group.setFixedHeight(235)

        outer = QVBoxLayout(group)
        outer.setContentsMargins(14, 16, 14, 10)
        outer.setSpacing(8)

        # Скрытые чекбоксы оставляем только технически, чтобы старые методы проекта не падали.
        # В интерфейс они НЕ добавляются.
        self.chk_expensive = QCheckBox(group)
        self.chk_expensive.setChecked(False)
        self.chk_expensive.setVisible(False)

        self.chk_heatmap = QCheckBox(group)
        self.chk_heatmap.setChecked(False)
        self.chk_heatmap.setVisible(False)

        self.chk_clusters = QCheckBox(group)
        self.chk_clusters.setChecked(False)
        self.chk_clusters.setVisible(False)

        self.chk_suspicious = QCheckBox(group)
        self.chk_suspicious.setChecked(False)
        self.chk_suspicious.setVisible(False)

        # Верхняя строка: статус + две нормальные кнопки
        header = QHBoxLayout()
        header.setSpacing(10)

        self.filter_result_label = QLabel("Показаны все объекты")
        self.filter_result_label.setMinimumWidth(260)
        self.filter_result_label.setStyleSheet(
            "background:#eef2ff;color:#1e293b;border:1px solid #c7d2fe;"
            "border-radius:11px;padding:8px 13px;font-size:12px;font-weight:800;"
        )
        header.addWidget(self.filter_result_label)

        hint = QLabel("Настрой параметры и нажми «Применить фильтр»")
        hint.setStyleSheet("color:#475569;font-size:12px;background:transparent;font-weight:600;")
        header.addWidget(hint, stretch=1)

        self.btn_apply_filters = QPushButton("✅ Применить фильтр")
        self.btn_apply_filters.setObjectName("applyFilterBtn")
        self.btn_apply_filters.setMinimumSize(170, 38)
        self.btn_apply_filters.clicked.connect(self._apply_filters)
        header.addWidget(self.btn_apply_filters)

        self.btn_reset_filters = QPushButton("↺ Сбросить всё")
        self.btn_reset_filters.setObjectName("resetFilterBtn")
        self.btn_reset_filters.setMinimumSize(145, 38)
        self.btn_reset_filters.clicked.connect(self._reset_filters)
        header.addWidget(self.btn_reset_filters)

        outer.addLayout(header)

        def make_card(title_text):
            card = QWidget()
            card.setObjectName("filterCard")
            card.setMinimumHeight(62)
            card.setStyleSheet(
                "QWidget#filterCard { background:#f8fafc; border:1px solid #e2e8f0; border-radius:11px; }"
                "QWidget#filterCard QLabel { background:transparent; border:none; color:#334155; }"
            )
            box = QVBoxLayout(card)
            box.setContentsMargins(10, 6, 10, 8)
            box.setSpacing(4)
            title = QLabel(title_text)
            title.setStyleSheet(
                "font-size:12px;font-weight:800;color:#334155;background:transparent;border:none;"
            )
            box.addWidget(title)
            return card, box

        def setup_input(widget, min_width=100):
            widget.setMinimumHeight(32)
            widget.setMinimumWidth(min_width)
            return widget

        def add_combo(parent_layout, title, combo, min_width=210):
            card, box = make_card(title)
            setup_input(combo, min_width)
            box.addWidget(combo)
            parent_layout.addWidget(card, stretch=1)

        def add_range(parent_layout, title, left_widget, right_widget, min_width=76):
            card, box = make_card(title)
            row = QHBoxLayout()
            row.setSpacing(5)

            lbl_from = QLabel("от")
            lbl_from.setFixedWidth(18)
            lbl_from.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")
            row.addWidget(lbl_from)

            setup_input(left_widget, min_width)
            row.addWidget(left_widget)

            lbl_to = QLabel("до")
            lbl_to.setFixedWidth(18)
            lbl_to.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")
            row.addWidget(lbl_to)

            setup_input(right_widget, min_width)
            row.addWidget(right_widget)

            box.addLayout(row)
            parent_layout.addWidget(card, stretch=1)

        # 1 строка
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.filter_district = QComboBox()
        self.filter_district.addItem("Все районы")
        add_combo(row1, "Район", self.filter_district, 220)

        self.filter_microdistrict = QComboBox()
        self.filter_microdistrict.addItem("Все микрорайоны")
        add_combo(row1, "Микрорайон", self.filter_microdistrict, 240)

        self.filter_price_category = QComboBox()
        self.filter_price_category.addItems([
            "Все категории",
            "🔴 ≥ 1 000 000 ₸/м²",
            "🟠 700 000–1 000 000 ₸/м²",
            "🟡 500 000–700 000 ₸/м²",
            "🟢 300 000–500 000 ₸/м²",
            "🔵 < 300 000 ₸/м²",
        ])
        add_combo(row1, "Категория цены за м²", self.filter_price_category, 250)

        outer.addLayout(row1)

        # 2 строка
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self.filter_price_min = QDoubleSpinBox()
        self.filter_price_min.setDecimals(1)
        self.filter_price_min.setSingleStep(1)
        add_price_max = QDoubleSpinBox()
        self.filter_price_max = add_price_max
        self.filter_price_max.setDecimals(1)
        self.filter_price_max.setSingleStep(1)
        add_range(row2, "Цена квартиры, млн ₸", self.filter_price_min, self.filter_price_max, 82)

        self.filter_ppm2_min = QSpinBox()
        self.filter_ppm2_min.setSingleStep(50)
        self.filter_ppm2_max = QSpinBox()
        self.filter_ppm2_max.setSingleStep(50)
        add_range(row2, "Цена за м², тыс ₸", self.filter_ppm2_min, self.filter_ppm2_max, 82)

        self.filter_rooms_min = QSpinBox()
        self.filter_rooms_max = QSpinBox()
        add_range(row2, "Комнаты", self.filter_rooms_min, self.filter_rooms_max, 62)

        self.filter_year_min = QSpinBox()
        self.filter_year_max = QSpinBox()
        add_range(row2, "Год", self.filter_year_min, self.filter_year_max, 72)

        self.filter_sq_min = QSpinBox()
        self.filter_sq_max = QSpinBox()
        add_range(row2, "Площадь, м²", self.filter_sq_min, self.filter_sq_max, 72)

        outer.addLayout(row2)

        return group
    def _init_filter_ranges(self):
        """Заполняет диапазоны и списки фильтров после загрузки CSV."""
        if self.df is None:
            return

        widgets = [
            "filter_district", "filter_microdistrict", "filter_price_category",
            "filter_price_min", "filter_price_max", "filter_ppm2_min", "filter_ppm2_max",
            "filter_rooms_min", "filter_rooms_max", "filter_year_min", "filter_year_max",
            "filter_sq_min", "filter_sq_max",
            "chk_expensive", "chk_heatmap", "chk_clusters", "chk_suspicious"
        ]

        for name in widgets:
            w = getattr(self, name, None)
            if w is not None:
                try:
                    w.blockSignals(True)
                except Exception:
                    pass

        df = self.df.copy()

        # Районы
        self.filter_district.clear()
        self.filter_district.addItem("Все районы")
        districts = []
        try:
            districts = list(DISTRICT_FILTER_ITEMS)
        except Exception:
            if "district" in df.columns:
                districts = sorted([
                    str(x).replace(" (приближённо)", "").strip()
                    for x in df["district"].dropna().unique()
                    if str(x).strip()
                ])
        self.filter_district.addItems(districts)

        # Микрорайоны
        self.filter_microdistrict.clear()
        self.filter_microdistrict.addItem("Все микрорайоны")
        micros = []
        try:
            micros = list(get_all_microdistricts())
        except Exception:
            micros = []
        if "microdistrict" in df.columns:
            discovered = sorted([
                str(x).strip() for x in df["microdistrict"].dropna().unique()
                if str(x).strip() and str(x).strip() != "Не определён"
            ])
            for m in discovered:
                if m not in micros:
                    micros.append(m)
        self.filter_microdistrict.addItems(micros)

        # Категории
        self.filter_price_category.clear()
        self.filter_price_category.addItems([
            "Все категории",
            "🔴 ≥ 1 000 000 ₸/м²",
            "🟠 700 000–1 000 000 ₸/м²",
            "🟡 500 000–700 000 ₸/м²",
            "🟢 300 000–500 000 ₸/м²",
            "🔵 < 300 000 ₸/м²",
        ])

        # Диапазоны
        price_max = float(df["price"].max()) / 1_000_000 if "price" in df.columns and len(df) else 1000
        price_limit = max(1, price_max + 1)
        self.filter_price_min.setRange(0, max(5000, price_limit))
        self.filter_price_max.setRange(0, max(5000, price_limit))
        self.filter_price_min.setValue(0)
        self.filter_price_max.setValue(price_limit)

        ppm2_max = int(df["price_per_m2"].max() / 1000) + 50 if "price_per_m2" in df.columns and len(df) else 5000
        self.filter_ppm2_min.setRange(0, max(5000, ppm2_max))
        self.filter_ppm2_max.setRange(0, max(5000, ppm2_max))
        self.filter_ppm2_min.setValue(0)
        self.filter_ppm2_max.setValue(max(1, ppm2_max))

        rooms_max = int(df["live_rooms"].max()) if "live_rooms" in df.columns and len(df) else 20
        self.filter_rooms_min.setRange(0, max(20, rooms_max))
        self.filter_rooms_max.setRange(0, max(20, rooms_max))
        self.filter_rooms_min.setValue(0)
        self.filter_rooms_max.setValue(max(1, rooms_max))

        year_min = int(df["year"].min()) if "year" in df.columns and len(df) else 1900
        year_max = int(df["year"].max()) if "year" in df.columns and len(df) else 2035
        self.filter_year_min.setRange(1900, 2035)
        self.filter_year_max.setRange(1900, 2035)
        self.filter_year_min.setValue(max(1900, year_min))
        self.filter_year_max.setValue(min(2035, year_max))

        sq_max = int(df["live_square"].max()) + 1 if "live_square" in df.columns and len(df) else 10000
        self.filter_sq_min.setRange(0, max(10000, sq_max))
        self.filter_sq_max.setRange(0, max(10000, sq_max))
        self.filter_sq_min.setValue(0)
        self.filter_sq_max.setValue(max(1, sq_max))

        # Скрытые старые режимы всегда выключены
        self.chk_expensive.setChecked(False)
        self.chk_heatmap.setChecked(False)
        self.chk_clusters.setChecked(False)
        self.chk_suspicious.setChecked(False)

        try:
            self.map_widget.set_show_heatmap(False)
            self.map_widget.set_show_clusters(False)
            self.map_widget.set_show_suspicious(False)
        except Exception:
            pass

        for name in widgets:
            w = getattr(self, name, None)
            if w is not None:
                try:
                    w.blockSignals(False)
                except Exception:
                    pass

        self.filtered_df = df.copy()
        self._apply_filters()
    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладка 1: Объект
        self.tabs.addTab(self._build_property_tab(), "🏠 Объект")

        # Вкладка 2: Статистика
        self.tabs.addTab(self._build_stats_tab(), "📊 Статистика")

        # Вкладка 3: ИИ-ассистент
        self.tabs.addTab(self._build_ai_tab(), "🤖 ИИ-ассистент")

        return panel

    def _build_property_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Заголовок
        self.prop_title = QLabel("Выберите объект на карте")
        self.prop_title.setObjectName("sectionLabel")
        self.prop_title.setWordWrap(True)
        layout.addWidget(self.prop_title)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # Основная информация
        self.prop_details = QTextEdit()
        self.prop_details.setReadOnly(True)
        self.prop_details.setMinimumHeight(300)
        self.prop_details.setHtml("<p style='color:#888'>Кликните на объект на карте для отображения информации</p>")
        layout.addWidget(self.prop_details)

        # Объекты рядом
        nearby_label = QLabel("📍 Объекты рядом")
        nearby_label.setObjectName("sectionLabel")
        layout.addWidget(nearby_label)

        self.nearby_text = QTextEdit()
        self.nearby_text.setReadOnly(True)
        self.nearby_text.setMinimumHeight(150)
        self.nearby_text.setHtml("<p style='color:#888'>Будут загружены при выборе объекта</p>")
        layout.addWidget(self.nearby_text)

        layout.addStretch()
        return scroll

    def _build_stats_tab(self) -> QWidget:
        # Statistics tab with full vertical space. No bottom hint.
        widget = QWidget()
        widget.setStyleSheet("background:#ffffff;color:#111827;")

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

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
        self.stats_display.setStyleSheet(
            "QTextEdit { background:#ffffff; color:#111827; border:1px solid #d8dee9; "
            "border-radius:10px; padding:10px; font-size:12px; }"
            "QScrollBar:vertical { background:#f1f5f9; width:14px; border-radius:7px; }"
            "QScrollBar::handle:vertical { background:#94a3b8; border-radius:7px; min-height:35px; }"
        )
        self.stats_display.setHtml(
            "<div style='font-family:Segoe UI,sans-serif;color:#111827;background:#ffffff;'>"
            "<p style='color:#64748b'>Загрузка статистики...</p></div>"
        )
        layout.addWidget(self.stats_display, stretch=1)

        return widget
    def _build_ai_tab(self) -> QWidget:
        """
        Нормальный чат ИИ-ассистента:
        - сообщения пользователя видны в чате;
        - после ответа можно писать следующий вопрос;
        - ИИ работает даже без выбранного объекта, но лучше с выбранным объектом.
        """
        widget = QWidget()
        widget.setStyleSheet("background:#ffffff;color:#111827;")

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(7)

        title = QLabel("🤖 ИИ-чат по недвижимости Алматы")
        title.setObjectName("sectionLabel")
        title.setStyleSheet("color:#1a237e;font-size:14px;font-weight:900;background:#ffffff;")
        layout.addWidget(title)

        self.ai_context_label = QLabel("Можно писать вопрос. Для точного анализа выберите объект на карте и нажмите ✅ Выбрать.")
        self.ai_context_label.setWordWrap(True)
        self.ai_context_label.setMaximumHeight(76)
        self.ai_context_label.setStyleSheet(
            "background:#eef2ff;color:#111827;border:1px solid #c7d2fe;"
            "border-radius:10px;padding:8px;font-size:12px;font-weight:600;"
        )
        layout.addWidget(self.ai_context_label)

        # История сообщений
        self.ai_history = []
        self.ai_busy = False

        quick_grid = QVBoxLayout()
        quick_grid.setSpacing(5)

        quick_questions = [
            ["Привет", "Что ты умеешь?", "Что влияет на цену?"],
            ["Почему такая цена?", "Дорого для района?", "Какие риски?"],
            ["Можно торговаться?", "Подходит для жизни?", "Полный анализ объекта"],
        ]

        for row_questions in quick_questions:
            row = QHBoxLayout()
            row.setSpacing(5)
            for q in row_questions:
                btn = QPushButton(q)
                btn.setMinimumHeight(30)
                btn.setStyleSheet(
                    "QPushButton { background:#e8eaf6;color:#1a237e;border:1px solid #c7d2fe;"
                    "border-radius:8px;font-size:11px;font-weight:700;padding:4px 6px; }"
                    "QPushButton:hover { background:#dbeafe; }"
                )
                btn.clicked.connect(lambda checked=False, text=q: self._quick_question(text))
                row.addWidget(btn)
            quick_grid.addLayout(row)

        layout.addLayout(quick_grid)

        self.ai_response = QTextEdit()
        self.ai_response.setReadOnly(True)
        self.ai_response.setAcceptRichText(True)
        self.ai_response.setLineWrapMode(QTextEdit.WidgetWidth)
        self.ai_response.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.ai_response.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ai_response.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ai_response.setStyleSheet(
            "QTextEdit { background:#ffffff; color:#111827; border:1px solid #d8dee9; "
            "border-radius:10px; padding:10px; font-size:12px; line-height:1.6; }"
            "QScrollBar:vertical { background:#f1f5f9; width:14px; border-radius:7px; }"
            "QScrollBar::handle:vertical { background:#94a3b8; border-radius:7px; min-height:35px; }"
        )
        layout.addWidget(self.ai_response, stretch=1)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Напиши вопрос в чат: цена, район, риски, торг, инфраструктура...")
        self.ai_input.setMinimumHeight(38)
        self.ai_input.setEnabled(True)
        self.ai_input.returnPressed.connect(self._ask_ai)
        input_row.addWidget(self.ai_input, stretch=1)

        self.ai_ask_btn = QPushButton("Отправить")
        self.ai_ask_btn.setObjectName("applyFilterBtn")
        self.ai_ask_btn.setMinimumHeight(38)
        self.ai_ask_btn.setMinimumWidth(110)
        self.ai_ask_btn.clicked.connect(self._ask_ai)
        input_row.addWidget(self.ai_ask_btn)

        layout.addLayout(input_row)

        self._append_ai_message(
            "assistant",
            "Привет! Я ИИ-ассистент по недвижимости Алматы. Можешь писать мне обычным сообщением. "
            "Для точного анализа выбери квартиру на карте и нажми зелёную кнопку **✅ Выбрать**."
        )

        return widget
    def _refresh_panels_for_selected_property(self):
        """
        Обновляет все вкладки под текущий selected_prop:
        Объект, Статистика, ИИ-ассистент.
        Вызывается при клике на другой объект и после применения фильтра.
        """
        if self.selected_prop is None:
            self._clear_selection_panels()
            return

        try:
            if hasattr(self, "_ensure_selected_microdistrict"):
                self._ensure_selected_microdistrict()
        except Exception:
            pass

        # 1) Вкладка "Объект"
        updated_object = False
        for method_name in [
            "_update_property_panel_full",
            "_update_property_panel_basic",
            "_update_property_panel",
            "_update_object_panel",
        ]:
            method = getattr(self, method_name, None)
            if callable(method):
                try:
                    method()
                    updated_object = True
                    break
                except TypeError:
                    try:
                        method(self.selected_prop)
                        updated_object = True
                        break
                    except Exception:
                        pass
                except Exception:
                    pass

        # 2) Вкладка "Статистика"
        try:
            if hasattr(self, "_update_stats_panel"):
                self._update_stats_panel()
        except Exception:
            pass

        # 3) Вкладка "ИИ-ассистент"
        try:
            if hasattr(self, "_update_ai_context_panel"):
                self._update_ai_context_panel()
        except Exception:
            pass

        # Если объектная вкладка не обновилась существующими методами — базовый fallback
        if not updated_object:
            try:
                prop = self.selected_prop
                title = str(prop.get("title") or prop.get("address") or "Выбранный объект")
                if hasattr(self, "prop_title"):
                    self.prop_title.setText(title)

                district = str(prop.get("district", "Не определён"))
                micro = str(prop.get("microdistrict", "Не определён"))
                price = prop.get("price", "—")
                ppm2 = prop.get("price_per_m2", prop.get("price_per_m2_raw", "—"))

                if hasattr(self, "prop_details"):
                    self.prop_details.setHtml(
                        "<div style='font-family:Segoe UI;color:#111827;background:#ffffff;'>"
                        f"<h3 style='color:#1a237e'>{title}</h3>"
                        f"<p><b>Район:</b> {district}</p>"
                        f"<p><b>Микрорайон:</b> {micro}</p>"
                        f"<p><b>Цена:</b> {price}</p>"
                        f"<p><b>Цена за м²:</b> {ppm2}</p>"
                        "</div>"
                    )
            except Exception:
                pass

    def _commit_pending_selection(self):
        """
        Подтверждает объект, который был кликнут на карте.
        После этого обновляются вкладки: Объект, Статистика, ИИ-ассистент.
        """
        prop = getattr(self, "pending_prop", None)
        if not prop:
            return False

        self.selected_prop = dict(prop)
        self.pending_prop = None
        self.pending_prop_id = None

        self.nearby_places = {}
        self.nearby_show_all = False

        try:
            if hasattr(self, "nearby_more_btn"):
                self.nearby_more_btn.setVisible(False)
                self.nearby_more_btn.setText("Показать больше объектов рядом")
        except Exception:
            pass

        # Возвращаем кнопку в режим фильтра
        self._set_apply_button_select_mode(False)

        # Сразу обновляем все вкладки базовыми данными
        try:
            if hasattr(self, "_ensure_selected_microdistrict"):
                self._ensure_selected_microdistrict()
        except Exception:
            pass

        try:
            if hasattr(self, "_update_property_panel_basic"):
                self._update_property_panel_basic()
            elif hasattr(self, "_update_property_panel"):
                self._update_property_panel()
        except Exception:
            pass

        try:
            if hasattr(self, "_update_stats_panel"):
                self._update_stats_panel()
        except Exception:
            pass

        try:
            if hasattr(self, "_update_ai_context_panel"):
                self._update_ai_context_panel()
        except Exception:
            pass

        # Стартуем геокодинг и объекты рядом в фоне
        try:
            if hasattr(self, "nearby_text"):
                self.nearby_text.setHtml(
                    "<p style='color:#64748b;background:#ffffff;'>Загрузка адреса и объектов рядом...</p>"
                )
            self._start_geo_thread()
        except Exception:
            pass

        try:
            title = self.selected_prop.get("address") or self.selected_prop.get("title") or "объект"
            self.status_bar.showMessage(f"Выбран объект: {title}", 7000)
        except Exception:
            pass

        return True

    def _on_property_selected(self, prop_id):
        """
        Клик по маркеру на карте НЕ сразу открывает карточку.
        Он ставит объект в ожидание выбора и превращает кнопку
        "Применить фильтр" в зелёную кнопку "✅ Выбрать".
        """
        if self.df is None:
            return

        try:
            prop_id = int(prop_id)
        except Exception:
            return

        # Ищем объект сначала в отфильтрованных данных, потом во всей базе
        row = None
        try:
            source_df = self.filtered_df if getattr(self, "filtered_df", None) is not None else self.df
            rows = source_df.loc[source_df["id"] == prop_id]
            if len(rows) > 0:
                row = rows.iloc[0]
        except Exception:
            row = None

        if row is None:
            try:
                rows = self.df.loc[self.df["id"] == prop_id]
                if len(rows) > 0:
                    row = rows.iloc[0]
            except Exception:
                row = None

        if row is None:
            try:
                self.status_bar.showMessage("Не удалось найти выбранный объект в данных.", 5000)
            except Exception:
                pass
            return

        try:
            prop = get_property_dict(row)
        except Exception:
            prop = row.to_dict()

        # Дополняем техническими и гео-данными
        try:
            prop["id"] = int(row.get("id", prop_id))
        except Exception:
            prop["id"] = prop_id

        prop["district"] = row.get("district", prop.get("district", "Район не определён точно"))
        prop["microdistrict"] = row.get("microdistrict", prop.get("microdistrict", "Не определён"))

        # Координаты нужны геокодеру / объектам рядом / ИИ
        try:
            prop["lat"] = float(row.get("map_lat", row.get("lat", prop.get("lat", 0))))
            prop["lon"] = float(row.get("map_lon", row.get("lon", prop.get("lon", 0))))
            prop["map_lat"] = prop["lat"]
            prop["map_lon"] = prop["lon"]
            prop["lat_raw"] = prop["lat"]
            prop["lon_raw"] = prop["lon"]
        except Exception:
            pass

        # Сохраняем как ожидающий выбор
        self.pending_prop = prop
        self.pending_prop_id = prop_id

        # Кнопка "Применить фильтр" временно становится "Выбрать"
        self._set_apply_button_select_mode(True)

        try:
            title = prop.get("address") or prop.get("title") or f"ID {prop_id}"
            self.status_bar.showMessage(
                f"Объект выбран на карте: {title}. Нажмите зелёную кнопку «Выбрать».",
                8000
            )
        except Exception:
            pass

        # Небольшая подсказка в ИИ, но сами вкладки пока не заполняем
        try:
            if hasattr(self, "ai_context_label"):
                self.ai_context_label.setText("Объект отмечен на карте. Нажмите «✅ Выбрать», чтобы загрузить данные.")
        except Exception:
            pass
    def _start_geo_thread(self):
        if self.geo_thread and self.geo_thread.isRunning():
            self.geo_thread.quit()

        self.geo_thread = GeoThread(self.selected_prop)
        self.geo_thread.resultReady.connect(self._on_geo_result)
        self.geo_thread.start()


    def _update_ai_context_panel(self):
        """Safe AI context updater. Prevents AttributeError after geocoding updates."""
        if not hasattr(self, "ai_context_label"):
            return

        prop = getattr(self, "selected_prop", None)
        if not prop:
            self.ai_context_label.setText("Сначала выберите объект на карте")
            return

        try:
            micro = str(prop.get("microdistrict", "")).strip()
            if (not micro) or micro in ["Не определён", "None", "nan"]:
                lat = prop.get("lat_raw") or prop.get("map_lat") or prop.get("latitude") or prop.get("lat")
                lon = prop.get("lon_raw") or prop.get("map_lon") or prop.get("longitude") or prop.get("lon")
                address_text = " ".join([
                    str(prop.get("address", "")),
                    str(prop.get("location", "")),
                    str(prop.get("title", "")),
                    str(prop.get("complex_name", "")),
                ])
                micro = determine_microdistrict(lat, lon, address_text)
                prop["microdistrict"] = micro
        except Exception:
            micro = str(prop.get("microdistrict", "Не определён"))

        district = str(prop.get("district", "Не определён"))
        price = prop.get("price_mln", prop.get("price", ""))
        ppm2 = prop.get("price_per_m2", prop.get("price_m2", ""))

        parts = [
            f"Выбран объект: район — {district}",
            f"микрорайон — {micro or 'Не определён'}",
        ]

        if price not in ["", None]:
            parts.append(f"цена — {price}")
        if ppm2 not in ["", None]:
            parts.append(f"цена за м² — {ppm2}")

        self.ai_context_label.setText(" | ".join(parts))

    def _on_geo_result(self, result: dict):
        """Получен результат геокодирования."""
        if self.selected_prop is None:
            return

        self.selected_prop["address"] = result.get("address", "Точный адрес не найден")
        self.selected_prop["microdistrict"] = result.get("microdistrict", "Не определён")
        self.nearby_places = result.get("nearby", {})

        # Добавляем microdistrict в df для статистики
        if self.df is not None:
            prop_id = self.selected_prop.get("id")
            if prop_id is not None:
                self.df.loc[self.df["id"] == prop_id, "microdistrict"] = self.selected_prop["microdistrict"]

        self._refresh_microdistrict_filter_values()
        self._update_property_panel_full()
        self._update_nearby_panel()
        self._update_stats_panel()
        self._update_ai_context_panel()

    def _refresh_microdistrict_filter_values(self):
        """Обновляет список микрорайонов в фильтре, сохраняя полный список Алматы."""
        if self.df is None or not hasattr(self, "filter_microdistrict"):
            return
        current = self.filter_microdistrict.currentText()
        self.filter_microdistrict.blockSignals(True)
        self.filter_microdistrict.clear()
        self.filter_microdistrict.addItem("Все микрорайоны")
        micros = list(get_all_microdistricts())
        if "microdistrict" in self.df.columns:
            discovered = sorted([str(x).strip() for x in self.df["microdistrict"].dropna().unique() if str(x).strip() and str(x).strip() != "Не определён"])
            for m in discovered:
                if m not in micros:
                    micros.append(m)
        self.filter_microdistrict.addItems(micros)
        idx = self.filter_microdistrict.findText(current)
        if idx >= 0:
            self.filter_microdistrict.setCurrentIndex(idx)
        self.filter_microdistrict.blockSignals(False)


    def _ensure_selected_microdistrict(self):
        # If selected object has no microdistrict, calculate it by coordinates.
        if not hasattr(self, "selected_prop") or self.selected_prop is None:
            return

        current = str(self.selected_prop.get("microdistrict", "")).strip()
        if current and current not in ["Не определён", "None", "nan", ""]:
            return

        lat = (
            self.selected_prop.get("lat_raw")
            or self.selected_prop.get("map_lat")
            or self.selected_prop.get("latitude")
            or self.selected_prop.get("lat")
        )
        lon = (
            self.selected_prop.get("lon_raw")
            or self.selected_prop.get("map_lon")
            or self.selected_prop.get("longitude")
            or self.selected_prop.get("lon")
        )

        address_text = " ".join([
            str(self.selected_prop.get("address", "")),
            str(self.selected_prop.get("location", "")),
            str(self.selected_prop.get("title", "")),
            str(self.selected_prop.get("complex_name", "")),
        ])

        micro = determine_microdistrict(lat, lon, address_text)
        if micro:
            self.selected_prop["microdistrict"] = micro

            try:
                prop_id = self.selected_prop.get("id")
                if prop_id is not None and self.df is not None and "id" in self.df.columns:
                    self.df.loc[self.df["id"] == prop_id, "microdistrict"] = micro
                if prop_id is not None and hasattr(self, "filtered_df") and self.filtered_df is not None and "id" in self.filtered_df.columns:
                    self.filtered_df.loc[self.filtered_df["id"] == prop_id, "microdistrict"] = micro
            except Exception:
                pass

    def _update_property_panel_basic(self):
        self._ensure_selected_microdistrict()
        """Быстрое обновление без адреса и nearby."""
        if self.selected_prop is None:
            return

        p = self.selected_prop
        district = p.get("district", "—")

        title = f"{p.get('priv_dorm', 'Объект')} · {p.get('rooms', '—')}-комн., {p.get('square', '—')} м²"
        self.prop_title.setText(title)

        d_avg = get_district_avg(self.df, district) if self.df is not None else None
        ppm2_raw = p.get("price_per_m2_raw")
        comparison = compare_to_average(ppm2_raw, d_avg) if ppm2_raw and d_avg else "—"

        html = self._build_property_html(p, district, d_avg, comparison, "Определяется...", "Определяется...")
        self.prop_details.setHtml(html)

    def _update_property_panel_full(self):
        self._ensure_selected_microdistrict()
        """Полное обновление с адресом."""
        if self.selected_prop is None:
            return

        p = self.selected_prop
        district = p.get("district", "—")
        address = p.get("address", "Точный адрес не найден")
        microdistrict = p.get("microdistrict", "Не определён")

        d_avg = get_district_avg(self.df, district) if self.df is not None else None
        ppm2_raw = p.get("price_per_m2_raw")
        comparison = compare_to_average(ppm2_raw, d_avg) if ppm2_raw and d_avg else "—"

        html = self._build_property_html(p, district, d_avg, comparison, address, microdistrict)
        self.prop_details.setHtml(html)

    def _build_property_html(self, p, district, d_avg, comparison, address, microdistrict) -> str:
        def row(label, value, highlight=False):
            style = "color:#1976d2;font-weight:bold" if highlight else "color:#111827;"
            return f"<tr><td style='color:#6b7280;padding:3px 8px 3px 0;width:140px'>{label}</td><td style='{style}'>{value}</td></tr>"

        d_avg_str = f"{int(d_avg):,} ₸/м²".replace(",", " ") if d_avg else "—"
        pct = get_property_percentile(self.df, p.get("price_per_m2_raw", 0)) if self.df is not None and p.get("price_per_m2_raw") else 0

        html = f"""
<style>
  body {{ font-family: 'Segoe UI', sans-serif; font-size: 12px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 3px 4px; vertical-align: top; }}
  .section {{ color: #1a237e; font-weight: bold; margin-top: 10px; margin-bottom: 4px; font-size: 13px; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; }}
</style>

<p class="section">💰 Стоимость</p>
<table>
{row('Цена', p.get('price', '—'), highlight=True)}
{row('Цена за м²', p.get('price_per_m2', '—'), highlight=True)}
{row('Среднее по р-ну', d_avg_str)}
{row('Сравнение', comparison)}
{row('Перцентиль', f'{pct:.0f}% (дороже {pct:.0f}% объектов)')}
</table>

<p class="section">🏠 Параметры квартиры</p>
<table>
{row('Тип', p.get('priv_dorm', '—'))}
{row('Комнат', str(p.get('rooms', '—')))}
{row('Площадь', f"{p.get('square', '—')} м²")}
{row('Этаж', p.get('floor', '—'))}
{row('Год постройки', str(p.get('year', '—')))}
{row('Тип здания', p.get('building', '—'))}
{row('Ремонт', p.get('renovation', '—'))}
{row('Мебель', p.get('furniture', '—'))}
{row('Санузел', p.get('toilet', '—'))}
{row('Ипотека', p.get('mortgage', '—'))}
{row('ЖК', p.get('complex', '—'))}
</table>

<p class="section">📍 Местоположение</p>
<table>
{row('Адрес', address)}
{row('Район', district)}
{row('Микрорайон', microdistrict)}
{row('Координаты', f"{p.get('lat', '—'):.5f}, {p.get('lon', '—'):.5f}")}
</table>
"""
        if p.get("suspicious"):
            html += '<p style="color:#e53935;font-size:11px;margin-top:8px;">⚠️ Координаты могут быть вне границ Алматы</p>'

        return html


    def _toggle_nearby_show_all(self):
        """Переключает краткий и расширенный список объектов рядом."""
        self.nearby_show_all = not getattr(self, "nearby_show_all", False)
        if hasattr(self, "nearby_more_btn"):
            self.nearby_more_btn.setText(
                "Свернуть список" if self.nearby_show_all else "Показать больше объектов рядом"
            )
        self._update_nearby_panel()

    def _update_nearby_panel(self):
        """Чистый и понятный блок объектов рядом без технических OSM-тегов."""
        if not self.nearby_places:
            if hasattr(self, "nearby_more_btn"):
                self.nearby_more_btn.setVisible(False)
            self.nearby_text.setHtml("<p style='color:#64748b'>Выберите объект на карте. Объекты рядом появятся здесь.</p>")
            return

        if "_error" in self.nearby_places:
            if hasattr(self, "nearby_more_btn"):
                self.nearby_more_btn.setVisible(False)
            self.nearby_text.setHtml(
                f"<p style='color:#dc2626'>⚠️ {self.nearby_places['_error']}</p>"
            )
            return

        show_all = getattr(self, "nearby_show_all", False)
        nearest_limit = 10 if show_all else 6
        per_category_limit = 12 if show_all else 3

        icons = {
            "Школы": "🏫",
            "Детские сады": "🧸",
            "Университеты / колледжи": "🎓",
            "Медицина": "🏥",
            "Аптеки": "💊",
            "Магазины и продукты": "🛒",
            "Торговые центры / рынки": "🛍️",
            "Остановки транспорта": "🚌",
            "Метро / ж/д станции": "🚇",
            "Парки и зелёные зоны": "🌳",
            "Кафе и рестораны": "🍽️",
            "Культура и досуг": "🎭",
            "Спорт и фитнес": "🏟️",
            "Спорт и площадки": "🏟️",
            "Банки и банкоматы": "🏦",
            "Социальные учреждения / детские дома": "🏠",
            "Другие объекты": "📌",
        }

        # Collect all visible objects.
        all_items = []
        total_items = 0
        for cat, items in self.nearby_places.items():
            if cat.startswith("_") or not isinstance(items, list):
                continue
            total_items += len(items)
            for item in items:
                x = dict(item)
                x["_cat"] = cat
                all_items.append(x)

        all_items.sort(key=lambda x: x.get("distance", 999999))

        if hasattr(self, "nearby_more_btn"):
            self.nearby_more_btn.setVisible(total_items > 18)
            self.nearby_more_btn.setText("Свернуть список" if show_all else "Показать больше объектов рядом")

        def safe(v, default="—"):
            return v if v not in (None, "", "Без названия") else default

        html = [
            "<div style='font-family:Segoe UI,sans-serif;color:#111827;background:#ffffff;font-size:12px;'>",
            "<style>",
            ".near-title{color:#1a237e;margin:4px 0 8px;font-size:14px;font-weight:800;}",
            ".near-card{border:1px solid #e2e8f0;border-radius:12px;padding:9px;margin:8px 0;background:#f8fafc;}",
            ".near-item{border-left:3px solid #1976d2;margin:7px 0;padding:7px 8px;background:#ffffff;border-radius:8px;}",
            ".near-name{font-weight:700;color:#0f172a;font-size:12px;}",
            ".near-meta{color:#475569;font-size:11px;margin-top:2px;}",
            ".near-warn{color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:5px;margin-top:5px;}",
            "</style>",
            "<div class='near-title'>📍 Объекты рядом</div>",
        ]

        # Nearest objects section.
        nearest = all_items[:nearest_limit]
        if nearest:
            html.append("<div class='near-card'><b>🚶 Ближайшие важные объекты</b>")
            for item in nearest:
                cat = item.get("_cat", "")
                icon = icons.get(cat, "📌")
                name = safe(item.get("name"), "Без названия")
                dist = item.get("distance", "—")
                typ = safe(item.get("type"), "объект")
                address = item.get("address", "")
                warning = item.get("warning", "")

                html.append("<div class='near-item'>")
                html.append(f"<div class='near-name'>{icon} {name}</div>")
                html.append(f"<div class='near-meta'>{cat} · {typ} · {dist} м</div>")
                if address:
                    html.append(f"<div class='near-meta'>Адрес: {address}</div>")
                if warning:
                    html.append(f"<div class='near-warn'>⚠️ {warning}</div>")
                html.append("</div>")
            html.append("</div>")

        # Categories.
        for cat, items in self.nearby_places.items():
            if cat.startswith("_") or not isinstance(items, list) or not items:
                continue

            # Hide low-value categories in compact mode.
            if not show_all and cat in ("Другие объекты",):
                continue

            icon = icons.get(cat, "📌")
            html.append(f"<div class='near-card'><b>{icon} {cat}</b>")

            for item in items[:per_category_limit]:
                name = safe(item.get("name"), "Без названия")
                dist = item.get("distance", "—")
                typ = safe(item.get("type"), "объект")
                address = item.get("address", "")
                warning = item.get("warning", "")

                html.append("<div class='near-item'>")
                html.append(f"<div class='near-name'>{name}</div>")
                html.append(f"<div class='near-meta'>Тип: {typ} · Расстояние: {dist} м</div>")
                if address:
                    html.append(f"<div class='near-meta'>Адрес: {address}</div>")
                if warning:
                    html.append(f"<div class='near-warn'>⚠️ {warning}</div>")
                html.append("</div>")

            html.append("</div>")

        html.append("</div>")
        self.nearby_text.setHtml("".join(html))

    def _update_stats_panel(self):
        if not self.global_stats:
            return

        def fmt(val):
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return "—"
            return f"{int(val):,}".replace(",", " ")

        gs = self.global_stats
        ds = self.district_stats

        html = f"""
<style>
  body {{ font-family: 'Segoe UI', sans-serif; font-size: 12px; color:#111827; background:#ffffff; }}
  h3 {{ color: #1a237e; margin: 10px 0 5px; font-size: 13px; }}
  p {{ margin: 3px 0; color:#111827; }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; }}
  table {{ width:100%; border-collapse:collapse; margin: 4px 0; }}
  td {{ padding: 3px 6px; color:#111827; }}
  tr:nth-child(even) {{ background: #f5f5f5; }}
</style>
<h3>📊 Общая статистика</h3>
<p>Всего объектов: <b>{gs['total']:,}</b></p>
<p>В границах Алматы: <b>{gs['total_valid']:,}</b></p>
<p>Средняя цена: <b>{fmt(gs.get('avg_price'))} ₸</b></p>
<p>Средняя цена/м²: <b>{fmt(gs.get('avg_price_m2'))} ₸/м²</b></p>
<p>Медианная цена/м²: <b>{fmt(gs.get('median_price_m2'))} ₸/м²</b></p>
<p>Мин. цена/м²: <b>{fmt(gs.get('min_price_m2'))} ₸/м²</b></p>
<p>Макс. цена/м²: <b>{fmt(gs.get('max_price_m2'))} ₸/м²</b></p>

<h3>🎨 По категориям цены</h3>
"""
        for label, info in gs.get("by_category", {}).items():
            html += (
                f'<p><span class="dot" style="background:{info["color"]};"></span>'
                f'{label}: <b>{info["count"]}</b></p>'
            )

        if ds:
            html += "<h3>🏙️ Средняя цена/м² по районам</h3>"
            html += "<table>"
            sorted_d = sorted(ds.items(), key=lambda x: x[1]["avg"], reverse=True)
            for d_name, info in sorted_d:
                d_avg = fmt(info["avg"])
                cnt = info["count"]
                selected_marker = ""
                if self.selected_prop and self.selected_prop.get("district") == d_name:
                    selected_marker = " ◀"
                html += (
                    f"<tr><td>{d_name}{selected_marker}</td>"
                    f"<td><b>{d_avg} ₸/м²</b></td>"
                    f"<td style='color:#888'>{cnt} obj.</td></tr>"
                )
            html += "</table>"

        if self.selected_prop:
            p = self.selected_prop
            ppm2 = p.get("price_per_m2_raw")
            district = p.get("district", "")
            d_avg = get_district_avg(self.df, district) if self.df is not None else None

            html += "<h3>🏠 Выбранный объект</h3>"
            html += f"<p>Цена/м²: <b>{p.get('price_per_m2', '—')}</b></p>"

            if ppm2 and self.df is not None:
                pct = get_property_percentile(self.df, ppm2)
                html += f"<p>Перцентиль: <b>{pct:.0f}%</b></p>"

            if d_avg and ppm2:
                cmp = compare_to_average(ppm2, d_avg)
                html += f"<p>Сравнение с районом: <b>{cmp}</b></p>"

        if isinstance(html, str):
            html = (
                "<style>/* stats-readability-fix-v2 */ "
                "body, div, p, td, th, span, li { color:#111827; } "
                "body { background:#ffffff; } "
                "table { width:100%; border-collapse:collapse; } "
                "td, th { padding:6px 8px; border-bottom:1px solid #e5e7eb; } "
                "h1, h2, h3 { color:#1a237e; } "
                "</style>" + html
            )
        self.stats_display.setHtml(html)

    # --------------------------------------------------------
    # ИИ-ассистент
    # --------------------------------------------------------

    def _render_ai_history(self):
        """Рисует историю сообщений как чат."""
        import html as _html
        import re

        def md_inline(s: str) -> str:
            s = _html.escape(str(s))
            s = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", s)
            s = re.sub(r"`([^`]+)`", r"<code style='background:#f1f5f9;padding:1px 4px;border-radius:4px'>\1</code>", s)
            return s

        def md_block(text: str) -> str:
            parts = []
            in_list = False

            def close_list():
                nonlocal in_list
                if in_list:
                    parts.append("</ul>")
                    in_list = False

            for raw in str(text or "").splitlines():
                line = raw.rstrip()

                if not line.strip():
                    close_list()
                    parts.append("<div style='height:5px'></div>")
                    continue

                if line.startswith("## "):
                    close_list()
                    parts.append(
                        f"<h3 style='margin:10px 0 5px;color:#1a237e;font-size:15px'>{md_inline(line[3:].strip())}</h3>"
                    )
                    continue

                if line.startswith("# "):
                    close_list()
                    parts.append(
                        f"<h2 style='margin:10px 0 6px;color:#1a237e;font-size:16px'>{md_inline(line[2:].strip())}</h2>"
                    )
                    continue

                if line.startswith("- ") or line.startswith("• "):
                    if not in_list:
                        parts.append("<ul style='margin:4px 0 8px 18px;padding:0'>")
                        in_list = True
                    parts.append(f"<li style='margin:3px 0'>{md_inline(line[2:].strip())}</li>")
                    continue

                close_list()
                parts.append(f"<p style='margin:4px 0'>{md_inline(line.strip())}</p>")

            close_list()
            return "".join(parts)

        html = (
            "<div style='font-family:Segoe UI,Arial,sans-serif;color:#111827;"
            "background:#ffffff;font-size:12px;line-height:1.55;'>"
        )

        for msg in getattr(self, "ai_history", []):
            role = msg.get("role")
            text = msg.get("text", "")

            if role == "user":
                html += (
                    "<div style='margin:8px 0;text-align:right;'>"
                    "<div style='display:inline-block;max-width:82%;background:#2563eb;color:white;"
                    "padding:9px 12px;border-radius:14px 14px 4px 14px;text-align:left;font-weight:600;'>"
                    f"{md_inline(text)}"
                    "</div></div>"
                )
            else:
                html += (
                    "<div style='margin:8px 0;text-align:left;'>"
                    "<div style='display:inline-block;max-width:92%;background:#f8fafc;color:#111827;"
                    "border:1px solid #e2e8f0;padding:10px 12px;border-radius:14px 14px 14px 4px;text-align:left;'>"
                    f"{md_block(text)}"
                    "</div></div>"
                )

        html += "</div>"

        if hasattr(self, "ai_response"):
            self.ai_response.setHtml(html)
            try:
                self.ai_response.verticalScrollBar().setValue(self.ai_response.verticalScrollBar().maximum())
            except Exception:
                pass

    def _quick_question(self, question: str):
        """Быстрый вопрос теперь тоже отправляется как обычное сообщение в чат."""
        if hasattr(self, "ai_input"):
            self.ai_input.setText(question)
        try:
            self.tabs.setCurrentIndex(2)
        except Exception:
            pass
        self._ask_ai()
    def _append_ai_message(self, role: str, text: str):
        """Добавляет сообщение в историю ИИ-чата и перерисовывает чат."""
        if not hasattr(self, "ai_history"):
            self.ai_history = []

        self.ai_history.append({
            "role": role,
            "text": str(text or "")
        })

        # Чтобы чат не разрастался бесконечно
        if len(self.ai_history) > 40:
            self.ai_history = self.ai_history[-40:]

        self._render_ai_history()

    def _ask_ai(self):
        """
        Отправка сообщения в ИИ-чат.
        Исправлено:
        - сообщение пользователя сразу видно в чате;
        - поле ввода очищается;
        - после ответа можно писать второй/третий вопрос;
        - без выбранного объекта ИИ всё равно отвечает на общие вопросы по недвижимости.
        """
        if not hasattr(self, "ai_input"):
            return

        question = self.ai_input.text().strip()
        if not question:
            return

        if getattr(self, "ai_busy", False):
            try:
                self.status_bar.showMessage("Подождите, ИИ ещё отвечает на предыдущий вопрос.", 4000)
            except Exception:
                pass
            return

        self.ai_input.clear()
        self._append_ai_message("user", question)

        # Контекст: выбранный объект, либо объект, кликнутый на карте, но ещё не подтверждённый
        prop_context = getattr(self, "selected_prop", None)
        if prop_context is None:
            prop_context = getattr(self, "pending_prop", None)
        if prop_context is None:
            prop_context = {}

        try:
            if prop_context and hasattr(self, "_ensure_selected_microdistrict"):
                # Если объект уже выбран, можно уточнить микрорайон
                self._ensure_selected_microdistrict()
        except Exception:
            pass

        # Microdistrict stats считаем быстро только в момент вопроса
        micro_stats = {}
        try:
            if self.df is not None and "microdistrict" in self.df.columns and "price_per_m2" in self.df.columns:
                grouped = self.df.groupby("microdistrict")["price_per_m2"]
                for name, group in grouped:
                    vals = group.dropna()
                    if len(vals) > 0 and str(name).strip() and str(name).strip() != "Не определён":
                        micro_stats[str(name)] = {
                            "avg": float(vals.mean()),
                            "median": float(vals.median()),
                            "count": int(len(vals)),
                        }
        except Exception:
            micro_stats = {}

        self.ai_busy = True
        self.ai_ask_btn.setEnabled(False)
        self.ai_ask_btn.setText("Думаю...")
        self.ai_input.setEnabled(True)
        self.ai_input.setPlaceholderText("ИИ отвечает... скоро можно будет задать следующий вопрос")

        self._append_ai_message("assistant", "⏳ Думаю...")

        try:
            self.ai_thread = AIThread(
                prop_context,
                question,
                self.district_stats,
                micro_stats,
                self.nearby_places,
            )
            self.ai_thread.resultReady.connect(self._on_ai_result)
            self.ai_thread.finished.connect(self._on_ai_finished)
            self.ai_thread.start()
        except Exception as e:
            # Если поток не стартовал, сразу возвращаем управление
            if self.ai_history and self.ai_history[-1]["text"] == "⏳ Думаю...":
                self.ai_history.pop()
            self._append_ai_message("assistant", f"Ошибка запуска ассистента: {e}")
            self._on_ai_finished()
    def _on_ai_result(self, answer: str):
        """Получили ответ ИИ: заменяем временное 'Думаю...' на настоящий ответ."""
        try:
            if hasattr(self, "ai_history") and self.ai_history:
                if self.ai_history[-1].get("role") == "assistant" and "Думаю" in self.ai_history[-1].get("text", ""):
                    self.ai_history.pop()

            self._append_ai_message("assistant", answer)
        except Exception:
            try:
                self.ai_response.setHtml(self._markdown_to_html(answer))
            except Exception:
                pass
    def _on_ai_finished(self):
        """Всегда возвращает поле ввода и кнопку после завершения ответа."""
        self.ai_busy = False

        try:
            self.ai_ask_btn.setEnabled(True)
            self.ai_ask_btn.setText("Отправить")
        except Exception:
            pass

        try:
            self.ai_input.setEnabled(True)
            self.ai_input.setPlaceholderText("Напиши следующий вопрос...")
            self.ai_input.setFocus()
        except Exception:
            pass

        try:
            self.ai_thread.deleteLater()
        except Exception:
            pass

    def _markdown_to_html(self, text: str) -> str:
        """Безопасное преобразование markdown-like ответа в HTML."""
        import re
        import html as _html

        text = str(text or "")
        html = (
            "<div style='font-family: Segoe UI, Arial, sans-serif; font-size:12px; "
            "line-height:1.65; color:#111827; background:#ffffff;'>"
        )

        in_list = False

        def close_list():
            nonlocal html, in_list
            if in_list:
                html += "</ul>"
                in_list = False

        for raw_line in text.splitlines():
            line = raw_line.rstrip()

            if not line.strip():
                close_list()
                html += "<div style='height:6px'></div>"
                continue

            if line.startswith("## "):
                close_list()
                content = _html.escape(line[3:].strip())
                html += f"<h3 style='color:#1a237e;margin:12px 0 6px;font-size:15px'>{content}</h3>"
                continue

            if line.startswith("# "):
                close_list()
                content = _html.escape(line[2:].strip())
                html += f"<h2 style='color:#1a237e;margin:14px 0 7px;font-size:16px'>{content}</h2>"
                continue

            if line.startswith("- ") or line.startswith("• "):
                if not in_list:
                    html += "<ul style='margin:4px 0 8px 18px;padding:0;'>"
                    in_list = True
                content = _html.escape(line[2:].strip())
                content = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", content)
                html += f"<li style='margin:3px 0'>{content}</li>"
                continue

            close_list()
            content = _html.escape(line.strip())
            content = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", content)
            content = re.sub(r"\*(.*?)\*", r"<i>\1</i>", content)
            html += f"<p style='margin:4px 0'>{content}</p>"

        close_list()
        html += "</div>"
        return html
    def _filter_by_microdistrict_smart(self, df, micro_name):
        """
        Smart microdistrict filter.

        If geo/microdistricts.geojson exists, determine_microdistrict() uses real polygons.
        If not, it uses approximate centers.
        """
        if df is None or len(df) == 0:
            return df

        micro_name = str(micro_name).strip()
        if not micro_name or micro_name == "Все микрорайоны":
            return df

        lat_col = "map_lat" if "map_lat" in df.columns else "latitude"
        lon_col = "map_lon" if "map_lon" in df.columns else "longitude"

        temp = df.copy()

        if lat_col in temp.columns and lon_col in temp.columns:
            temp["microdistrict"] = temp.apply(
                lambda r: determine_microdistrict(
                    r.get(lat_col, 0),
                    r.get(lon_col, 0),
                    str(r.get("address", "")) + " " + str(r.get("location", "")) + " " + str(r.get("title", ""))
                ),
                axis=1
            )

        if "microdistrict" in temp.columns:
            exact = temp[temp["microdistrict"].astype(str).str.strip() == micro_name].copy()
            if len(exact) > 0:
                return exact

        center = None
        try:
            center = get_microdistrict_center(micro_name)
        except Exception:
            center = None

        if center and lat_col in temp.columns and lon_col in temp.columns:
            clat, clon, radius = center
            radius = max(float(radius or 0), 1400.0)

            dlat = (temp[lat_col].astype(float) - float(clat)) * 111000.0
            dlon = (temp[lon_col].astype(float) - float(clon)) * 81000.0
            temp["_micro_dist"] = (dlat * dlat + dlon * dlon) ** 0.5

            near = temp[temp["_micro_dist"] <= radius].copy()
            if "_micro_dist" in near.columns:
                near = near.drop(columns=["_micro_dist"])
            return near

        return temp.iloc[0:0].copy()
    def _clear_selection_panels(self, reason: str = "Выберите объект на карте"):
        """
        Полностью очищает вкладки "Объект", "Статистика", "ИИ-ассистент".
        Используется при кнопке "Сбросить всё" и когда выбранный объект исчез после фильтра.
        """
        self.selected_prop = None
        self.nearby_places = {}

        # Объект
        try:
            if hasattr(self, "prop_title"):
                self.prop_title.setText("Выберите объект на карте")
            if hasattr(self, "prop_details"):
                self.prop_details.setHtml(
                    "<div style='font-family:Segoe UI;color:#64748b;background:#ffffff;'>"
                    "<p>Нет выбранного объекта.</p>"
                    "</div>"
                )
            if hasattr(self, "nearby_text"):
                self.nearby_text.setHtml(
                    "<div style='font-family:Segoe UI;color:#64748b;background:#ffffff;'>"
                    "<p>Объекты рядом появятся после выбора недвижимости на карте.</p>"
                    "</div>"
                )
        except Exception:
            pass

        # Статистика
        try:
            if hasattr(self, "stats_display"):
                self.stats_display.setHtml(
                    "<div style='font-family:Segoe UI;color:#64748b;background:#ffffff;'>"
                    "<h3 style='color:#1a237e'>📊 Статистика</h3>"
                    "<p>Нет выбранного объекта.</p>"
                    "<p>Выберите недвижимость на карте, чтобы увидеть сравнение цены, района и объекта.</p>"
                    "</div>"
                )
        except Exception:
            pass

        # ИИ-ассистент
        try:
            if hasattr(self, "ai_context_label"):
                self.ai_context_label.setText("Сначала выберите объект на карте")
            if hasattr(self, "ai_input"):
                self.ai_input.clear()
            if hasattr(self, "ai_response"):
                self.ai_response.setHtml(
                    "<div style='font-family:Segoe UI;color:#64748b;background:#ffffff;'>"
                    "<h3 style='color:#1a237e'>🤖 ИИ-ассистент</h3>"
                    "<p>Нет выбранного объекта.</p>"
                    "<p>Кликните по недвижимости на карте, затем задайте вопрос.</p>"
                    "</div>"
                )
        except Exception:
            pass

        try:
            self.status_bar.showMessage(reason, 5000)
        except Exception:
            pass

    def _set_apply_button_select_mode(self, is_select_mode: bool):
        """
        Переключает главную кнопку:
        - обычный режим: Применить фильтр
        - после клика по маркеру: ✅ Выбрать
        """
        btn = getattr(self, "btn_apply_filters", None)
        if btn is None:
            return

        if is_select_mode:
            btn.setText("✅ Выбрать")
            btn.setToolTip("Подтвердить выбранную недвижимость и обновить вкладки")
            btn.setStyleSheet(
                "QPushButton { background:#16a34a; color:white; border:none; border-radius:12px; "
                "padding:8px 16px; font-size:13px; font-weight:900; }"
                "QPushButton:hover { background:#15803d; }"
                "QPushButton:pressed { background:#166534; }"
            )
        else:
            btn.setText("✅ Применить фильтр")
            btn.setToolTip("Применить выбранные параметры фильтра к карте")
            btn.setStyleSheet("")  # возвращаем стиль из STYLE_SHEET

    def _apply_filters(self):
        """
        Одна кнопка выполняет две роли:
        1) если пользователь кликнул объект на карте — кнопка работает как "✅ Выбрать";
        2) если объекта в ожидании нет — кнопка работает как "✅ Применить фильтр".
        """
        # Режим выбора объекта
        if getattr(self, "pending_prop", None) is not None:
            self._commit_pending_selection()
            return

        if self.df is None:
            return

        required = [
            "filter_price_min", "filter_price_max",
            "filter_ppm2_min", "filter_ppm2_max",
            "filter_rooms_min", "filter_rooms_max",
            "filter_year_min", "filter_year_max",
            "filter_sq_min", "filter_sq_max",
            "filter_district", "filter_microdistrict", "filter_price_category"
        ]
        if any(not hasattr(self, name) for name in required):
            return

        df = self.df.copy()
        total = len(df)

        # По умолчанию показываем только объекты в Алматы
        if "coords_suspicious" in df.columns:
            df = df[~df["coords_suspicious"]].copy()

        # Цена квартиры, млн ₸
        if "price" in df.columns:
            min_price = min(self.filter_price_min.value(), self.filter_price_max.value()) * 1_000_000
            max_price = max(self.filter_price_min.value(), self.filter_price_max.value()) * 1_000_000
            df = df[(df["price"] >= min_price) & (df["price"] <= max_price)].copy()

        # Цена за м², тыс ₸
        if "price_per_m2" in df.columns:
            min_ppm2 = min(self.filter_ppm2_min.value(), self.filter_ppm2_max.value()) * 1000
            max_ppm2 = max(self.filter_ppm2_min.value(), self.filter_ppm2_max.value()) * 1000
            df = df[(df["price_per_m2"] >= min_ppm2) & (df["price_per_m2"] <= max_ppm2)].copy()

        # Комнаты
        if "live_rooms" in df.columns:
            min_rooms = min(self.filter_rooms_min.value(), self.filter_rooms_max.value())
            max_rooms = max(self.filter_rooms_min.value(), self.filter_rooms_max.value())
            df = df[(df["live_rooms"] >= min_rooms) & (df["live_rooms"] <= max_rooms)].copy()

        # Год постройки
        if "year" in df.columns:
            min_year = min(self.filter_year_min.value(), self.filter_year_max.value())
            max_year = max(self.filter_year_min.value(), self.filter_year_max.value())
            df = df[(df["year"] >= min_year) & (df["year"] <= max_year)].copy()

        # Площадь
        if "live_square" in df.columns:
            min_sq = min(self.filter_sq_min.value(), self.filter_sq_max.value())
            max_sq = max(self.filter_sq_min.value(), self.filter_sq_max.value())
            df = df[(df["live_square"] >= min_sq) & (df["live_square"] <= max_sq)].copy()

        # Район
        district = self.filter_district.currentText()
        if district and district != "Все районы" and "district" in df.columns:
            clean_districts = (
                df["district"].astype(str)
                .str.replace(" (приближённо)", "", regex=False)
                .str.replace(" (??????????)", "", regex=False)
                .str.strip()
            )
            df = df[clean_districts == district].copy()

        # Микрорайон
        micro = self.filter_microdistrict.currentText()
        if micro and micro != "Все микрорайоны":
            if hasattr(self, "_filter_by_microdistrict_smart"):
                df = self._filter_by_microdistrict_smart(df, micro)
            elif "microdistrict" in df.columns:
                df = df[df["microdistrict"].astype(str).str.strip() == micro].copy()

        # Категория цены за м²
        category = self.filter_price_category.currentText()
        if "price_per_m2" in df.columns:
            if category.startswith("🔴"):
                df = df[df["price_per_m2"] >= 1_000_000].copy()
            elif category.startswith("🟠"):
                df = df[(df["price_per_m2"] >= 700_000) & (df["price_per_m2"] < 1_000_000)].copy()
            elif category.startswith("🟡"):
                df = df[(df["price_per_m2"] >= 500_000) & (df["price_per_m2"] < 700_000)].copy()
            elif category.startswith("🟢"):
                df = df[(df["price_per_m2"] >= 300_000) & (df["price_per_m2"] < 500_000)].copy()
            elif category.startswith("🔵"):
                df = df[df["price_per_m2"] < 300_000].copy()

        self.filtered_df = df.copy()

        # Если после фильтра ранее выбранный объект исчез — очищаем вкладки.
        if self.selected_prop is not None:
            selected_id = self.selected_prop.get("id")
            visible_ids = set(df["id"].tolist()) if len(df) and "id" in df.columns else set()
            if selected_id not in visible_ids:
                if hasattr(self, "_clear_selection_panels"):
                    self._clear_selection_panels("Выбранный объект не входит в текущий фильтр.")
                else:
                    self.selected_prop = None
                    self.nearby_places = {}

        # Перезагружаем карту отфильтрованными объектами
        if hasattr(self, "map_widget"):
            self.map_widget.load_data(df)

        shown = len(df)
        status_text = f"Показано {shown:,} из {total:,} объектов".replace(",", " ")

        if hasattr(self, "filter_result_label"):
            self.filter_result_label.setText(status_text)

        if hasattr(self, "status_bar"):
            self.status_bar.showMessage("Фильтр применён: " + status_text)

        # После применения фильтра кнопка точно должна быть обратно фильтром
        self.pending_prop = None
        self.pending_prop_id = None
        self._set_apply_button_select_mode(False)

        try:
            if hasattr(self, "_update_stats_panel"):
                self._update_stats_panel()
        except Exception:
            pass
    def _reset_filters(self):
        """
        Сброс фильтров + сброс выбранного/ожидающего объекта.
        После сброса вкладки Объект/Статистика/ИИ пустые.
        """
        self.pending_prop = None
        self.pending_prop_id = None
        self._set_apply_button_select_mode(False)

        if self.df is None:
            if hasattr(self, "_clear_selection_panels"):
                self._clear_selection_panels("Нет загруженных данных")
            return

        try:
            self.chk_expensive.setChecked(False)
            self.chk_heatmap.setChecked(False)
            self.chk_clusters.setChecked(False)
            self.chk_suspicious.setChecked(False)
        except Exception:
            pass

        try:
            self.map_widget.set_show_heatmap(False)
            self.map_widget.set_show_clusters(False)
            self.map_widget.set_show_suspicious(False)
        except Exception:
            pass

        # Перезаполняем фильтры и карту
        self._init_filter_ranges()

        # После _init_filter_ranges / _apply_filters принудительно очищаем вкладки
        if hasattr(self, "_clear_selection_panels"):
            self._clear_selection_panels("Фильтры сброшены. Выберите объект на карте.")
        else:
            self.selected_prop = None
            self.nearby_places = {}
    def _on_heatmap_changed(self, state):
        val = state == Qt.Checked
        if val and hasattr(self, "chk_clusters"):
            self.chk_clusters.blockSignals(True)
            self.chk_clusters.setChecked(False)
            self.chk_clusters.blockSignals(False)
        try:
            self.map_widget.set_show_heatmap(val)
        except Exception:
            pass

    def _on_clusters_changed(self, state):
        val = state == Qt.Checked
        if val and hasattr(self, "chk_heatmap"):
            self.chk_heatmap.blockSignals(True)
            self.chk_heatmap.setChecked(False)
            self.chk_heatmap.blockSignals(False)
        try:
            self.map_widget.set_show_clusters(val)
        except Exception:
            pass

    def _on_suspicious_changed(self, state):
        self._apply_filters()

    def closeEvent(self, event):
        if self.geo_thread and self.geo_thread.isRunning():
            self.geo_thread.quit()
            self.geo_thread.wait(2000)
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.quit()
            self.ai_thread.wait(2000)
        super().closeEvent(event)


# ============================================================
# Точка входа
# ============================================================

def main():
    # Включаем совместимые флаги QtWebEngine
    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-gpu --disable-gpu-compositing --ignore-certificate-errors --no-sandbox"
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
