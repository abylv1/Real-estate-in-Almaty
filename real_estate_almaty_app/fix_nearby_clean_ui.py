# -*- coding: utf-8 -*-
"""
Fix nearby places UI:
- remove technical header: source/radius/OSM explanation
- remove OSM tags from UI
- remove 'Еще скрыто...' text
- make the button switch compact/detailed mode
- keep categories, names, distance, type, address, warnings

Run from project root:
    python fix_nearby_clean_ui.py
"""

from pathlib import Path
import re

PROJECT = Path.cwd()
main_path = PROJECT / "main.py"

if not main_path.exists():
    raise SystemExit("ERROR: main.py not found. Run this file from the project root folder.")

s = main_path.read_text(encoding="utf-8", errors="replace")
backup = main_path.with_suffix(".py.backup_nearby_clean_ui")
if not backup.exists():
    backup.write_text(s, encoding="utf-8")

# Ensure state field exists
if "self.nearby_show_all" not in s:
    s = s.replace(
        "        self.nearby_places = {}\n",
        "        self.nearby_places = {}\n        self.nearby_show_all = False\n",
        1,
    )

# Ensure button exists. Put it BEFORE the QTextEdit when possible, so it is easy to see.
if "self.nearby_more_btn" not in s:
    s = s.replace(
        "        nearby_label = QLabel(\"📍 Объекты рядом\")\n        nearby_label.setObjectName(\"sectionLabel\")\n        layout.addWidget(nearby_label)\n\n        self.nearby_text = QTextEdit()",
        "        nearby_label = QLabel(\"📍 Объекты рядом\")\n        nearby_label.setObjectName(\"sectionLabel\")\n        layout.addWidget(nearby_label)\n\n        self.nearby_more_btn = QPushButton(\"Показать больше объектов рядом\")\n        self.nearby_more_btn.setObjectName(\"resetBtn\")\n        self.nearby_more_btn.clicked.connect(self._toggle_nearby_show_all)\n        self.nearby_more_btn.setVisible(False)\n        layout.addWidget(self.nearby_more_btn)\n\n        self.nearby_text = QTextEdit()",
        1,
    )
else:
    # If button already exists below QTextEdit, keep it but normalize text.
    s = re.sub(
        r'self\.nearby_more_btn\s*=\s*QPushButton\([^\n]*\)',
        'self.nearby_more_btn = QPushButton("Показать больше объектов рядом")',
        s,
        count=1,
    )

# Reset button and state on selected property
if "self.nearby_more_btn.setText('Показать больше объектов рядом')" not in s and "self.nearby_more_btn.setText(\"Показать больше объектов рядом\")" not in s:
    s = s.replace(
        "        self.selected_prop = get_property_dict(row)\n        self.nearby_places = {}\n",
        "        self.selected_prop = get_property_dict(row)\n        self.nearby_places = {}\n        self.nearby_show_all = False\n        if hasattr(self, 'nearby_more_btn'):\n            self.nearby_more_btn.setVisible(False)\n            self.nearby_more_btn.setText('Показать больше объектов рядом')\n",
        1,
    )

new_methods = r'''    def _toggle_nearby_show_all(self):
        """Переключает краткий и подробный режим списка объектов рядом."""
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
            self.nearby_text.setHtml(
                "<p style='color:#64748b;background:#ffffff;'>Выберите объект на карте, чтобы увидеть инфраструктуру рядом.</p>"
            )
            return

        if "_error" in self.nearby_places:
            if hasattr(self, "nearby_more_btn"):
                self.nearby_more_btn.setVisible(False)
            self.nearby_text.setHtml(
                f"<p style='color:#dc2626;background:#ffffff;'>{self.nearby_places['_error']}</p>"
            )
            return

        show_all = getattr(self, "nearby_show_all", False)
        per_category_limit = 12 if show_all else 5

        categories = [
            (cat, items)
            for cat, items in self.nearby_places.items()
            if not str(cat).startswith("_") and isinstance(items, list) and items
        ]

        total = sum(len(items) for _, items in categories)
        has_more = any(len(items) > 5 for _, items in categories)

        if hasattr(self, "nearby_more_btn"):
            self.nearby_more_btn.setVisible(has_more)
            self.nearby_more_btn.setText(
                "Свернуть список" if show_all else "Показать больше объектов рядом"
            )

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
            "Банки и банкоматы": "🏦",
            "Социальные учреждения / детские дома": "🏠",
            "Другие объекты": "📌",
        }

        # Ближайшие объекты по всем категориям
        all_items = []
        for cat, items in categories:
            for item in items:
                item_copy = dict(item)
                item_copy["_cat"] = cat
                all_items.append(item_copy)
        all_items = sorted(all_items, key=lambda x: x.get("distance", 999999))
        nearest = all_items[:8]

        html = [
            "<div style='font-family:Segoe UI,sans-serif;color:#111827;background:#ffffff;font-size:12px;'>",
            "<style>",
            ".near-card{border:1px solid #e2e8f0;border-radius:12px;padding:9px;margin:8px 0;background:#f8fafc;}",
            ".near-item{border-left:3px solid #1976d2;margin:7px 0;padding:7px 8px;background:#ffffff;border-radius:8px;}",
            ".near-name{font-weight:700;color:#0f172a;font-size:12px;}",
            ".near-meta{color:#475569;font-size:11px;margin-top:2px;}",
            ".near-warn{color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:5px;margin-top:5px;}",
            "</style>",
            "<h3 style='color:#1a237e;margin:4px 0 8px;'>📍 Объекты рядом</h3>",
        ]

        if nearest:
            html.append("<div class='near-card'><b>🚶 Ближайшие важные объекты</b>")
            for item in nearest:
                cat = item.get("_cat", "")
                icon = icons.get(cat, "📌")
                name = item.get("name", "Без названия")
                dist = item.get("distance", "—")
                typ = item.get("type", "объект")
                address = item.get("address", "")
                warning = item.get("warning", "")

                html.append("<div class='near-item'>")
                html.append(f"<div class='near-name'>{icon} {name}</div>")
                html.append(f"<div class='near-meta'>{cat} · {typ} · <b>{dist} м</b></div>")
                if address:
                    html.append(f"<div class='near-meta'>Адрес: {address}</div>")
                if warning:
                    html.append(f"<div class='near-warn'>⚠️ {warning}</div>")
                html.append("</div>")
            html.append("</div>")

        for cat, items in categories:
            icon = icons.get(cat, "📌")
            shown = items[:per_category_limit]
            html.append(
                f"<div class='near-card'><b>{icon} {cat}</b> "
                f"<span style='color:#64748b'>({len(items)} шт.)</span>"
            )

            for item in shown:
                name = item.get("name", "Без названия")
                dist = item.get("distance", "—")
                typ = item.get("type", "объект")
                address = item.get("address", "")
                warning = item.get("warning", "")

                html.append("<div class='near-item'>")
                html.append(f"<div class='near-name'>{name}</div>")
                html.append(f"<div class='near-meta'>Тип: {typ} · Расстояние: <b>{dist} м</b></div>")
                if address:
                    html.append(f"<div class='near-meta'>Адрес: {address}</div>")
                if warning:
                    html.append(f"<div class='near-warn'>⚠️ {warning}</div>")
                html.append("</div>")

            html.append("</div>")

        html.append("</div>")
        self.nearby_text.setHtml("".join(html))

'''

# Replace from toggle if exists, otherwise just update panel
if "    def _toggle_nearby_show_all(self):" in s:
    pattern = r"    def _toggle_nearby_show_all\(self\):[\s\S]*?(?=    def _update_stats_panel)"
    s2, count = re.subn(pattern, new_methods, s, count=1)
else:
    pattern = r"    def _update_nearby_panel\(self\):[\s\S]*?(?=    def _update_stats_panel)"
    s2, count = re.subn(pattern, new_methods, s, count=1)

if count == 0:
    raise SystemExit("ERROR: Could not find nearby panel methods in main.py")

main_path.write_text(s2, encoding="utf-8")
print("OK: main.py updated")
print("Now run: python main.py")
