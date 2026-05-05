# -*- coding: utf-8 -*-
"""
fix_selection_reset_sync.py

Исправляет поведение:
1) "Сбросить всё" очищает вкладки Объект / Статистика / ИИ-ассистент.
2) Когда кликаешь другой объект на карте, все вкладки сразу обновляются под новый объект.
3) Когда нажимаешь "Применить фильтр", вкладки синхронизируются:
   - выбранный объект остался в фильтре -> вкладки обновляются;
   - выбранный объект исчез из фильтра -> вкладки очищаются.

Запуск:
python fix_selection_reset_sync.py
"""

from pathlib import Path
import re
import shutil
import py_compile

MAIN_PATH = Path("main.py")
if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти скрипт из папки проекта.")

backup = Path("main.py.backup_selection_reset_sync")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

CLEAR_METHOD = "    def _clear_selection_panels(self, reason: str = \"Выберите объект на карте\"):\n        \"\"\"\n        Полностью очищает вкладки \"Объект\", \"Статистика\", \"ИИ-ассистент\".\n        Используется при кнопке \"Сбросить всё\" и когда выбранный объект исчез после фильтра.\n        \"\"\"\n        self.selected_prop = None\n        self.nearby_places = {}\n\n        # Объект\n        try:\n            if hasattr(self, \"prop_title\"):\n                self.prop_title.setText(\"Выберите объект на карте\")\n            if hasattr(self, \"prop_details\"):\n                self.prop_details.setHtml(\n                    \"<div style='font-family:Segoe UI;color:#64748b;background:#ffffff;'>\"\n                    \"<p>Нет выбранного объекта.</p>\"\n                    \"</div>\"\n                )\n            if hasattr(self, \"nearby_text\"):\n                self.nearby_text.setHtml(\n                    \"<div style='font-family:Segoe UI;color:#64748b;background:#ffffff;'>\"\n                    \"<p>Объекты рядом появятся после выбора недвижимости на карте.</p>\"\n                    \"</div>\"\n                )\n        except Exception:\n            pass\n\n        # Статистика\n        try:\n            if hasattr(self, \"stats_display\"):\n                self.stats_display.setHtml(\n                    \"<div style='font-family:Segoe UI;color:#64748b;background:#ffffff;'>\"\n                    \"<h3 style='color:#1a237e'>📊 Статистика</h3>\"\n                    \"<p>Нет выбранного объекта.</p>\"\n                    \"<p>Выберите недвижимость на карте, чтобы увидеть сравнение цены, района и объекта.</p>\"\n                    \"</div>\"\n                )\n        except Exception:\n            pass\n\n        # ИИ-ассистент\n        try:\n            if hasattr(self, \"ai_context_label\"):\n                self.ai_context_label.setText(\"Сначала выберите объект на карте\")\n            if hasattr(self, \"ai_input\"):\n                self.ai_input.clear()\n            if hasattr(self, \"ai_response\"):\n                self.ai_response.setHtml(\n                    \"<div style='font-family:Segoe UI;color:#64748b;background:#ffffff;'>\"\n                    \"<h3 style='color:#1a237e'>🤖 ИИ-ассистент</h3>\"\n                    \"<p>Нет выбранного объекта.</p>\"\n                    \"<p>Кликните по недвижимости на карте, затем задайте вопрос.</p>\"\n                    \"</div>\"\n                )\n        except Exception:\n            pass\n\n        try:\n            self.status_bar.showMessage(reason, 5000)\n        except Exception:\n            pass\n"
REFRESH_METHOD = "    def _refresh_panels_for_selected_property(self):\n        \"\"\"\n        Обновляет все вкладки под текущий selected_prop:\n        Объект, Статистика, ИИ-ассистент.\n        Вызывается при клике на другой объект и после применения фильтра.\n        \"\"\"\n        if self.selected_prop is None:\n            self._clear_selection_panels()\n            return\n\n        try:\n            if hasattr(self, \"_ensure_selected_microdistrict\"):\n                self._ensure_selected_microdistrict()\n        except Exception:\n            pass\n\n        # 1) Вкладка \"Объект\"\n        updated_object = False\n        for method_name in [\n            \"_update_property_panel_full\",\n            \"_update_property_panel_basic\",\n            \"_update_property_panel\",\n            \"_update_object_panel\",\n        ]:\n            method = getattr(self, method_name, None)\n            if callable(method):\n                try:\n                    method()\n                    updated_object = True\n                    break\n                except TypeError:\n                    try:\n                        method(self.selected_prop)\n                        updated_object = True\n                        break\n                    except Exception:\n                        pass\n                except Exception:\n                    pass\n\n        # 2) Вкладка \"Статистика\"\n        try:\n            if hasattr(self, \"_update_stats_panel\"):\n                self._update_stats_panel()\n        except Exception:\n            pass\n\n        # 3) Вкладка \"ИИ-ассистент\"\n        try:\n            if hasattr(self, \"_update_ai_context_panel\"):\n                self._update_ai_context_panel()\n        except Exception:\n            pass\n\n        # Если объектная вкладка не обновилась существующими методами — базовый fallback\n        if not updated_object:\n            try:\n                prop = self.selected_prop\n                title = str(prop.get(\"title\") or prop.get(\"address\") or \"Выбранный объект\")\n                if hasattr(self, \"prop_title\"):\n                    self.prop_title.setText(title)\n\n                district = str(prop.get(\"district\", \"Не определён\"))\n                micro = str(prop.get(\"microdistrict\", \"Не определён\"))\n                price = prop.get(\"price\", \"—\")\n                ppm2 = prop.get(\"price_per_m2\", prop.get(\"price_per_m2_raw\", \"—\"))\n\n                if hasattr(self, \"prop_details\"):\n                    self.prop_details.setHtml(\n                        \"<div style='font-family:Segoe UI;color:#111827;background:#ffffff;'>\"\n                        f\"<h3 style='color:#1a237e'>{title}</h3>\"\n                        f\"<p><b>Район:</b> {district}</p>\"\n                        f\"<p><b>Микрорайон:</b> {micro}</p>\"\n                        f\"<p><b>Цена:</b> {price}</p>\"\n                        f\"<p><b>Цена за м²:</b> {ppm2}</p>\"\n                        \"</div>\"\n                    )\n            except Exception:\n                pass\n"
ON_SELECTED_METHOD = "    def _on_property_selected(self, prop_data):\n        \"\"\"\n        Когда пользователь выбирает другую недвижимость на карте,\n        все вкладки должны сразу обновиться под новый объект.\n        \"\"\"\n        if not prop_data:\n            self._clear_selection_panels(\"Объект не выбран\")\n            return\n\n        try:\n            self.selected_prop = dict(prop_data)\n        except Exception:\n            self.selected_prop = prop_data\n\n        # Сразу переключать вкладку не обязательно: данные обновятся во всех вкладках,\n        # а пользователь сам может перейти в \"Объект\", \"Статистика\" или \"ИИ-ассистент\".\n        self._refresh_panels_for_selected_property()\n\n        try:\n            title = self.selected_prop.get(\"title\") or self.selected_prop.get(\"address\") or \"объект\"\n            self.status_bar.showMessage(f\"Выбран объект: {title}\", 5000)\n        except Exception:\n            pass\n"
RESET_METHOD = "    def _reset_filters(self):\n        \"\"\"\n        Полный сброс фильтров, карты и выбранного объекта.\n        После нажатия \"Сбросить всё\" вкладки \"Объект\", \"Статистика\", \"ИИ-ассистент\" очищаются.\n        \"\"\"\n        if self.df is None:\n            self._clear_selection_panels(\"Нет загруженных данных\")\n            return\n\n        try:\n            self.chk_expensive.setChecked(False)\n            self.chk_heatmap.setChecked(False)\n            self.chk_clusters.setChecked(False)\n            self.chk_suspicious.setChecked(False)\n        except Exception:\n            pass\n\n        try:\n            self.map_widget.set_show_heatmap(False)\n            self.map_widget.set_show_clusters(False)\n            self.map_widget.set_show_suspicious(False)\n        except Exception:\n            pass\n\n        # Перезаполняем поля фильтров без старого выбранного объекта\n        self.selected_prop = None\n        self.nearby_places = {}\n\n        self._init_filter_ranges()\n\n        # _init_filter_ranges может вызвать _apply_filters и статистику — после этого принудительно очищаем вкладки\n        self._clear_selection_panels(\"Фильтры сброшены. Выберите объект на карте.\")\n"
APPLY_TAIL_CODE = "        # Синхронизация вкладок после кнопки \"Применить фильтр\"\n        # Если выбранный объект остался на карте — обновляем все вкладки под него.\n        # Если выбранный объект больше не подходит под фильтр — очищаем вкладки.\n        try:\n            if self.selected_prop is not None:\n                selected_id = self.selected_prop.get(\"id\")\n                visible_ids = set(df[\"id\"].tolist()) if len(df) and \"id\" in df.columns else set()\n\n                if selected_id in visible_ids:\n                    # Берём свежую строку из df после фильтра, чтобы данные точно соответствовали карте\n                    try:\n                        fresh_row = df[df[\"id\"] == selected_id].iloc[0].to_dict()\n                        self.selected_prop.update(fresh_row)\n                    except Exception:\n                        pass\n                    self._refresh_panels_for_selected_property()\n                else:\n                    self._clear_selection_panels(\"Выбранный объект не входит в текущий фильтр.\")\n            else:\n                # Если фильтр применили без выбранного объекта — вкладки остаются пустыми.\n                self._clear_selection_panels(\"Фильтр применён. Выберите объект на карте.\")\n        except Exception:\n            pass\n"

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

    # fallback before _apply_filters
    marker = "\n    def _apply_filters"
    if marker in source:
        print("Inserted:", method_name, "before _apply_filters")
        return source.replace(marker, "\n" + new_method.rstrip() + "\n" + marker, 1)

    raise RuntimeError(f"Не найден метод {method_name} и место для вставки.")

# 1) Add/replace helper methods
text = replace_or_insert(text, "_clear_selection_panels", CLEAR_METHOD, "_refresh_panels_for_selected_property")
text = replace_or_insert(text, "_refresh_panels_for_selected_property", REFRESH_METHOD, "_on_property_selected")

# 2) Replace selection and reset methods
text = replace_or_insert(text, "_on_property_selected", ON_SELECTED_METHOD, "_apply_filters")
text = replace_or_insert(text, "_reset_filters", RESET_METHOD, "_apply_filters")

# 3) Patch _apply_filters: add synchronization before method ends.
bounds = method_bounds(text, "_apply_filters")
if not bounds:
    raise RuntimeError("Не найден _apply_filters")

start, end = bounds
apply_body = text[start:end]

# Remove old sync code if patch was run before
apply_body = re.sub(
    r"\n\s*# Синхронизация вкладок после кнопки \"Применить фильтр\"[\s\S]*?except Exception:\s*\n\s*pass\s*\n",
    "\n",
    apply_body,
    count=1,
)

# Insert before final try _update_stats_panel if exists, otherwise before end of method.
inserted = False

# Good place: after map_widget.load_data(df)
target = "self.map_widget.load_data(df)"
idx = apply_body.find(target)
if idx != -1:
    line_end = apply_body.find("\n", idx)
    if line_end != -1:
        apply_body = apply_body[:line_end+1] + "\n" + APPLY_TAIL_CODE.rstrip() + "\n" + apply_body[line_end+1:]
        inserted = True
        print("OK: selection sync inserted after map_widget.load_data(df)")

if not inserted:
    # Insert near end before next method boundary
    apply_body = apply_body.rstrip() + "\n\n" + APPLY_TAIL_CODE.rstrip() + "\n"
    print("OK: selection sync appended to _apply_filters")

text = text[:start] + apply_body + text[end:]

MAIN_PATH.write_text(text, encoding="utf-8")
py_compile.compile(str(MAIN_PATH), doraise=True)

print("DONE: selection/reset synchronization installed.")
print("Run: python main.py")
