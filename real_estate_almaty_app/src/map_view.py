# -*- coding: utf-8 -*-
"""
Виджет интерактивной карты на основе QWebEngineView + Leaflet.js.
Связь Python ↔ JavaScript через QWebChannel.
"""

import json
import os
import tempfile
import pandas as pd
import numpy as np

from PySide6.QtCore import QObject, Signal, Slot, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QWidget, QVBoxLayout

from src.config import MAP_TEMPLATE_PATH


# ============================================================
# Мост Python ↔ JavaScript
# ============================================================

class MapBridge(QObject):
    """Объект, передаваемый в JavaScript через QWebChannel."""

    # Сигнал: пользователь кликнул на маркер (передаётся ID объекта)
    markerClicked = Signal(int)

    @Slot(int)
    def onMarkerClicked(self, prop_id: int):
        """Вызывается из JavaScript при клике на маркер."""
        self.markerClicked.emit(prop_id)


# ============================================================
# Виджет карты
# ============================================================

class MapWidget(QWidget):
    """Встраиваемый виджет карты."""

    # Внешний сигнал для MainWindow
    propertySelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = None
        self._temp_html = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.web_view = QWebEngineView(self)

        # ????????? ????????? HTML-????? ????????? ????????-????? ?????
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        layout.addWidget(self.web_view)

        # Настройка WebChannel
        self.channel = QWebChannel(self.web_view.page())
        self.bridge = MapBridge()
        self.channel.registerObject("bridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Подключаем сигнал клика
        self.bridge.markerClicked.connect(self.propertySelected)

    def load_data(self, df: pd.DataFrame):
        """Загружает данные и генерирует HTML-страницу карты."""
        self._df = df
        html_content = self._build_html(df)

                # Записываем HTML рядом с map_template.html, чтобы локальные vendor-файлы работали
        assets_dir = os.path.dirname(MAP_TEMPLATE_PATH)
        path = os.path.join(assets_dir, "generated_map.html")

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self._temp_html = path
        self.web_view.load(QUrl.fromLocalFile(path))

    def _build_html(self, df: pd.DataFrame) -> str:
        """Строит HTML-страницу, вставляя данные как JSON."""
        with open(MAP_TEMPLATE_PATH, encoding="utf-8") as f:
            template = f.read()

        # Формируем компактный массив объектов для JS
        props = []
        for _, row in df.iterrows():
            lat = float(row["map_lat"]) if not pd.isna(row["map_lat"]) else None
            lon = float(row["map_lon"]) if not pd.isna(row["map_lon"]) else None
            if lat is None or lon is None:
                continue

            price_raw = float(row["price"]) if not pd.isna(row.get("price")) else None
            ppm2_raw = float(row["price_per_m2"]) if not pd.isna(row.get("price_per_m2")) else None
            rooms = int(row["live_rooms"]) if not pd.isna(row.get("live_rooms")) else 0
            square = float(row["live_square"]) if not pd.isna(row.get("live_square")) else 0
            year = int(row["year"]) if not pd.isna(row.get("year")) else 0

            props.append({
                "id": int(row["id"]),
                "lat": lat,
                "lon": lon,
                "color": str(row.get("color", "#9e9e9e")),
                "price_raw": price_raw,
                "ppm2_raw": ppm2_raw,
                "rooms": rooms,
                "square": square,
                "year": year,
                "suspicious": bool(row.get("coords_suspicious", False)),
            })

        props_json = json.dumps(props, ensure_ascii=False)
        html = template.replace("PROPERTIES_JSON_PLACEHOLDER", props_json)
        return html

    def apply_filters(self, filter_params: dict):
        """Передаёт параметры фильтра в JavaScript."""
        js = f"applyFilters({json.dumps(filter_params, ensure_ascii=False)});"
        self.web_view.page().runJavaScript(js)

    def set_show_clusters(self, val: bool):
        self.web_view.page().runJavaScript(f"setShowClusters({'true' if val else 'false'});")

    def set_show_heatmap(self, val: bool):
        self.web_view.page().runJavaScript(f"setShowHeatmap({'true' if val else 'false'});")

    def set_show_suspicious(self, val: bool):
        self.web_view.page().runJavaScript(f"setShowSuspicious({'true' if val else 'false'});")

    def reload_data(self, df: pd.DataFrame):
        """Перезагружает данные на карте."""
        self.load_data(df)
