# -*- coding: utf-8 -*-
"""
Clean UI patch for the "Объекты рядом" block.

What it does:
- removes technical summary lines: count, radius, source, OSM explanation;
- removes OSM-tags from UI;
- removes 'Ещё скрыто...' text;
- fixes the 'Показать больше объектов рядом' button;
- keeps detailed, readable nearby-place cards.

Run from the project root:
    python fix_nearby_clean_ui_v2.py
"""

from pathlib import Path
import re

ROOT = Path.cwd()
MAIN = ROOT / "main.py"

if not MAIN.exists():
    raise SystemExit("ERROR: main.py not found. Run this script from the project root folder.")

text = MAIN.read_text(encoding="utf-8", errors="replace")

backup = ROOT / "main.py.backup_clean_nearby_v2"
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

# -------------------------------------------------------------------
# Ensure state variable exists
# -------------------------------------------------------------------
if "self.nearby_show_all" not in text:
    text = text.replace(
        "        self.nearby_places = {}\n",
        "        self.nearby_places = {}\n        self.nearby_show_all = False\n",
        1,
    )

# -------------------------------------------------------------------
# Ensure button exists in property tab
# -------------------------------------------------------------------
if "self.nearby_more_btn" not in text:
    old = (
        "        self.nearby_text.setHtml(\"<p style='color:#888'>Будут загружены при выборе объекта</p>\")\n"
        "        layout.addWidget(self.nearby_text)\n"
    )
    new = (
        "        self.nearby_text.setHtml(\"<p style='color:#888'>Будут загружены при выборе объекта</p>\")\n"
        "        layout.addWidget(self.nearby_text)\n\n"
        "        self.nearby_more_btn = QPushButton(\"Показать больше объектов рядом\")\n"
        "        self.nearby_more_btn.setObjectName(\"resetBtn\")\n"
        "        self.nearby_more_btn.clicked.connect(self._toggle_nearby_show_all)\n"
        "        self.nearby_more_btn.setVisible(False)\n"
        "        layout.addWidget(self.nearby_more_btn)\n"
    )
    if old in text:
        text = text.replace(old, new, 1)
else:
    # Normalize existing button text and connection if the block exists.
    text = re.sub(
        r'self\.nearby_more_btn\s*=\s*QPushButton\([^\n]*\)',
        'self.nearby_more_btn = QPushButton("Показать больше объектов рядом")',
        text,
        count=1,
    )
    if "self.nearby_more_btn.clicked.connect(self._toggle_nearby_show_all)" not in text:
        text = text.replace(
            "        self.nearby_more_btn.setObjectName(\"resetBtn\")\n",
            "        self.nearby_more_btn.setObjectName(\"resetBtn\")\n"
            "        self.nearby_more_btn.clicked.connect(self._toggle_nearby_show_all)\n",
            1,
        )

# -------------------------------------------------------------------
# Reset show_all on new property selection
# -------------------------------------------------------------------
if "self.nearby_show_all = False" not in text[text.find("def _on_property_selected"): text.find("def _start_geo_thread") if "def _start_geo_thread" in text else len(text)]:
    text = text.replace(
        "        self.selected_prop = get_property_dict(row)\n",
        "        self.selected_prop = get_property_dict(row)\n"
        "        self.nearby_show_all = False\n"
        "        if hasattr(self, 'nearby_more_btn'):\n"
        "            self.nearby_more_btn.setVisible(False)\n"
        "            self.nearby_more_btn.setText('Показать больше объектов рядом')\n",
        1,
    )

# -------------------------------------------------------------------
# Toggle method
# -------------------------------------------------------------------
toggle_method = '''    def _toggle_nearby_show_all(self):
        """Переключает краткий и расширенный список объектов рядом."""
        self.nearby_show_all = not getattr(self, "nearby_show_all", False)
        if hasattr(self, "nearby_more_btn"):
            self.nearby_more_btn.setText(
                "Свернуть список" if self.nearby_show_all else "Показать больше объектов рядом"
            )
        self._update_nearby_panel()

'''

if "def _toggle_nearby_show_all" in text:
    text = re.sub(
        r"    def _toggle_nearby_show_all\(self\):[\s\S]*?(?=    def _update_nearby_panel)",
        toggle_method,
        text,
        count=1,
    )
else:
    text = text.replace("    def _update_nearby_panel(self):", toggle_method + "    def _update_nearby_panel(self):", 1)

# -------------------------------------------------------------------
# Clean nearby panel
# -------------------------------------------------------------------
new_update_nearby = r'''    def _update_nearby_panel(self):
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

'''

pattern = r"    def _update_nearby_panel\(self\):[\s\S]*?(?=    def _update_stats_panel)"
text2, count = re.subn(pattern, new_update_nearby, text, count=1)

if count == 0:
    raise SystemExit("ERROR: Could not find _update_nearby_panel block in main.py")

MAIN.write_text(text2, encoding="utf-8")
print("OK: main.py updated")
print("Removed: count/radius/source/OSM-tags/hidden-message")
print("Fixed: nearby more button")
print("Now run: python main.py")
