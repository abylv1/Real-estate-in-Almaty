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
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
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
QMainWindow { background: #f0f2f5; }
QWidget { font-family: 'Segoe UI', Arial, sans-serif; }

QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #dde1e7;
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 8px;
    background: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #1a237e;
}

QPushButton {
    background: #1976d2;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover { background: #1565c0; }
QPushButton:pressed { background: #0d47a1; }
QPushButton:disabled { background: #b0bec5; color: #fff; }

QPushButton#resetBtn {
    background: #546e7a;
}
QPushButton#resetBtn:hover { background: #455a64; }

QLineEdit {
    border: 1px solid #b0bec5;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    background: white;
}
QLineEdit:focus { border-color: #1976d2; }

QTextEdit {
    border: 1px solid #dde1e7;
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
    background: white;
    line-height: 1.5;
}

QTabWidget::pane {
    border: 1px solid #dde1e7;
    border-radius: 6px;
    background: white;
}
QTabBar::tab {
    padding: 7px 16px;
    font-size: 12px;
    border-radius: 4px 4px 0 0;
    background: #e8eaf6;
    margin-right: 2px;
    color: #444;
}
QTabBar::tab:selected { background: white; color: #1a237e; font-weight: bold; }

QCheckBox { font-size: 12px; color: #333; }
QCheckBox::indicator { width: 16px; height: 16px; }

QLabel#propLabel { font-size: 12px; color: #333; }
QLabel#sectionLabel { font-size: 13px; font-weight: bold; color: #1a237e; }

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 8px; background: #f0f2f5; }
QScrollBar::handle:vertical { background: #b0bec5; border-radius: 4px; min-height: 20px; }

QStatusBar { background: #1a237e; color: white; font-size: 12px; padding: 4px 10px; }
QStatusBar QLabel { color: white; }

QComboBox {
    border: 1px solid #b0bec5;
    border-radius: 6px;
    padding: 5px 10px;
    background: white;
    font-size: 12px;
}

QSpinBox, QDoubleSpinBox {
    border: 1px solid #b0bec5;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
    background: white;
}

QFrame#separator { background: #dde1e7; max-height: 1px; }
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
        self.global_stats = {}
        self.district_stats = {}
        self.selected_prop = None
        self.nearby_places = {}
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
        group = QGroupBox("🔍 Фильтры")
        group.setMaximumHeight(120)
        layout = QHBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 6)

        # Цена
        layout.addWidget(QLabel("Цена (млн ₸):"))
        self.filter_price_min = QDoubleSpinBox()
        self.filter_price_min.setRange(0, 1000)
        self.filter_price_min.setValue(0)
        self.filter_price_min.setSuffix(" млн")
        self.filter_price_min.setDecimals(0)
        self.filter_price_min.setMaximumWidth(90)
        layout.addWidget(self.filter_price_min)
        layout.addWidget(QLabel("–"))
        self.filter_price_max = QDoubleSpinBox()
        self.filter_price_max.setRange(0, 1000)
        self.filter_price_max.setValue(1000)
        self.filter_price_max.setSuffix(" млн")
        self.filter_price_max.setDecimals(0)
        self.filter_price_max.setMaximumWidth(90)
        layout.addWidget(self.filter_price_max)

        layout.addWidget(QLabel("  Комнат:"))
        self.filter_rooms_min = QSpinBox()
        self.filter_rooms_min.setRange(0, 10)
        self.filter_rooms_min.setValue(0)
        self.filter_rooms_min.setMaximumWidth(60)
        layout.addWidget(self.filter_rooms_min)
        layout.addWidget(QLabel("–"))
        self.filter_rooms_max = QSpinBox()
        self.filter_rooms_max.setRange(0, 10)
        self.filter_rooms_max.setValue(10)
        self.filter_rooms_max.setMaximumWidth(60)
        layout.addWidget(self.filter_rooms_max)

        layout.addWidget(QLabel("  Год:"))
        self.filter_year_min = QSpinBox()
        self.filter_year_min.setRange(1900, 2030)
        self.filter_year_min.setValue(1900)
        self.filter_year_min.setMaximumWidth(75)
        layout.addWidget(self.filter_year_min)
        layout.addWidget(QLabel("–"))
        self.filter_year_max = QSpinBox()
        self.filter_year_max.setRange(1900, 2030)
        self.filter_year_max.setValue(2030)
        self.filter_year_max.setMaximumWidth(75)
        layout.addWidget(self.filter_year_max)

        layout.addWidget(QLabel("  Площадь (м²):"))
        self.filter_sq_min = QSpinBox()
        self.filter_sq_min.setRange(0, 10000)
        self.filter_sq_min.setValue(0)
        self.filter_sq_min.setMaximumWidth(70)
        layout.addWidget(self.filter_sq_min)
        layout.addWidget(QLabel("–"))
        self.filter_sq_max = QSpinBox()
        self.filter_sq_max.setRange(0, 10000)
        self.filter_sq_max.setValue(10000)
        self.filter_sq_max.setMaximumWidth(70)
        layout.addWidget(self.filter_sq_max)

        layout.addSpacing(10)

        # Чекбоксы
        self.chk_expensive = QCheckBox("Только дорогие (🔴)")
        self.chk_expensive.stateChanged.connect(self._apply_filters)
        layout.addWidget(self.chk_expensive)

        self.chk_heatmap = QCheckBox("Тепловая карта")
        self.chk_heatmap.stateChanged.connect(self._on_heatmap_changed)
        layout.addWidget(self.chk_heatmap)

        self.chk_clusters = QCheckBox("Кластеры")
        self.chk_clusters.stateChanged.connect(self._on_clusters_changed)
        layout.addWidget(self.chk_clusters)

        self.chk_suspicious = QCheckBox("Вне Алматы")
        self.chk_suspicious.stateChanged.connect(self._on_suspicious_changed)
        layout.addWidget(self.chk_suspicious)

        layout.addSpacing(8)
        btn_apply = QPushButton("Применить")
        btn_apply.clicked.connect(self._apply_filters)
        layout.addWidget(btn_apply)

        btn_reset = QPushButton("Сбросить")
        btn_reset.setObjectName("resetBtn")
        btn_reset.clicked.connect(self._reset_filters)
        layout.addWidget(btn_reset)

        layout.addStretch()
        return group

    def _init_filter_ranges(self):
        if self.df is None:
            return
        df = self.df
        self.filter_price_min.setValue(0)
        self.filter_price_max.setValue(int(df['price'].max() / 1_000_000) + 1)
        self.filter_rooms_max.setValue(int(df['live_rooms'].max()))
        self.filter_year_min.setValue(int(df['year'].min()))
        self.filter_year_max.setValue(int(df['year'].max()))
        self.filter_sq_max.setValue(int(df['live_square'].max()) + 1)

    # --------------------------------------------------------
    # Правая панель (вкладки)
    # --------------------------------------------------------

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
        self.selected_prop["district"] = row.get("district", "Район не определён точно")

        # Переключаемся на вкладку объекта
        self.tabs.setCurrentIndex(0)

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

        self._update_property_panel_full()
        self._update_nearby_panel()
        self._update_stats_panel()

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
            style = "color:#1976d2;font-weight:bold" if highlight else ""
            return f"<tr><td style='color:#888;padding:3px 8px 3px 0;width:140px'>{label}</td><td style='{style}'>{value}</td></tr>"

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

    def _update_nearby_panel(self):
        """Обновляет панель объектов рядом."""
        nearby = self.nearby_places

        if not nearby:
            self.nearby_text.setHtml("<p style='color:#888'>Нет данных</p>")
            return

        if "_error" in nearby:
            self.nearby_text.setHtml(
                f"<p style='color:#e53935'>⚠️ {nearby['_error']}</p>"
            )
            return

        total = sum(len(v) for k, v in nearby.items() if not k.startswith("_"))
        html_parts = [f"<p><b>Найдено объектов: {total}</b></p><ul style='margin:4px 0;padding-left:16px;'>"]

        for cat, items in nearby.items():
            if cat.startswith("_") or not items:
                continue
            nearest = items[0]
            html_parts.append(
                f"<li><b>{cat}</b> ({len(items)} шт.) — "
                f"{nearest['name']}, {nearest['distance']} м</li>"
            )

        html_parts.append("</ul>")
        self.nearby_text.setHtml("".join(html_parts))

    # --------------------------------------------------------
    # Статистика
    # --------------------------------------------------------

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
  body {{ font-family: 'Segoe UI', sans-serif; font-size: 12px; }}
  h3 {{ color: #1a237e; margin: 10px 0 5px; font-size: 13px; }}
  p {{ margin: 3px 0; }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; }}
  table {{ width:100%; border-collapse:collapse; margin: 4px 0; }}
  td {{ padding: 3px 6px; }}
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
        html = "<div style='font-family: Segoe UI, sans-serif; font-size: 12px; line-height: 1.6;'>"

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
        if self.df is None:
            return

        params = {
            "min_price": self.filter_price_min.value() * 1_000_000 or None,
            "max_price": self.filter_price_max.value() * 1_000_000 or None,
            "min_rooms": self.filter_rooms_min.value() or None,
            "max_rooms": self.filter_rooms_max.value() or None,
            "min_year": self.filter_year_min.value() or None,
            "max_year": self.filter_year_max.value() or None,
            "min_square": self.filter_sq_min.value() or None,
            "max_square": self.filter_sq_max.value() or None,
            "min_ppm2": None,
            "max_ppm2": None,
            "only_expensive": self.chk_expensive.isChecked(),
        }

        self.map_widget.apply_filters(params)

    def _reset_filters(self):
        self._init_filter_ranges()
        self.chk_expensive.setChecked(False)
        self.chk_heatmap.setChecked(False)
        self.chk_clusters.setChecked(False)
        self._apply_filters()

    def _on_heatmap_changed(self, state):
        val = state == Qt.Checked
        if val:
            self.chk_clusters.setChecked(False)
        self.map_widget.set_show_heatmap(val)

    def _on_clusters_changed(self, state):
        val = state == Qt.Checked
        if val:
            self.chk_heatmap.setChecked(False)
        self.map_widget.set_show_clusters(val)

    def _on_suspicious_changed(self, state):
        val = state == Qt.Checked
        self.map_widget.set_show_suspicious(val)

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
