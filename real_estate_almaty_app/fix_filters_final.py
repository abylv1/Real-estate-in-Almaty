# -*- coding: utf-8 -*-
"""
fix_filters_final.py

Финальная замена логики фильтров:
- фильтрация работает в Python, а не только в JavaScript;
- карта заново получает только отфильтрованные квартиры;
- добавлены фильтры: район, микрорайон, цена, цена за м², комнаты, год, площадь, категория;
- исправлен статус "показано N из M";
- выбранный объект корректно очищается, если он не подходит под фильтр.

Запускать из корня проекта:
python fix_filters_final.py
"""

from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("Не найден main.py. Запусти этот файл из корня проекта real_estate_almaty_app.")

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

backup = Path("main.py.backup_filters_final")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)


def ensure_import(source: str) -> str:
    """Добавляет QGridLayout в импорт PySide6.QtWidgets."""
    if "QGridLayout" in source:
        return source

    source = source.replace(
        "QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,",
        "QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,"
    )
    return source


def replace_method(source: str, name: str, new_code: str) -> str:
    """
    Заменяет метод внутри класса MainWindow по имени.
    Метод должен иметь отступ 4 пробела.
    """
    pattern = rf"\n    def {re.escape(name)}\([^\n]*\):[\s\S]*?(?=\n    def |\n# ============================================================|\Z)"
    new_block = "\n" + new_code.rstrip() + "\n"
    source2, count = re.subn(pattern, new_block, source, count=1)
    if count == 0:
        print(f"WARNING: method {name} not found; adding before closeEvent if possible")
        marker = "\n    def closeEvent"
        if marker in source:
            source2 = source.replace(marker, new_block + marker, 1)
        else:
            source2 = source + new_block
    else:
        print(f"OK: replaced {name}")
    return source2


text = ensure_import(text)

# Добавляем self.filtered_df, если нет
if "self.filtered_df" not in text:
    text = text.replace(
        "        self.df = None\n",
        "        self.df = None\n        self.filtered_df = None\n",
        1
    )
    print("OK: added self.filtered_df")


new_build_filters = '''    def _build_filters_panel(self) -> QGroupBox:
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
        self.filter_district.addItem("Все районы")
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

        return group'''


new_init_filter_ranges = '''    def _init_filter_ranges(self):
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
        if "district" in df.columns:
            districts = sorted([
                str(x) for x in df["district"].dropna().unique()
                if str(x).strip()
            ])
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
        self._apply_filters()'''


new_apply_filters = '''    def _apply_filters(self):
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
        if district and district != "Все районы" and "district" in df.columns:
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
            pass'''


new_reset_filters = '''    def _reset_filters(self):
        """Полный сброс фильтров."""
        if self.df is None:
            return
        self._init_filter_ranges()'''


new_heatmap = '''    def _on_heatmap_changed(self, state):
        val = state == Qt.Checked
        if val and hasattr(self, "chk_clusters"):
            self.chk_clusters.blockSignals(True)
            self.chk_clusters.setChecked(False)
            self.chk_clusters.blockSignals(False)
        try:
            self.map_widget.set_show_heatmap(val)
        except Exception:
            pass'''


new_clusters = '''    def _on_clusters_changed(self, state):
        val = state == Qt.Checked
        if val and hasattr(self, "chk_heatmap"):
            self.chk_heatmap.blockSignals(True)
            self.chk_heatmap.setChecked(False)
            self.chk_heatmap.blockSignals(False)
        try:
            self.map_widget.set_show_clusters(val)
        except Exception:
            pass'''


new_suspicious = '''    def _on_suspicious_changed(self, state):
        self._apply_filters()'''


new_refresh_micro = '''    def _refresh_microdistrict_filter_values(self):
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

        self.filter_microdistrict.blockSignals(False)'''


# Заменяем методы
text = replace_method(text, "_build_filters_panel", new_build_filters)
text = replace_method(text, "_init_filter_ranges", new_init_filter_ranges)
text = replace_method(text, "_apply_filters", new_apply_filters)
text = replace_method(text, "_reset_filters", new_reset_filters)
text = replace_method(text, "_on_heatmap_changed", new_heatmap)
text = replace_method(text, "_on_clusters_changed", new_clusters)
text = replace_method(text, "_on_suspicious_changed", new_suspicious)

if "def _refresh_microdistrict_filter_values" not in text:
    # Добавляем перед _update_property_panel_basic, потому что это рядом с geo result
    marker = "\n    def _update_property_panel_basic"
    if marker in text:
        text = text.replace(marker, "\n" + new_refresh_micro + "\n" + marker, 1)
        print("OK: added _refresh_microdistrict_filter_values")
    else:
        text = text + "\n" + new_refresh_micro + "\n"

# Патчим _on_geo_result: после обновления df обновлять список микрорайонов
if "self._refresh_microdistrict_filter_values()" not in text:
    text = text.replace(
        "        self._update_property_panel_full()\n        self._update_nearby_panel()\n        self._update_stats_panel()\n",
        "        self._refresh_microdistrict_filter_values()\n        self._update_property_panel_full()\n        self._update_nearby_panel()\n        self._update_stats_panel()\n",
        1
    )
    print("OK: patched _on_geo_result microdistrict refresh")

# Убираем принудительный переход на вкладку объект, если он есть
text = text.replace(
    "        # Переключаемся на вкладку объекта\n        self.tabs.setCurrentIndex(0)\n\n",
    "        # Вкладку не переключаем автоматически: объект обновляется во всех вкладках.\n\n"
)

# Улучшаем статистику, чтобы она брала filtered_df, если такой есть
text = text.replace(
    "        html = build_stats_html(self.global_stats, self.district_stats, self.selected_prop, self.df)",
    "        stats_df = self.filtered_df if self.filtered_df is not None else self.df\n        current_global_stats = compute_global_stats(stats_df)\n        current_district_stats = compute_district_stats(stats_df)\n        html = build_stats_html(current_global_stats, current_district_stats, self.selected_prop, stats_df)"
)

MAIN_PATH.write_text(text, encoding="utf-8")
print("DONE: main.py filters replaced")
print("Now run:")
print("python main.py")
