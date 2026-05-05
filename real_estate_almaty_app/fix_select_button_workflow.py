# -*- coding: utf-8 -*-
"""
fix_select_button_workflow.py

Исправляет выбор недвижимости:
- клик по маркеру на карте НЕ должен ломать вкладки;
- после клика кнопка "Применить фильтр" становится зелёной "✅ Выбрать";
- после нажатия "✅ Выбрать" обновляются вкладки "Объект", "Статистика", "ИИ-ассистент";
- если pending-объекта нет, эта же кнопка работает как обычный "Применить фильтр".

Запуск:
python fix_select_button_workflow.py
"""

from pathlib import Path
import re
import shutil
import py_compile

MAIN_PATH = Path("main.py")
if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти скрипт из папки проекта.")

backup = Path("main.py.backup_select_button_workflow")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

ON_PROPERTY_SELECTED = "    def _on_property_selected(self, prop_id):\n        \"\"\"\n        Клик по маркеру на карте НЕ сразу открывает карточку.\n        Он ставит объект в ожидание выбора и превращает кнопку\n        \"Применить фильтр\" в зелёную кнопку \"✅ Выбрать\".\n        \"\"\"\n        if self.df is None:\n            return\n\n        try:\n            prop_id = int(prop_id)\n        except Exception:\n            return\n\n        # Ищем объект сначала в отфильтрованных данных, потом во всей базе\n        row = None\n        try:\n            source_df = self.filtered_df if getattr(self, \"filtered_df\", None) is not None else self.df\n            rows = source_df.loc[source_df[\"id\"] == prop_id]\n            if len(rows) > 0:\n                row = rows.iloc[0]\n        except Exception:\n            row = None\n\n        if row is None:\n            try:\n                rows = self.df.loc[self.df[\"id\"] == prop_id]\n                if len(rows) > 0:\n                    row = rows.iloc[0]\n            except Exception:\n                row = None\n\n        if row is None:\n            try:\n                self.status_bar.showMessage(\"Не удалось найти выбранный объект в данных.\", 5000)\n            except Exception:\n                pass\n            return\n\n        try:\n            prop = get_property_dict(row)\n        except Exception:\n            prop = row.to_dict()\n\n        # Дополняем техническими и гео-данными\n        try:\n            prop[\"id\"] = int(row.get(\"id\", prop_id))\n        except Exception:\n            prop[\"id\"] = prop_id\n\n        prop[\"district\"] = row.get(\"district\", prop.get(\"district\", \"Район не определён точно\"))\n        prop[\"microdistrict\"] = row.get(\"microdistrict\", prop.get(\"microdistrict\", \"Не определён\"))\n\n        # Координаты нужны геокодеру / объектам рядом / ИИ\n        try:\n            prop[\"lat\"] = float(row.get(\"map_lat\", row.get(\"lat\", prop.get(\"lat\", 0))))\n            prop[\"lon\"] = float(row.get(\"map_lon\", row.get(\"lon\", prop.get(\"lon\", 0))))\n            prop[\"map_lat\"] = prop[\"lat\"]\n            prop[\"map_lon\"] = prop[\"lon\"]\n            prop[\"lat_raw\"] = prop[\"lat\"]\n            prop[\"lon_raw\"] = prop[\"lon\"]\n        except Exception:\n            pass\n\n        # Сохраняем как ожидающий выбор\n        self.pending_prop = prop\n        self.pending_prop_id = prop_id\n\n        # Кнопка \"Применить фильтр\" временно становится \"Выбрать\"\n        self._set_apply_button_select_mode(True)\n\n        try:\n            title = prop.get(\"address\") or prop.get(\"title\") or f\"ID {prop_id}\"\n            self.status_bar.showMessage(\n                f\"Объект выбран на карте: {title}. Нажмите зелёную кнопку «Выбрать».\",\n                8000\n            )\n        except Exception:\n            pass\n\n        # Небольшая подсказка в ИИ, но сами вкладки пока не заполняем\n        try:\n            if hasattr(self, \"ai_context_label\"):\n                self.ai_context_label.setText(\"Объект отмечен на карте. Нажмите «✅ Выбрать», чтобы загрузить данные.\")\n        except Exception:\n            pass\n"
SET_BUTTON_MODE = "    def _set_apply_button_select_mode(self, is_select_mode: bool):\n        \"\"\"\n        Переключает главную кнопку:\n        - обычный режим: Применить фильтр\n        - после клика по маркеру: ✅ Выбрать\n        \"\"\"\n        btn = getattr(self, \"btn_apply_filters\", None)\n        if btn is None:\n            return\n\n        if is_select_mode:\n            btn.setText(\"✅ Выбрать\")\n            btn.setToolTip(\"Подтвердить выбранную недвижимость и обновить вкладки\")\n            btn.setStyleSheet(\n                \"QPushButton { background:#16a34a; color:white; border:none; border-radius:12px; \"\n                \"padding:8px 16px; font-size:13px; font-weight:900; }\"\n                \"QPushButton:hover { background:#15803d; }\"\n                \"QPushButton:pressed { background:#166534; }\"\n            )\n        else:\n            btn.setText(\"✅ Применить фильтр\")\n            btn.setToolTip(\"Применить выбранные параметры фильтра к карте\")\n            btn.setStyleSheet(\"\")  # возвращаем стиль из STYLE_SHEET\n"
COMMIT_METHOD = "    def _commit_pending_selection(self):\n        \"\"\"\n        Подтверждает объект, который был кликнут на карте.\n        После этого обновляются вкладки: Объект, Статистика, ИИ-ассистент.\n        \"\"\"\n        prop = getattr(self, \"pending_prop\", None)\n        if not prop:\n            return False\n\n        self.selected_prop = dict(prop)\n        self.pending_prop = None\n        self.pending_prop_id = None\n\n        self.nearby_places = {}\n        self.nearby_show_all = False\n\n        try:\n            if hasattr(self, \"nearby_more_btn\"):\n                self.nearby_more_btn.setVisible(False)\n                self.nearby_more_btn.setText(\"Показать больше объектов рядом\")\n        except Exception:\n            pass\n\n        # Возвращаем кнопку в режим фильтра\n        self._set_apply_button_select_mode(False)\n\n        # Сразу обновляем все вкладки базовыми данными\n        try:\n            if hasattr(self, \"_ensure_selected_microdistrict\"):\n                self._ensure_selected_microdistrict()\n        except Exception:\n            pass\n\n        try:\n            if hasattr(self, \"_update_property_panel_basic\"):\n                self._update_property_panel_basic()\n            elif hasattr(self, \"_update_property_panel\"):\n                self._update_property_panel()\n        except Exception:\n            pass\n\n        try:\n            if hasattr(self, \"_update_stats_panel\"):\n                self._update_stats_panel()\n        except Exception:\n            pass\n\n        try:\n            if hasattr(self, \"_update_ai_context_panel\"):\n                self._update_ai_context_panel()\n        except Exception:\n            pass\n\n        # Стартуем геокодинг и объекты рядом в фоне\n        try:\n            if hasattr(self, \"nearby_text\"):\n                self.nearby_text.setHtml(\n                    \"<p style='color:#64748b;background:#ffffff;'>Загрузка адреса и объектов рядом...</p>\"\n                )\n            self._start_geo_thread()\n        except Exception:\n            pass\n\n        try:\n            title = self.selected_prop.get(\"address\") or self.selected_prop.get(\"title\") or \"объект\"\n            self.status_bar.showMessage(f\"Выбран объект: {title}\", 7000)\n        except Exception:\n            pass\n\n        return True\n"
APPLY_METHOD = "    def _apply_filters(self):\n        \"\"\"\n        Одна кнопка выполняет две роли:\n        1) если пользователь кликнул объект на карте — кнопка работает как \"✅ Выбрать\";\n        2) если объекта в ожидании нет — кнопка работает как \"✅ Применить фильтр\".\n        \"\"\"\n        # Режим выбора объекта\n        if getattr(self, \"pending_prop\", None) is not None:\n            self._commit_pending_selection()\n            return\n\n        if self.df is None:\n            return\n\n        required = [\n            \"filter_price_min\", \"filter_price_max\",\n            \"filter_ppm2_min\", \"filter_ppm2_max\",\n            \"filter_rooms_min\", \"filter_rooms_max\",\n            \"filter_year_min\", \"filter_year_max\",\n            \"filter_sq_min\", \"filter_sq_max\",\n            \"filter_district\", \"filter_microdistrict\", \"filter_price_category\"\n        ]\n        if any(not hasattr(self, name) for name in required):\n            return\n\n        df = self.df.copy()\n        total = len(df)\n\n        # По умолчанию показываем только объекты в Алматы\n        if \"coords_suspicious\" in df.columns:\n            df = df[~df[\"coords_suspicious\"]].copy()\n\n        # Цена квартиры, млн ₸\n        if \"price\" in df.columns:\n            min_price = min(self.filter_price_min.value(), self.filter_price_max.value()) * 1_000_000\n            max_price = max(self.filter_price_min.value(), self.filter_price_max.value()) * 1_000_000\n            df = df[(df[\"price\"] >= min_price) & (df[\"price\"] <= max_price)].copy()\n\n        # Цена за м², тыс ₸\n        if \"price_per_m2\" in df.columns:\n            min_ppm2 = min(self.filter_ppm2_min.value(), self.filter_ppm2_max.value()) * 1000\n            max_ppm2 = max(self.filter_ppm2_min.value(), self.filter_ppm2_max.value()) * 1000\n            df = df[(df[\"price_per_m2\"] >= min_ppm2) & (df[\"price_per_m2\"] <= max_ppm2)].copy()\n\n        # Комнаты\n        if \"live_rooms\" in df.columns:\n            min_rooms = min(self.filter_rooms_min.value(), self.filter_rooms_max.value())\n            max_rooms = max(self.filter_rooms_min.value(), self.filter_rooms_max.value())\n            df = df[(df[\"live_rooms\"] >= min_rooms) & (df[\"live_rooms\"] <= max_rooms)].copy()\n\n        # Год постройки\n        if \"year\" in df.columns:\n            min_year = min(self.filter_year_min.value(), self.filter_year_max.value())\n            max_year = max(self.filter_year_min.value(), self.filter_year_max.value())\n            df = df[(df[\"year\"] >= min_year) & (df[\"year\"] <= max_year)].copy()\n\n        # Площадь\n        if \"live_square\" in df.columns:\n            min_sq = min(self.filter_sq_min.value(), self.filter_sq_max.value())\n            max_sq = max(self.filter_sq_min.value(), self.filter_sq_max.value())\n            df = df[(df[\"live_square\"] >= min_sq) & (df[\"live_square\"] <= max_sq)].copy()\n\n        # Район\n        district = self.filter_district.currentText()\n        if district and district != \"Все районы\" and \"district\" in df.columns:\n            clean_districts = (\n                df[\"district\"].astype(str)\n                .str.replace(\" (приближённо)\", \"\", regex=False)\n                .str.replace(\" (??????????)\", \"\", regex=False)\n                .str.strip()\n            )\n            df = df[clean_districts == district].copy()\n\n        # Микрорайон\n        micro = self.filter_microdistrict.currentText()\n        if micro and micro != \"Все микрорайоны\":\n            if hasattr(self, \"_filter_by_microdistrict_smart\"):\n                df = self._filter_by_microdistrict_smart(df, micro)\n            elif \"microdistrict\" in df.columns:\n                df = df[df[\"microdistrict\"].astype(str).str.strip() == micro].copy()\n\n        # Категория цены за м²\n        category = self.filter_price_category.currentText()\n        if \"price_per_m2\" in df.columns:\n            if category.startswith(\"🔴\"):\n                df = df[df[\"price_per_m2\"] >= 1_000_000].copy()\n            elif category.startswith(\"🟠\"):\n                df = df[(df[\"price_per_m2\"] >= 700_000) & (df[\"price_per_m2\"] < 1_000_000)].copy()\n            elif category.startswith(\"🟡\"):\n                df = df[(df[\"price_per_m2\"] >= 500_000) & (df[\"price_per_m2\"] < 700_000)].copy()\n            elif category.startswith(\"🟢\"):\n                df = df[(df[\"price_per_m2\"] >= 300_000) & (df[\"price_per_m2\"] < 500_000)].copy()\n            elif category.startswith(\"🔵\"):\n                df = df[df[\"price_per_m2\"] < 300_000].copy()\n\n        self.filtered_df = df.copy()\n\n        # Если после фильтра ранее выбранный объект исчез — очищаем вкладки.\n        if self.selected_prop is not None:\n            selected_id = self.selected_prop.get(\"id\")\n            visible_ids = set(df[\"id\"].tolist()) if len(df) and \"id\" in df.columns else set()\n            if selected_id not in visible_ids:\n                if hasattr(self, \"_clear_selection_panels\"):\n                    self._clear_selection_panels(\"Выбранный объект не входит в текущий фильтр.\")\n                else:\n                    self.selected_prop = None\n                    self.nearby_places = {}\n\n        # Перезагружаем карту отфильтрованными объектами\n        if hasattr(self, \"map_widget\"):\n            self.map_widget.load_data(df)\n\n        shown = len(df)\n        status_text = f\"Показано {shown:,} из {total:,} объектов\".replace(\",\", \" \")\n\n        if hasattr(self, \"filter_result_label\"):\n            self.filter_result_label.setText(status_text)\n\n        if hasattr(self, \"status_bar\"):\n            self.status_bar.showMessage(\"Фильтр применён: \" + status_text)\n\n        # После применения фильтра кнопка точно должна быть обратно фильтром\n        self.pending_prop = None\n        self.pending_prop_id = None\n        self._set_apply_button_select_mode(False)\n\n        try:\n            if hasattr(self, \"_update_stats_panel\"):\n                self._update_stats_panel()\n        except Exception:\n            pass\n"
RESET_METHOD = "    def _reset_filters(self):\n        \"\"\"\n        Сброс фильтров + сброс выбранного/ожидающего объекта.\n        После сброса вкладки Объект/Статистика/ИИ пустые.\n        \"\"\"\n        self.pending_prop = None\n        self.pending_prop_id = None\n        self._set_apply_button_select_mode(False)\n\n        if self.df is None:\n            if hasattr(self, \"_clear_selection_panels\"):\n                self._clear_selection_panels(\"Нет загруженных данных\")\n            return\n\n        try:\n            self.chk_expensive.setChecked(False)\n            self.chk_heatmap.setChecked(False)\n            self.chk_clusters.setChecked(False)\n            self.chk_suspicious.setChecked(False)\n        except Exception:\n            pass\n\n        try:\n            self.map_widget.set_show_heatmap(False)\n            self.map_widget.set_show_clusters(False)\n            self.map_widget.set_show_suspicious(False)\n        except Exception:\n            pass\n\n        # Перезаполняем фильтры и карту\n        self._init_filter_ranges()\n\n        # После _init_filter_ranges / _apply_filters принудительно очищаем вкладки\n        if hasattr(self, \"_clear_selection_panels\"):\n            self._clear_selection_panels(\"Фильтры сброшены. Выберите объект на карте.\")\n        else:\n            self.selected_prop = None\n            self.nearby_places = {}\n"
INIT_EXTRA = "        self.pending_prop = None\n        self.pending_prop_id = None\n"

def method_bounds(source: str, method_name: str):
    matches = list(re.finditer(rf"(?m)^    def {re.escape(method_name)}\s*\(", source))
    if not matches:
        return None
    m = matches[0]
    next_m = re.search(r"(?m)^    def \w+\s*\(", source[m.end():])
    end = m.end() + next_m.start() if next_m else len(source)
    return m.start(), end

def replace_or_insert(source: str, method_name: str, new_method: str, before_method: str | None = None) -> str:
    bounds = method_bounds(source, method_name)
    if bounds:
        start, end = bounds
        print("Replaced:", method_name)
        return source[:start] + new_method.rstrip() + "\n" + source[end:]

    if before_method:
        marker = "\n    def " + before_method
        if marker in source:
            print("Inserted:", method_name, "before", before_method)
            return source.replace(marker, "\n" + new_method.rstrip() + "\n" + marker, 1)

    marker = "\n    def _apply_filters"
    if marker in source:
        print("Inserted:", method_name, "before _apply_filters")
        return source.replace(marker, "\n" + new_method.rstrip() + "\n" + marker, 1)

    raise RuntimeError(f"Не найден метод {method_name} и место для вставки.")

# Добавляем pending поля в __init__
if "self.pending_prop" not in text:
    marker = "        self.selected_prop = None\n"
    if marker in text:
        text = text.replace(marker, marker + INIT_EXTRA, 1)
        print("OK: pending_prop fields added to __init__")
    else:
        print("WARNING: could not add pending_prop fields to __init__")
else:
    print("OK: pending_prop fields already exist")

# Методы workflow
text = replace_or_insert(text, "_set_apply_button_select_mode", SET_BUTTON_MODE, "_commit_pending_selection")
text = replace_or_insert(text, "_commit_pending_selection", COMMIT_METHOD, "_on_property_selected")
text = replace_or_insert(text, "_on_property_selected", ON_PROPERTY_SELECTED, "_apply_filters")
text = replace_or_insert(text, "_apply_filters", APPLY_METHOD, "_reset_filters")
text = replace_or_insert(text, "_reset_filters", RESET_METHOD, "_on_heatmap_changed")

MAIN_PATH.write_text(text, encoding="utf-8")
py_compile.compile(str(MAIN_PATH), doraise=True)

print("DONE: select-button workflow installed.")
print("Run: python main.py")
