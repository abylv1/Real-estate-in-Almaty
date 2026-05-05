# -*- coding: utf-8 -*-
"""
Final UTF-8 fix for the Almaty real estate app.
Run from project root:
    python fix_nearby_final_utf8.py
It fixes:
- mojibake/???? text in nearby places UI;
- wrong OSM classification such as pitch/ATM appearing as child homes;
- too much noisy OSM data;
- better detailed nearby places panel with show-more button.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path.cwd()


def backup(path: Path) -> None:
    if path.exists():
        b = path.with_suffix(path.suffix + ".backup_final_nearby_utf8")
        if not b.exists():
            b.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")


def patch_geo_utils() -> None:
    path = ROOT / "src" / "geo_utils.py"
    text = path.read_text(encoding="utf-8", errors="replace")
    backup(path)

    new_code = r'''
# ============================================================
# Улучшенный поиск объектов рядом через Overpass API
# ============================================================

def _tag(tags: dict, key: str, default: str = "") -> str:
    """Безопасно получает OSM-тег."""
    value = tags.get(key, default)
    return "" if value is None else str(value)


def _name_from_tags(tags: dict) -> str:
    """Возвращает лучшее доступное название объекта."""
    return (
        _tag(tags, "name:ru") or
        _tag(tags, "name") or
        _tag(tags, "official_name:ru") or
        _tag(tags, "official_name") or
        _tag(tags, "brand:ru") or
        _tag(tags, "brand") or
        "Без названия"
    )


def _address_from_tags(tags: dict) -> str:
    """Собирает адрес из OSM-тегов."""
    street = _tag(tags, "addr:street")
    house = _tag(tags, "addr:housenumber")
    micro = _tag(tags, "addr:subdistrict") or _tag(tags, "addr:district")
    city = _tag(tags, "addr:city")

    main = ", ".join([x for x in [street, house] if x])
    extra = ", ".join([x for x in [micro, city] if x])

    if main and extra:
        return f"{main} ({extra})"
    if main:
        return main
    if extra:
        return extra
    return ""


def _human_type(tags: dict) -> str:
    """Человеческое описание типа объекта."""
    amenity = _tag(tags, "amenity")
    shop = _tag(tags, "shop")
    leisure = _tag(tags, "leisure")
    tourism = _tag(tags, "tourism")
    highway = _tag(tags, "highway")
    public_transport = _tag(tags, "public_transport")
    railway = _tag(tags, "railway")
    social = _tag(tags, "social_facility")
    healthcare = _tag(tags, "healthcare")
    cuisine = _tag(tags, "cuisine")

    mapping = {
        "school": "школа / образовательное учреждение",
        "kindergarten": "детский сад",
        "university": "университет",
        "college": "колледж",
        "hospital": "больница",
        "clinic": "клиника",
        "doctors": "медицинский центр / врачи",
        "pharmacy": "аптека",
        "restaurant": "ресторан",
        "cafe": "кафе",
        "fast_food": "фастфуд",
        "food_court": "фудкорт",
        "theatre": "театр",
        "cinema": "кинотеатр",
        "bank": "банк",
        "atm": "банкомат",
        "social_facility": "социальное учреждение",
        "supermarket": "супермаркет",
        "convenience": "магазин у дома",
        "grocery": "продуктовый магазин",
        "bakery": "пекарня",
        "mall": "торговый центр",
        "department_store": "универмаг / магазин",
        "park": "парк",
        "sports_centre": "спортцентр",
        "fitness_centre": "фитнес-клуб",
        "stadium": "стадион",
        "museum": "музей",
        "attraction": "достопримечательность",
        "bus_stop": "остановка автобуса",
        "station": "станция",
        "subway_entrance": "вход в метро",
        "group_home": "детский дом / учреждение проживания",
        "assisted_living": "социальное учреждение",
        "outreach": "социальная служба",
    }

    raw = amenity or shop or leisure or tourism or highway or public_transport or railway or healthcare or social
    base = mapping.get(raw, raw or "объект инфраструктуры")
    if cuisine and amenity in {"restaurant", "cafe", "fast_food", "food_court"}:
        return f"{base}, кухня: {cuisine}"
    return base


def _classify_place(tags: dict, name: str) -> tuple[str, str]:
    """Возвращает категорию и предупреждение."""
    name_l = (name or "").lower()
    amenity = _tag(tags, "amenity")
    shop = _tag(tags, "shop")
    leisure = _tag(tags, "leisure")
    tourism = _tag(tags, "tourism")
    highway = _tag(tags, "highway")
    public_transport = _tag(tags, "public_transport")
    railway = _tag(tags, "railway")
    social = _tag(tags, "social_facility")
    station = _tag(tags, "station")
    healthcare = _tag(tags, "healthcare")

    social_keywords = [
        "детский дом", "дом ребенка", "дом ребёнка", "orphan", "orphanage",
        "интернат", "центр адаптации", "кризисный центр", "социальн"
    ]

    if amenity == "social_facility" or social or any(k in name_l for k in social_keywords):
        return "Социальные учреждения / детские дома", (
            "Это не обычная школа: по названию или OSM-тегам объект похож на социальное учреждение, "
            "детский дом, интернат или похожую организацию."
        )

    if amenity == "school":
        warning = ""
        if any(k in name_l for k in ["спец", "коррекц", "интернат", "детский дом"]):
            warning = "Проверьте тип: по названию это может быть не обычная общеобразовательная школа."
        return "Школы", warning

    if amenity == "kindergarten":
        return "Детские сады", ""
    if amenity in {"university", "college"}:
        return "Университеты / колледжи", ""
    if amenity in {"hospital", "clinic", "doctors"} or healthcare:
        return "Медицина", ""
    if amenity == "pharmacy":
        return "Аптеки", ""
    if amenity in {"restaurant", "cafe", "fast_food", "food_court"}:
        return "Кафе и рестораны", ""
    if amenity in {"theatre", "cinema"} or tourism in {"museum", "attraction"}:
        return "Культура и досуг", ""
    if amenity in {"bank", "atm"}:
        return "Банки и банкоматы", ""

    if shop in {"mall", "department_store"}:
        return "Торговые центры / рынки", ""
    if shop in {"supermarket", "convenience", "grocery", "greengrocer", "bakery", "butcher", "deli"}:
        return "Магазины и продукты", ""

    if highway == "bus_stop" or public_transport in {"platform", "station"}:
        return "Остановки транспорта", ""
    if railway in {"station", "subway_entrance"} or station == "subway":
        return "Метро / ж/д станции", ""

    if leisure == "park":
        return "Парки и зелёные зоны", ""
    if leisure in {"sports_centre", "fitness_centre", "stadium"}:
        return "Спорт и фитнес", ""

    return "Другие объекты", ""


def _importance_score(category: str, distance: float, name: str) -> float:
    weight = {
        "Метро / ж/д станции": 0.55,
        "Остановки транспорта": 0.70,
        "Магазины и продукты": 0.85,
        "Аптеки": 0.90,
        "Медицина": 0.95,
        "Школы": 1.00,
        "Детские сады": 1.05,
        "Парки и зелёные зоны": 1.10,
        "Торговые центры / рынки": 1.15,
        "Университеты / колледжи": 1.20,
        "Кафе и рестораны": 1.25,
        "Культура и досуг": 1.30,
        "Спорт и фитнес": 1.35,
        "Банки и банкоматы": 1.45,
        "Социальные учреждения / детские дома": 1.60,
        "Другие объекты": 2.00,
    }.get(category, 2.00)
    no_name_penalty = 200 if not name or name == "Без названия" else 0
    return distance * weight + no_name_penalty


def _should_skip_place(tags: dict, name: str) -> bool:
    """Убирает мусорные и технические объекты, которые забивают список."""
    leisure = _tag(tags, "leisure")
    public_transport = _tag(tags, "public_transport")
    amenity = _tag(tags, "amenity")
    name = name or ""

    # Безымянные спортивные площадки создают десятки однотипных точек.
    if leisure == "pitch" and name == "Без названия":
        return True

    # stop_position часто дублирует bus_stop и засоряет список.
    if public_transport == "stop_position":
        return True

    # Безымянные банкоматы лучше не показывать в подробной инфраструктуре.
    if amenity == "atm" and name == "Без названия":
        return True

    return False


def _dedupe_items(items: list[dict]) -> list[dict]:
    """Удаляет явные дубли по названию/категории на близком расстоянии."""
    result = []
    seen = set()
    for item in sorted(items, key=lambda x: x.get("distance", 999999)):
        name_key = (item.get("name") or "").lower().strip()
        cat = item.get("category", "")
        dist_bucket = int(item.get("distance", 0) // 100)
        key = (cat, name_key, dist_bucket)
        if name_key and name_key != "без названия" and key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def get_nearby_places(lat: float, lon: float, radius: int = NEARBY_RADIUS) -> dict:
    """
    Подробный поиск инфраструктуры рядом через OpenStreetMap / Overpass API.
    Возвращает категории с объектами, расстоянием, типом, адресом и OSM-тегами.
    """
    radius = max(int(radius or NEARBY_RADIUS), 1200)

    cache = _load_osm_cache()
    key = f"nearby_v5_clean_{_cache_key(lat, lon)}_{radius}"
    if key in cache:
        return cache[key]

    # ВАЖНО: intentionally do NOT request leisure=pitch and public_transport=stop_position,
    # because they create hundreds of low-value duplicated objects.
    selectors = [
        '["amenity"~"^(school|kindergarten|university|college|hospital|clinic|doctors|pharmacy|restaurant|cafe|fast_food|food_court|theatre|cinema|bank|atm|social_facility|marketplace)$"]',
        '["shop"~"^(supermarket|convenience|grocery|greengrocer|bakery|butcher|deli|mall|department_store)$"]',
        '["leisure"~"^(park|sports_centre|fitness_centre|stadium)$"]',
        '["tourism"~"^(museum|attraction)$"]',
        '["highway"="bus_stop"]',
        '["public_transport"~"^(platform|station)$"]',
        '["railway"~"^(station|subway_entrance)$"]',
        '["station"="subway"]',
        '["healthcare"]',
        '["social_facility"]',
    ]

    union_parts = []
    for selector in selectors:
        union_parts.append(f'node{selector}(around:{radius},{lat},{lon});')
        union_parts.append(f'way{selector}(around:{radius},{lat},{lon});')
        union_parts.append(f'relation{selector}(around:{radius},{lat},{lon});')

    query = f"""
[out:json][timeout:35];
(
  {''.join(union_parts)}
);
out center tags;
"""

    raw_items: list[dict] = []
    seen_osm = set()

    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=max(REQUEST_TIMEOUT + 25, 35),
            headers={"User-Agent": "AlmatyRealEstateApp/1.0 (student project)"},
        )
        resp.raise_for_status()
        data = resp.json()

        for element in data.get("elements", []):
            tags = element.get("tags", {}) or {}
            osm_type = element.get("type", "node")
            osm_id = element.get("id")
            if osm_id is None:
                continue

            uniq = f"{osm_type}/{osm_id}"
            if uniq in seen_osm:
                continue
            seen_osm.add(uniq)

            elat = element.get("lat") or element.get("center", {}).get("lat")
            elon = element.get("lon") or element.get("center", {}).get("lon")
            if elat is None or elon is None:
                continue

            name = _name_from_tags(tags)
            if _should_skip_place(tags, name):
                continue

            dist = round(haversine_distance(lat, lon, float(elat), float(elon)))
            category, warning = _classify_place(tags, name)
            human_type = _human_type(tags)
            address = _address_from_tags(tags)

            item = {
                "name": name,
                "distance": int(dist),
                "type": human_type,
                "category": category,
                "address": address,
                "warning": warning,
                "lat": float(elat),
                "lon": float(elon),
                "osm_type": osm_type,
                "osm_id": int(osm_id),
                "osm_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                "tags": {
                    k: v for k, v in tags.items()
                    if k in (
                        "amenity", "shop", "leisure", "tourism", "highway",
                        "public_transport", "railway", "station", "healthcare",
                        "social_facility", "name", "name:ru", "brand",
                        "addr:street", "addr:housenumber", "opening_hours",
                        "operator", "website", "phone", "cuisine"
                    )
                },
            }
            item["importance_score"] = _importance_score(category, dist, name)
            raw_items.append(item)

        raw_items = _dedupe_items(raw_items)

        grouped: dict[str, list[dict]] = {}
        for item in raw_items:
            grouped.setdefault(item["category"], []).append(item)

        for cat in list(grouped.keys()):
            grouped[cat] = sorted(
                grouped[cat],
                key=lambda x: (x.get("importance_score", 999999), x.get("distance", 999999))
            )

        ordered = {}
        for cat, items in sorted(
            grouped.items(),
            key=lambda kv: min([i.get("importance_score", 999999) for i in kv[1]]) if kv[1] else 999999
        ):
            ordered[cat] = items

        ordered["_total"] = sum(len(v) for v in ordered.values() if isinstance(v, list))
        ordered["_radius"] = radius
        ordered["_source"] = "OpenStreetMap / Overpass API"
        ordered["_note"] = (
            "Категории определяются по OSM-тегам и названию. "
            "Безымянные спортивные площадки, технические stop_position и безымянные банкоматы скрыты, "
            "чтобы список был полезнее."
        )

        cache[key] = ordered
        _save_osm_cache(cache)
        return ordered

    except requests.RequestException:
        return {
            "_error": "Данные об объектах рядом недоступны. Проверьте интернет или доступ к Overpass API.",
            "_total": 0,
            "_radius": radius,
        }
    except Exception as e:
        return {
            "_error": f"Ошибка обработки объектов рядом: {str(e)}",
            "_total": 0,
            "_radius": radius,
        }
'''

    idx = text.find("def get_nearby_places(")
    if idx == -1:
        raise RuntimeError("Не найден def get_nearby_places в src/geo_utils.py")
    text = text[:idx] + new_code
    path.write_text(text, encoding="utf-8")
    print("OK: src/geo_utils.py updated")


def patch_main() -> None:
    path = ROOT / "main.py"
    text = path.read_text(encoding="utf-8", errors="replace")
    backup(path)

    # Ensure state exists
    if "self.nearby_show_all" not in text:
        text = text.replace(
            "        self.nearby_places = {}\n",
            "        self.nearby_places = {}\n        self.nearby_show_all = False\n",
            1,
        )

    # Add button if missing
    if "self.nearby_more_btn" not in text:
        text = text.replace(
            "        self.nearby_text.setHtml(\"<p style='color:#888'>Будут загружены при выборе объекта</p>\")\n        layout.addWidget(self.nearby_text)\n",
            "        self.nearby_text.setHtml(\"<p style='color:#64748b'>Будут загружены при выборе объекта</p>\")\n        layout.addWidget(self.nearby_text)\n\n"
            "        self.nearby_more_btn = QPushButton(\"Показать все объекты рядом\")\n"
            "        self.nearby_more_btn.setObjectName(\"resetBtn\")\n"
            "        self.nearby_more_btn.clicked.connect(self._toggle_nearby_show_all)\n"
            "        self.nearby_more_btn.setVisible(False)\n"
            "        layout.addWidget(self.nearby_more_btn)\n",
        )

    # Reset on select
    text = text.replace(
        "        self.selected_prop = get_property_dict(row)\n        self.nearby_places = {}\n",
        "        self.selected_prop = get_property_dict(row)\n        self.nearby_places = {}\n        self.nearby_show_all = False\n        if hasattr(self, 'nearby_more_btn'):\n            self.nearby_more_btn.setVisible(False)\n            self.nearby_more_btn.setText('Показать все объекты рядом')\n",
    )

    toggle_method = r'''
    def _toggle_nearby_show_all(self):
        """Переключает краткий и полный список объектов рядом."""
        self.nearby_show_all = not getattr(self, "nearby_show_all", False)
        if hasattr(self, "nearby_more_btn"):
            self.nearby_more_btn.setText(
                "Свернуть список объектов рядом" if self.nearby_show_all else "Показать все объекты рядом"
            )
        self._update_nearby_panel()

'''
    if "def _toggle_nearby_show_all" not in text:
        text = text.replace("    def _update_nearby_panel(self):", toggle_method + "    def _update_nearby_panel(self):", 1)

    new_method = r'''    def _update_nearby_panel(self):
        """Подробный блок объектов рядом без проблем с кодировкой."""
        if not self.nearby_places:
            if hasattr(self, "nearby_more_btn"):
                self.nearby_more_btn.setVisible(False)
            self.nearby_text.setHtml("<p style='color:#64748b'>Нет данных об объектах рядом.</p>")
            return

        if "_error" in self.nearby_places:
            if hasattr(self, "nearby_more_btn"):
                self.nearby_more_btn.setVisible(False)
            self.nearby_text.setHtml(
                f"<p style='color:#dc2626'>{self.nearby_places['_error']}</p>"
            )
            return

        radius = self.nearby_places.get("_radius", 1200)
        total = self.nearby_places.get("_total")
        if total is None:
            total = sum(len(items) for cat, items in self.nearby_places.items() if not cat.startswith("_") and isinstance(items, list))

        show_all = getattr(self, "nearby_show_all", False)
        per_category_limit = 9999 if show_all else 5

        if hasattr(self, "nearby_more_btn"):
            self.nearby_more_btn.setVisible(total > 12)
            self.nearby_more_btn.setText(
                "Свернуть список объектов рядом" if show_all else f"Показать все объекты рядом ({total})"
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

        all_items = []
        for cat, items in self.nearby_places.items():
            if cat.startswith("_") or not isinstance(items, list):
                continue
            for item in items:
                copied = dict(item)
                copied["_cat"] = cat
                all_items.append(copied)
        all_items = sorted(all_items, key=lambda x: x.get("distance", 999999))

        html = [
            "<div style='font-family:Segoe UI,Arial,sans-serif;color:#111827;background:#ffffff;font-size:12px;'>",
            "<style>",
            ".near-summary{background:#eef2ff;border:1px solid #c7d2fe;border-radius:12px;padding:9px;margin-bottom:8px;}",
            ".near-card{border:1px solid #e2e8f0;border-radius:12px;padding:9px;margin:8px 0;background:#f8fafc;}",
            ".near-item{border-left:3px solid #1976d2;margin:7px 0;padding:7px 8px;background:#ffffff;border-radius:8px;}",
            ".near-name{font-weight:700;color:#0f172a;font-size:12px;}",
            ".near-meta{color:#475569;font-size:11px;margin-top:2px;}",
            ".near-warn{color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:5px;margin-top:5px;}",
            ".near-tag{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:10px;padding:2px 6px;margin:2px;font-size:10px;}",
            "</style>",
            "<h3 style='color:#1a237e;margin:4px 0 8px;'>📍 Объекты рядом</h3>",
            "<div class='near-summary'>",
            f"<b>Найдено объектов:</b> {total}<br>",
            f"<b>Радиус поиска:</b> примерно {radius} м<br>",
            "<b>Источник:</b> OpenStreetMap / Overpass API<br>",
            "<span style='color:#64748b'>Сначала показаны ближайшие и самые полезные объекты. Мусорные дубли вроде stop_position и безымянных площадок скрываются.</span>",
            "</div>",
        ]

        nearest = all_items[:8]
        if nearest:
            html.append("<div class='near-card'><b>🚶 Самые ближайшие объекты</b>")
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
                html.append(f"<div class='near-meta'>Категория: <b>{cat}</b> · Тип: {typ} · Расстояние: <b>{dist} м</b></div>")
                if address:
                    html.append(f"<div class='near-meta'>Адрес: {address}</div>")
                if warning:
                    html.append(f"<div class='near-warn'>⚠️ {warning}</div>")
                html.append("</div>")
            html.append("</div>")

        for cat, items in self.nearby_places.items():
            if cat.startswith("_") or not isinstance(items, list) or not items:
                continue
            icon = icons.get(cat, "📌")
            html.append(f"<div class='near-card'><b>{icon} {cat}</b> <span style='color:#64748b'>({len(items)} шт.)</span>")
            for item in items[:per_category_limit]:
                name = item.get("name", "Без названия")
                dist = item.get("distance", "—")
                typ = item.get("type", "объект")
                address = item.get("address", "")
                warning = item.get("warning", "")
                tags = item.get("tags", {}) or {}
                html.append("<div class='near-item'>")
                html.append(f"<div class='near-name'>{name}</div>")
                html.append(f"<div class='near-meta'>Тип: {typ} · Расстояние: <b>{dist} м</b></div>")
                if address:
                    html.append(f"<div class='near-meta'>Адрес: {address}</div>")
                if warning:
                    html.append(f"<div class='near-warn'>⚠️ {warning}</div>")
                tag_parts = []
                for k in ["amenity", "shop", "leisure", "tourism", "highway", "public_transport", "railway", "social_facility", "opening_hours", "operator"]:
                    if tags.get(k):
                        tag_parts.append(f"{k}: {tags[k]}")
                if tag_parts:
                    html.append("<div class='near-meta'>OSM-теги: " + " ".join(f"<span class='near-tag'>{t}</span>" for t in tag_parts[:6]) + "</div>")
                html.append("</div>")
            if not show_all and len(items) > per_category_limit:
                html.append(f"<p style='color:#64748b;margin-left:8px;'>Ещё скрыто: {len(items)-per_category_limit}. Нажми кнопку «Показать все объекты рядом».</p>")
            html.append("</div>")

        html.append("<p style='color:#64748b;font-size:11px;margin-top:8px;'>Важно: данные берутся из OpenStreetMap. Если объект неправильно размечен в OSM, программа показывает предупреждение и уточняет категорию по названию.</p>")
        html.append("</div>")
        self.nearby_text.setHtml("".join(html))

'''

    pattern = r"    def _update_nearby_panel\(self\):[\s\S]*?(?=    def _update_stats_panel)"
    text2, count = re.subn(pattern, new_method, text, count=1)
    if count == 0:
        raise RuntimeError("Не найден метод _update_nearby_panel в main.py")
    path.write_text(text2, encoding="utf-8")
    print("OK: main.py updated")


def clear_cache() -> None:
    cache = ROOT / "cache" / "osm_cache.json"
    cache.parent.mkdir(exist_ok=True)
    cache.write_text("{}", encoding="utf-8")
    print("OK: cache/osm_cache.json cleared")


if __name__ == "__main__":
    patch_geo_utils()
    patch_main()
    clear_cache()
    print("DONE. Now run: python main.py")
