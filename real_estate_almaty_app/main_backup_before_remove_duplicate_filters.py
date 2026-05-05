# -*- coding: utf-8 -*-
"""
Главный файл приложения: Анализ рынка недвижимости Алматы.
Запуск: python main.py
"""

import sys
import os
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
from src.geo_utils import determine_district, get_address, determine_microdistrict, get_nearby_places
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
        try:
            df, warnings = load_data()
            self._warnings = warnings

            # Определяем район для каждого объекта (локально, без сети)
            df["district"] = df.apply(
                lambda r: determine_district(r["map_lat"], r["map_lon"]), axis=1
            )
            df["microdistrict"] = "Не определён"  # будет определяться по клику

            self.df = df
            self.global_stats = compute_global_stats(df)
            self.district_stats = compute_district_stats(df)

            # Загружаем карту
            self.map_widget.load_data(df)

            # Обновляем статистику
            self._update_stats_panel()

            # Диапазоны для фильтров
            self._init_filter_ranges()

            # Статусная строка
            total = self.global_stats["total"]
            valid = self.global_stats["total_valid"]
            susp = total - valid
            self.status_bar.showMessage(
                f"Загружено объектов: {total}  |  В границах Алматы: {valid}  |  Вне Алматы: {susp}"
            )

            if warnings:
                QTimer.singleShot(1000, self._show_warnings)

        except FileNotFoundError as e:
            QMessageBox.critical(
                self, "Файл не найден",
                str(e),
                QMessageBox.Ok
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка загрузки данных",
                f"Не удалось загрузить данные:\n{str(e)}",
                QMessageBox.Ok
            )

    def _show_warnings(self):
        if self._warnings:
            msg = "\n".join(f"• {w}" for w in self._warnings)
            QMessageBox.information(
                self, "Предупреждения при загрузке",
                f"Данные загружены с предупреждениями:\n\n{msg}",
                QMessageBox.Ok
            )

    # --------------------------------------------------------
    # Построение UI
    # --------------------------------------------------------

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
        Просторная панель фильтров без наложения текста и полей.
        Логика фильтрации остаётся прежней: все элементы подключены к _apply_filters.
        """
        group = QGroupBox("🔎 Фильтры недвижимости")
        group.setObjectName("filtersBox")
        group.setFixedHeight(315)

        outer = QVBoxLayout(group)
        outer.setContentsMargins(16, 18, 16, 12)
        outer.setSpacing(9)

        # Верхняя строка: статус и кнопки
        header = QHBoxLayout()
        header.setSpacing(10)

        self.filter_result_label = QLabel("Показаны все объекты")
        self.filter_result_label.setMinimumWidth(230)
        self.filter_result_label.setStyleSheet(
            "background:#eef2ff;color:#1e293b;border:1px solid #c7d2fe;"
            "border-radius:10px;padding:7px 12px;font-size:12px;font-weight:bold;"
        )
        header.addWidget(self.filter_result_label)

        hint = QLabel("Выбери район, цену, комнаты, год или площадь — карта обновится по этим условиям")
        hint.setStyleSheet("color:#475569;font-size:12px;background:transparent;")
        header.addWidget(hint, stretch=1)

        self.btn_apply_filters = QPushButton("Применить")
        self.btn_apply_filters.setMinimumWidth(120)
        self.btn_apply_filters.setMinimumHeight(34)
        self.btn_apply_filters.clicked.connect(self._apply_filters)
        header.addWidget(self.btn_apply_filters)

        btn_reset = QPushButton("Сбросить")
        btn_reset.setObjectName("resetBtn")
        btn_reset.setMinimumWidth(110)
        btn_reset.setMinimumHeight(34)
        btn_reset.clicked.connect(self._reset_filters)
        header.addWidget(btn_reset)

        outer.addLayout(header)

        def create_card(title_text):
            card = QWidget()
            card.setStyleSheet(
                "QWidget { background:#f8fafc; border:1px solid #e2e8f0; "
                "border-radius:10px; }"
                "QLabel { border:none; background:transparent; color:#334155; }"
            )
            box = QVBoxLayout(card)
            box.setContentsMargins(10, 7, 10, 9)
            box.setSpacing(5)

            title = QLabel(title_text)
            title.setStyleSheet(
                "color:#334155;font-size:12px;font-weight:700;background:transparent;border:none;"
            )
            box.addWidget(title)
            return card, box

        def setup_widget(w, min_width=150):
            w.setMinimumHeight(34)
            w.setMinimumWidth(min_width)
            return w

        def add_combo_card(row_layout, title_text, combo, min_width=210):
            card, box = create_card(title_text)
            setup_widget(combo, min_width)
            box.addWidget(combo)
            row_layout.addWidget(card, stretch=1)

        def add_range_card(row_layout, title_text, left_widget, right_widget, min_width=95):
            card, box = create_card(title_text)

            range_row = QHBoxLayout()
            range_row.setSpacing(7)

            lbl_from = QLabel("от")
            lbl_from.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")
            lbl_from.setFixedWidth(18)
            range_row.addWidget(lbl_from)

            setup_widget(left_widget, min_width)
            range_row.addWidget(left_widget)

            lbl_to = QLabel("до")
            lbl_to.setStyleSheet("color:#64748b;font-size:11px;border:none;background:transparent;")
            lbl_to.setFixedWidth(18)
            range_row.addWidget(lbl_to)

            setup_widget(right_widget, min_width)
            range_row.addWidget(right_widget)

            box.addLayout(range_row)
            row_layout.addWidget(card, stretch=1)

        # Строка 1: район / микрорайон / категория
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.filter_district = QComboBox()
        self.filter_district.addItem("Все районы")
        self.filter_district.currentTextChanged.connect(self._apply_filters)
        add_combo_card(row1, "Район", self.filter_district, 220)

        self.filter_microdistrict = QComboBox()
        self.filter_microdistrict.addItem("Все микрорайоны")
        self.filter_microdistrict.currentTextChanged.connect(self._apply_filters)
        add_combo_card(row1, "Микрорайон", self.filter_microdistrict, 240)

        self.filter_price_category = QComboBox()
        self.filter_price_category.addItems([
            "Все категории",
            "🔴 ≥ 1 000 000 ₸/м²",
            "🟠 700 000–1 000 000 ₸/м²",
            "🟡 500 000–700 000 ₸/м²",
            "🟢 300 000–500 000 ₸/м²",
            "🔵 < 300 000 ₸/м²",
        ])
        self.filter_price_category.currentTextChanged.connect(self._apply_filters)
        add_combo_card(row1, "Категория цены за м²", self.filter_price_category, 250)

        outer.addLayout(row1)

        # Строка 2: цена квартиры / цена за м² / площадь
        row2 = QHBoxLayout()
        row2.setSpacing(10)

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

        add_range_card(row2, "Цена квартиры, млн ₸", self.filter_price_min, self.filter_price_max, 95)

        self.filter_ppm2_min = QSpinBox()
        self.filter_ppm2_min.setRange(0, 5000)
        self.filter_ppm2_min.setSingleStep(50)
        self.filter_ppm2_min.valueChanged.connect(self._apply_filters)

        self.filter_ppm2_max = QSpinBox()
        self.filter_ppm2_max.setRange(0, 5000)
        self.filter_ppm2_max.setSingleStep(50)
        self.filter_ppm2_max.valueChanged.connect(self._apply_filters)

        add_range_card(row2, "Цена за м², тыс ₸", self.filter_ppm2_min, self.filter_ppm2_max, 95)

        self.filter_sq_min = QSpinBox()
        self.filter_sq_min.setRange(0, 10000)
        self.filter_sq_min.valueChanged.connect(self._apply_filters)

        self.filter_sq_max = QSpinBox()
        self.filter_sq_max.setRange(0, 10000)
        self.filter_sq_max.valueChanged.connect(self._apply_filters)

        add_range_card(row2, "Площадь, м²", self.filter_sq_min, self.filter_sq_max, 95)

        outer.addLayout(row2)

        # Строка 3: комнаты / год / режимы карты
        row3 = QHBoxLayout()
        row3.setSpacing(10)

        self.filter_rooms_min = QSpinBox()
        self.filter_rooms_min.setRange(0, 20)
        self.filter_rooms_min.valueChanged.connect(self._apply_filters)

        self.filter_rooms_max = QSpinBox()
        self.filter_rooms_max.setRange(0, 20)
        self.filter_rooms_max.valueChanged.connect(self._apply_filters)

        add_range_card(row3, "Комнаты", self.filter_rooms_min, self.filter_rooms_max, 95)

        self.filter_year_min = QSpinBox()
        self.filter_year_min.setRange(1900, 2035)
        self.filter_year_min.valueChanged.connect(self._apply_filters)

        self.filter_year_max = QSpinBox()
        self.filter_year_max.setRange(1900, 2035)
        self.filter_year_max.valueChanged.connect(self._apply_filters)

        add_range_card(row3, "Год постройки", self.filter_year_min, self.filter_year_max, 95)

        mode_card, mode_box = create_card("Дополнительно")
        mode_row = QHBoxLayout()
        mode_row.setSpacing(14)

        self.chk_expensive = QCheckBox("Только дорогие 🔴")
        self.chk_expensive.stateChanged.connect(self._apply_filters)
        mode_row.addWidget(self.chk_expensive)

        self.chk_heatmap = QCheckBox("Тепловая карта")
        self.chk_heatmap.stateChanged.connect(self._on_heatmap_changed)
        mode_row.addWidget(self.chk_heatmap)

        self.chk_clusters = QCheckBox("Кластеры")
        self.chk_clusters.stateChanged.connect(self._on_clusters_changed)
        mode_row.addWidget(self.chk_clusters)

        self.chk_suspicious = QCheckBox("Вне Алматы")
        self.chk_suspicious.stateChanged.connect(self._apply_filters)
        mode_row.addWidget(self.chk_suspicious)

        mode_row.addStretch()
        mode_box.addLayout(mode_row)

        row3.addWidget(mode_card, stretch=1)
        outer.addLayout(row3)

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
        if "district" in df.columns:
            df["district"] = (
                df["district"].astype(str)
                .str.replace(" (приближённо)", "", regex=False)
                .str.replace(" (??????????)", "", regex=False)
                .str.strip()
            )

        # Районы
        self.filter_district.clear()
        self.filter_district.addItem('Все районы')
        if "district" in df.columns:
            districts = DISTRICT_FILTER_ITEMS
        self.filter_district.addItems(districts)

        # Микрорайоны
        self.filter_microdistrict.clear()
        self.filter_microdistrict.addItem("Все микрорайоны")
        if "microdistrict" in df.columns:
            micros = sorted([
                str(x) for x in df["microdistrict"].dropna().unique()
                if str(x).strip() and str(x) != "Не определён"
            ])
            self.filter_microdistrict.addItems(micros)

        # Цена квартиры, млн
        price_max = float(df["price"].max()) / 1_000_000 if len(df) else 1000
        self.filter_price_min.setValue(0)
        self.filter_price_max.setValue(max(1, price_max + 1))

        # Цена за м², тыс
        ppm2_max = int(df["price_per_m2"].max() / 1000) + 50 if len(df) else 5000
        self.filter_ppm2_min.setValue(0)
        self.filter_ppm2_max.setValue(max(1, ppm2_max))

        self.filter_rooms_min.setValue(0)
        self.filter_rooms_max.setValue(max(1, int(df["live_rooms"].max())))

        year_min = int(df["year"].min()) if len(df) else 1900
        year_max = int(df["year"].max()) if len(df) else 2035
        self.filter_year_min.setValue(max(1900, year_min))
        self.filter_year_max.setValue(min(2035, year_max))

        self.filter_sq_min.setValue(0)
        self.filter_sq_max.setValue(max(1, int(df["live_square"].max()) + 1))

        self.filter_price_category.setCurrentIndex(0)
        self.chk_expensive.setChecked(False)
        self.chk_heatmap.setChecked(False)
        self.chk_clusters.setChecked(False)
        self.chk_suspicious.setChecked(False)

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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setHtml("<p style='color:#888'>Загрузка статистики...</p>")
        layout.addWidget(self.stats_display)

        return scroll

    def _build_stats_tab(self) -> QWidget:
        """
        Исправленная вкладка статистики.
        Здесь QTextEdit сам отвечает за прокрутку, поэтому можно нормально
        спускаться вниз и читать весь текст.
        """
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

        self.stats_display.setStyleSheet("""
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
        """)

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

    def _build_ai_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("🤖 ИИ-ассистент")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        hint = QLabel("Выберите объект на карте и задайте вопрос:")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(hint)

        # Быстрые вопросы
        quick_label = QLabel("Быстрые вопросы:")
        quick_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(quick_label)

        questions = [
            "Почему здесь такая цена?",
            "Дорого это или дёшево для района?",
            "Что рядом влияет на цену?",
            "Подходит ли эта квартира для жизни?",
            "Сравни со средней ценой района.",
            "Что исторически влияет на цену?",
        ]
        for q in questions:
            btn = QPushButton(q)
            btn.setStyleSheet(
                "QPushButton { background: #e8eaf6; color: #1a237e; font-size: 11px; "
                "padding: 5px 10px; text-align: left; } "
                "QPushButton:hover { background: #c5cae9; }"
            )
            btn.clicked.connect(lambda checked, text=q: self._quick_question(text))
            layout.addWidget(btn)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # Поле ввода
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Введите вопрос об объекте...")
        self.ai_input.returnPressed.connect(self._ask_ai)
        layout.addWidget(self.ai_input)

        self.ai_ask_btn = QPushButton("Спросить ИИ")
        self.ai_ask_btn.clicked.connect(self._ask_ai)
        layout.addWidget(self.ai_ask_btn)

        # Ответ ассистента
        self.ai_response = QTextEdit()
        self.ai_response.setReadOnly(True)
        self.ai_response.setMinimumHeight(250)
        self.ai_response.setHtml(
            "<p style='color:#888'>Выберите объект на карте, затем задайте вопрос.</p>"
        )
        layout.addWidget(self.ai_response, stretch=1)

        return widget

    # --------------------------------------------------------
    # Обработка выбора объекта
    # --------------------------------------------------------

    def _on_property_selected(self, prop_id: int):
        """Вызывается при клике на маркер карты."""
        if self.df is None:
            return

        try:
            row = self.df.loc[self.df["id"] == prop_id].iloc[0]
        except (IndexError, KeyError):
            return

        self.selected_prop = get_property_dict(row)
        self.nearby_show_all = False
        if hasattr(self, 'nearby_more_btn'):
            self.nearby_more_btn.setVisible(False)
            self.nearby_more_btn.setText('Показать больше объектов рядом')
        self.selected_prop["district"] = row.get("district", "Район не определён точно")

        # Вкладку не переключаем автоматически: объект обновляется во всех вкладках.

        # Показываем базовую информацию сразу
        self._update_property_panel_basic()

        # Запускаем геокодирование в фоне
        self.nearby_text.setHtml("<p style='color:#888'>Загрузка данных о местоположении...</p>")
        self._start_geo_thread()

    def _start_geo_thread(self):
        if self.geo_thread and self.geo_thread.isRunning():
            self.geo_thread.quit()

        self.geo_thread = GeoThread(self.selected_prop)
        self.geo_thread.resultReady.connect(self._on_geo_result)
        self.geo_thread.start()

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
        """Обновляет список микрорайонов после определения адреса выбранного объекта."""
        if self.df is None or not hasattr(self, "filter_microdistrict"):
            return

        current = self.filter_microdistrict.currentText()

        self.filter_microdistrict.blockSignals(True)
        self.filter_microdistrict.clear()
        self.filter_microdistrict.addItem("Все микрорайоны")

        if "microdistrict" in self.df.columns:
            micros = sorted([
                str(x) for x in self.df["microdistrict"].dropna().unique()
                if str(x).strip() and str(x) != "Не определён"
            ])
            self.filter_microdistrict.addItems(micros)

        idx = self.filter_microdistrict.findText(current)
        if idx >= 0:
            self.filter_microdistrict.setCurrentIndex(idx)

        self.filter_microdistrict.blockSignals(False)

    def _update_property_panel_basic(self):
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

    def _quick_question(self, question: str):
        self.ai_input.setText(question)
        self._ask_ai()
        self.tabs.setCurrentIndex(2)  # Переключаемся на вкладку ИИ

    def _ask_ai(self):
        if self.selected_prop is None:
            self.ai_response.setHtml(
                "<p style='color:#e53935'>⚠️ Сначала выберите объект на карте.</p>"
            )
            return

        question = self.ai_input.text().strip()
        if not question:
            return

        self.ai_ask_btn.setEnabled(False)
        self.ai_ask_btn.setText("Генерация ответа...")
        self.ai_response.setHtml("<p style='color:#888'>🤔 Анализирую данные...</p>")

        self.ai_thread = AIThread(
            self.selected_prop,
            question,
            self.district_stats,
            None,
            self.nearby_places,
        )
        self.ai_thread.resultReady.connect(self._on_ai_result)
        self.ai_thread.start()

    def _on_ai_result(self, answer: str):
        # Форматируем ответ (простой markdown -> HTML)
        html = self._markdown_to_html(answer)
        self.ai_response.setHtml(html)
        self.ai_ask_btn.setEnabled(True)
        self.ai_ask_btn.setText("Спросить ИИ")

    def _markdown_to_html(self, text: str) -> str:
        """Простое преобразование markdown в HTML для TextEdit."""
        import re
        html = "<div style='font-family: Segoe UI, sans-serif; font-size: 12px; line-height: 1.6; color:#111827; background:#ffffff;'>"

        lines = text.split("\n")
        for line in lines:
            # Заголовки
            if line.startswith("### "):
                html += f"<h4 style='color:#1a237e;margin:8px 0 4px'>{line[4:]}</h4>"
            elif line.startswith("## "):
                html += f"<h3 style='color:#1a237e;margin:10px 0 4px'>{line[3:]}</h3>"
            elif line.startswith("# "):
                html += f"<h2 style='color:#1a237e;margin:12px 0 4px'>{line[2:]}</h2>"
            # Список
            elif line.startswith("• ") or line.startswith("- "):
                content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line[2:])
                html += f"<p style='margin:2px 0 2px 12px'>• {content}</p>"
            # Пустая строка
            elif line.strip() == "":
                html += "<br/>"
            # Обычный текст
            else:
                content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', content)
                html += f"<p style='margin:2px 0'>{content}</p>"

        html += "</div>"
        return html

    # --------------------------------------------------------
    # Фильтры
    # --------------------------------------------------------

    def _apply_filters(self):
        """
        Строгая фильтрация.
        ВАЖНО: здесь мы фильтруем pandas DataFrame и заново отправляем
        на карту только подходящие строки. Старый JS-фильтр не используется.
        """
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

        # По умолчанию скрываем координаты вне Алматы
        if hasattr(self, "chk_suspicious") and not self.chk_suspicious.isChecked():
            if "coords_suspicious" in df.columns:
                df = df[~df["coords_suspicious"]].copy()

        # Цена квартиры
        min_price = min(self.filter_price_min.value(), self.filter_price_max.value()) * 1_000_000
        max_price = max(self.filter_price_min.value(), self.filter_price_max.value()) * 1_000_000
        df = df[(df["price"] >= min_price) & (df["price"] <= max_price)]

        # Цена за м²
        min_ppm2 = min(self.filter_ppm2_min.value(), self.filter_ppm2_max.value()) * 1000
        max_ppm2 = max(self.filter_ppm2_min.value(), self.filter_ppm2_max.value()) * 1000
        df = df[(df["price_per_m2"] >= min_ppm2) & (df["price_per_m2"] <= max_ppm2)]

        # Комнаты
        min_rooms = min(self.filter_rooms_min.value(), self.filter_rooms_max.value())
        max_rooms = max(self.filter_rooms_min.value(), self.filter_rooms_max.value())
        df = df[(df["live_rooms"] >= min_rooms) & (df["live_rooms"] <= max_rooms)]

        # Год
        min_year = min(self.filter_year_min.value(), self.filter_year_max.value())
        max_year = max(self.filter_year_min.value(), self.filter_year_max.value())
        df = df[(df["year"] >= min_year) & (df["year"] <= max_year)]

        # Площадь
        min_sq = min(self.filter_sq_min.value(), self.filter_sq_max.value())
        max_sq = max(self.filter_sq_min.value(), self.filter_sq_max.value())
        df = df[(df["live_square"] >= min_sq) & (df["live_square"] <= max_sq)]

        # Район
        district = self.filter_district.currentText()
        if district and district != 'Все районы' and "district" in df.columns:
            df = df[df["district"].astype(str) == district]

        # Микрорайон
        micro = self.filter_microdistrict.currentText()
        if micro and micro != "Все микрорайоны" and "microdistrict" in df.columns:
            df = df[df["microdistrict"].astype(str) == micro]

        # Категория цвета / цены
        category = self.filter_price_category.currentText()
        if hasattr(self, "chk_expensive") and self.chk_expensive.isChecked():
            category = "🔴 ≥ 1 000 000 ₸/м²"

        if category.startswith("🔴"):
            df = df[df["price_per_m2"] >= 1_000_000]
        elif category.startswith("🟠"):
            df = df[(df["price_per_m2"] >= 700_000) & (df["price_per_m2"] < 1_000_000)]
        elif category.startswith("🟡"):
            df = df[(df["price_per_m2"] >= 500_000) & (df["price_per_m2"] < 700_000)]
        elif category.startswith("🟢"):
            df = df[(df["price_per_m2"] >= 300_000) & (df["price_per_m2"] < 500_000)]
        elif category.startswith("🔵"):
            df = df[df["price_per_m2"] < 300_000]

        self.filtered_df = df.copy()

        # Если выбранный объект больше не входит в фильтр — очищаем карточку
        if self.selected_prop is not None:
            selected_id = self.selected_prop.get("id")
            visible_ids = set(df["id"].tolist()) if len(df) else set()
            if selected_id not in visible_ids:
                self.selected_prop = None
                self.nearby_places = {}
                self.prop_title.setText("Выберите объект на карте")
                self.prop_details.setHtml(
                    "<p style='color:#64748b;background:#ffffff;'>"
                    "Выбранный объект не входит в текущий фильтр.</p>"
                )
                self.nearby_text.setHtml(
                    "<p style='color:#64748b;background:#ffffff;'>Выберите объект на карте.</p>"
                )

        # Главное: перезагружаем карту именно отфильтрованным DataFrame
        self.map_widget.load_data(df)

        # Статус
        shown = len(df)
        status_text = f"Показано {shown:,} из {total:,} объектов".replace(",", " ")
        if hasattr(self, "filter_result_label"):
            self.filter_result_label.setText(status_text)
        self.status_bar.showMessage("Фильтр: " + status_text)

        # Обновляем статистику по текущему фильтру, если метод использует filtered_df
        try:
            self._update_stats_panel()
        except Exception:
            pass

    def _reset_filters(self):
        """Полный сброс фильтров."""
        if self.df is None:
            return
        self._init_filter_ranges()

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

    def _build_filters_panel(self) -> QGroupBox:
        """
        Улучшенная панель фильтров.
        Важно: фильтры работают строго через Python DataFrame,
        а не через старую JavaScript-фильтрацию.
        """
        group = QGroupBox("🔎 Фильтры недвижимости")
        group.setObjectName("filtersBox")
        group.setMaximumHeight(185)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.filter_result_label = QLabel("Показаны все объекты")
        self.filter_result_label.setStyleSheet(
            "background:#eef2ff;color:#1e293b;border:1px solid #c7d2fe;"
            "border-radius:10px;padding:5px 10px;font-weight:bold;"
        )
        top_row.addWidget(self.filter_result_label)
        top_row.addStretch()

        self.btn_apply_filters = QPushButton("Применить")
        self.btn_apply_filters.clicked.connect(self._apply_filters)
        top_row.addWidget(self.btn_apply_filters)

        btn_reset = QPushButton("Сбросить")
        btn_reset.setObjectName("resetBtn")
        btn_reset.clicked.connect(self._reset_filters)
        top_row.addWidget(btn_reset)

        layout.addLayout(top_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        layout.addLayout(grid)

        def make_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("color:#334155;font-size:11px;font-weight:600;")
            return lbl

        # --- Район ---
        grid.addWidget(make_label("Район"), 0, 0)
        self.filter_district = QComboBox()
        self.filter_district.addItem('Все районы')
        self.filter_district.currentTextChanged.connect(self._apply_filters)
        grid.addWidget(self.filter_district, 1, 0)

        # --- Микрорайон ---
        grid.addWidget(make_label("Микрорайон"), 0, 1)
        self.filter_microdistrict = QComboBox()
        self.filter_microdistrict.addItem("Все микрорайоны")
        self.filter_microdistrict.currentTextChanged.connect(self._apply_filters)
        grid.addWidget(self.filter_microdistrict, 1, 1)

        # --- Цена квартиры ---
        grid.addWidget(make_label("Цена квартиры, млн ₸"), 0, 2)
        price_box = QHBoxLayout()
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

        price_box.addWidget(self.filter_price_min)
        price_box.addWidget(QLabel("—"))
        price_box.addWidget(self.filter_price_max)
        grid.addLayout(price_box, 1, 2)

        # --- Цена за м² ---
        grid.addWidget(make_label("Цена за м², тыс ₸"), 0, 3)
        ppm_box = QHBoxLayout()
        self.filter_ppm2_min = QSpinBox()
        self.filter_ppm2_min.setRange(0, 5000)
        self.filter_ppm2_min.setSingleStep(50)
        self.filter_ppm2_min.valueChanged.connect(self._apply_filters)

        self.filter_ppm2_max = QSpinBox()
        self.filter_ppm2_max.setRange(0, 5000)
        self.filter_ppm2_max.setSingleStep(50)
        self.filter_ppm2_max.valueChanged.connect(self._apply_filters)

        ppm_box.addWidget(self.filter_ppm2_min)
        ppm_box.addWidget(QLabel("—"))
        ppm_box.addWidget(self.filter_ppm2_max)
        grid.addLayout(ppm_box, 1, 3)

        # --- Комнаты ---
        grid.addWidget(make_label("Комнаты"), 2, 0)
        rooms_box = QHBoxLayout()
        self.filter_rooms_min = QSpinBox()
        self.filter_rooms_min.setRange(0, 20)
        self.filter_rooms_min.valueChanged.connect(self._apply_filters)

        self.filter_rooms_max = QSpinBox()
        self.filter_rooms_max.setRange(0, 20)
        self.filter_rooms_max.valueChanged.connect(self._apply_filters)

        rooms_box.addWidget(self.filter_rooms_min)
        rooms_box.addWidget(QLabel("—"))
        rooms_box.addWidget(self.filter_rooms_max)
        grid.addLayout(rooms_box, 3, 0)

        # --- Год ---
        grid.addWidget(make_label("Год постройки"), 2, 1)
        year_box = QHBoxLayout()
        self.filter_year_min = QSpinBox()
        self.filter_year_min.setRange(1900, 2035)
        self.filter_year_min.valueChanged.connect(self._apply_filters)

        self.filter_year_max = QSpinBox()
        self.filter_year_max.setRange(1900, 2035)
        self.filter_year_max.valueChanged.connect(self._apply_filters)

        year_box.addWidget(self.filter_year_min)
        year_box.addWidget(QLabel("—"))
        year_box.addWidget(self.filter_year_max)
        grid.addLayout(year_box, 3, 1)

        # --- Площадь ---
        grid.addWidget(make_label("Площадь, м²"), 2, 2)
        sq_box = QHBoxLayout()
        self.filter_sq_min = QSpinBox()
        self.filter_sq_min.setRange(0, 10000)
        self.filter_sq_min.valueChanged.connect(self._apply_filters)

        self.filter_sq_max = QSpinBox()
        self.filter_sq_max.setRange(0, 10000)
        self.filter_sq_max.valueChanged.connect(self._apply_filters)

        sq_box.addWidget(self.filter_sq_min)
        sq_box.addWidget(QLabel("—"))
        sq_box.addWidget(self.filter_sq_max)
        grid.addLayout(sq_box, 3, 2)

        # --- Категория ---
        grid.addWidget(make_label("Категория цены"), 2, 3)
        self.filter_price_category = QComboBox()
        self.filter_price_category.addItems([
            "Все категории",
            "🔴 ≥ 1 000 000 ₸/м²",
            "🟠 700 000–1 000 000 ₸/м²",
            "🟡 500 000–700 000 ₸/м²",
            "🟢 300 000–500 000 ₸/м²",
            "🔵 < 300 000 ₸/м²",
        ])
        self.filter_price_category.currentTextChanged.connect(self._apply_filters)
        grid.addWidget(self.filter_price_category, 3, 3)

        # --- Чекбоксы ---
        checks = QHBoxLayout()

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
        layout.addLayout(checks)

        return group

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
    # Включаем OpenGL software rendering для совместимости
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)

    # Стиль Fusion для корректного отображения
    app.setStyle("Fusion")

    # Улучшенный DPI
    try:
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass  # PySide6 6.x может не иметь этих атрибутов

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
