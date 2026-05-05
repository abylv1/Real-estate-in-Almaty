# -*- coding: utf-8 -*-
"""
Fixes the Nearby Places block for the Almaty real estate app.
Run from the project root:
    python fix_nearby_utf8.py
"""
from pathlib import Path
import re

ROOT = Path.cwd()

geo_path = ROOT / "src" / "geo_utils.py"
main_path = ROOT / "main.py"
cache_path = ROOT / "cache" / "osm_cache.json"

if not geo_path.exists() or not main_path.exists():
    raise SystemExit("Запусти этот файл из корня проекта, где есть main.py и папка src/")

# Backups
for p in [geo_path, main_path]:
    backup = p.with_suffix(p.suffix + ".backup_nearby_utf8")
    if not backup.exists():
        backup.write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

# ============================================================
# geo_utils.py
# ============================================================
geo = geo_path.read_text(encoding="utf-8", errors="replace")

new_geo_tail = r'''
# ============================================================
# Улучшенный поиск объектов рядом через Overpass API
# ============================================================

def _tag(tags: dict, key: str, default: str = "") -> str:
    """Безопасно получает OSM-тег."""
    val = tags.get(key, default)
    return "" if val is None else str(val)


def _name_from_tags(tags: dict) -> str:
    """Достаёт наиболее читаемое название объекта."""
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
    """Собирает адрес из OSM-тегов, если он есть."""
    street = _tag(tags, "addr:street")
    house = _tag(tags, "addr:housenumber")
    district = _tag(tags, "addr:district")
    city = _tag(tags, "addr:city")

    parts = []
    if street:
        parts.append(street)
    if house:
        parts.append(house)

    main = ", ".join(parts)
    extra = ", ".join([x for x in [district, city] if x])

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
    healthcare = _tag(tags, "healthcare")
    social = _tag(tags, "social_facility")
    cuisine = _tag(tags, "cuisine")

    mapping = {
        "school": "школа / образовательное учреждение",
        "kindergarten": "детский сад",
        "university": "университет",
        "college": "колледж",
        "hospital": "больница",
        "clinic": "клиника",
        "doctors": "медицинский кабинет",
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
        "greengrocer": "овощной магазин",
        "bakery": "пекарня",
        "butcher": "мясной магазин",
        "deli": "гастроном",
        "mall": "торговый центр",
        "department_store": "универмаг",
        "park": "парк",
        "sports_centre": "спортцентр",
        "fitness_centre": "фитнес-центр",
        "pitch": "спортивная площадка",
        "stadium": "стадион",
        "museum": "музей",
        "attraction": "достопримечательность",
        "bus_stop": "остановка автобуса",
        "platform": "остановочная платформа",
        "stop_position": "точка остановки транспорта",
        "station": "станция",
        "subway_entrance": "вход в метро",
        "group_home": "детский дом / учреждение проживания",
        "assisted_living": "социальное учреждение",
        "outreach": "социальная служба",
    }

    base = (
        mapping.get(amenity) or mapping.get(shop) or mapping.get(leisure) or
        mapping.get(tourism) or mapping.get(highway) or mapping.get(public_transport) or
        mapping.get(railway) or mapping.get(healthcare) or mapping.get(social) or
        amenity or shop or leisure or tourism or highway or public_transport or railway or healthcare or social or "объект"
    )

    if cuisine and amenity in ("restaurant", "cafe", "fast_food", "food_court"):
        return f"{base}, кухня: {cuisine}"
    return base


def _classify_place(tags: dict, name: str) -> tuple[str, str]:
    """
    Возвращает (категория, предупреждение).
    Важно: детский дом, интернат, соц. учреждение НЕ показываем как обычную школу.
    Спортивные площадки pitch НЕ показываем как социальные учреждения.
    """
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
        "интернат", "центр адаптации", "кризисный центр"
    ]
    if any(k in name_l for k in social_keywords) or amenity == "social_facility" or bool(social):
        return "Социальные учреждения / детские дома", (
            "Это не обычная школа: по названию или OSM-тегам объект похож на детский дом, "
            "интернат или социальное учреждение. Проверьте вручную при важном решении."
        )

    if amenity == "school":
        warning = ""
        if any(k in name_l for k in ["спец", "коррекц", "интернат", "детский дом"]):
            warning = "Проверьте тип: по названию это может быть не обычная общеобразовательная школа."
        return "Школы", warning

    if amenity == "kindergarten":
        return "Детские сады", ""
    if amenity in ("university", "college"):
        return "Университеты / колледжи", ""

    if amenity in ("hospital", "clinic", "doctors") or healthcare:
        return "Медицина", ""
    if amenity == "pharmacy":
        return "Аптеки", ""

    if shop in ("mall", "department_store") or amenity == "marketplace":
        return "Торговые центры / рынки", ""
    if shop in ("supermarket", "convenience", "grocery", "greengrocer", "bakery", "butcher", "deli"):
        return "Магазины и продукты", ""

    if highway == "bus_stop" or public_transport in ("platform", "stop_position", "station"):
        return "Остановки транспорта", ""
    if railway in ("station", "subway_entrance") or station == "subway":
        return "Метро / ж/д станции", ""

    if leisure == "park":
        return "Парки и зелёные зоны", ""
    if leisure in ("sports_centre", "fitness_centre", "pitch", "stadium"):
        return "Спорт и площадки", ""

    if amenity in ("restaurant", "cafe", "fast_food", "food_court"):
        return "Кафе и рестораны", ""
    if amenity in ("theatre", "cinema") or tourism in ("museum", "attraction"):
        return "Культура и досуг", ""
    if amenity in ("bank", "atm"):
        return "Банки и банкоматы", ""

    return "Другие объекты", ""


def _importance_score(category: str, distance: float, name: str) -> float:
    """Оценка важности для сортировки."""
    category_weight = {
        "Остановки транспорта": 0.80,
        "Метро / ж/д станции": 0.60,
        "Магазины и продукты": 0.90,
        "Аптеки": 0.95,
        "Медицина": 1.00,
        "Школы": 1.05,
        "Детские сады": 1.10,
        "Парки и зелёные зоны": 1.15,
        "Торговые центры / рынки": 1.20,
        "Университеты / колледжи": 1.25,
        "Кафе и рестораны": 1.30,
        "Спорт и площадки": 1.35,
        "Культура и досуг": 1.40,
        "Банки и банкоматы": 1.45,
        "Социальные учреждения / детские дома": 1.70,
        "Другие объекты": 2.00,
    }.get(category, 2.00)

    no_name_penalty = 120 if not name or name == "Без названия" else 0
    return distance * category_weight + no_name_penalty


def _dedupe_items(items: list[dict]) -> list[dict]:
    """Убирает дубли, например один и тот же фитнес как node и way."""
    result = []
    for item in sorted(items, key=lambda x: (x.get("distance", 999999), x.get("name", ""))):
        name = (item.get("name") or "").strip().lower()
        cat = item.get("category", "")
        dist = item.get("distance", 999999)
        duplicate = False
        for old in result:
            old_name = (old.get("name") or "").strip().lower()
            old_cat = old.get("category", "")
            old_dist = old.get("distance", 999999)
            if name and name != "без названия" and name == old_name and cat == old_cat and abs(dist - old_dist) <= 35:
                duplicate = True
                break
        if not duplicate:
            result.append(item)
    return result


def get_nearby_places(lat: float, lon: float, radius: int = NEARBY_RADIUS) -> dict:
    """
    Подробный поиск важных объектов рядом через OpenStreetMap Overpass API.
    """
    radius = max(int(radius or NEARBY_RADIUS), 1200)

    cache = _load_osm_cache()
    key = f"nearby_v4_utf8_{_cache_key(lat, lon)}_{radius}"
    if key in cache:
        return cache[key]

    selectors = [
        '["amenity"~"^(school|kindergarten|university|college|hospital|clinic|doctors|pharmacy|restaurant|cafe|fast_food|food_court|theatre|cinema|bank|atm|social_facility|marketplace)$"]',
        '["shop"~"^(supermarket|convenience|grocery|greengrocer|bakery|butcher|deli|mall|department_store)$"]',
        '["leisure"~"^(park|sports_centre|fitness_centre|pitch|stadium)$"]',
        '["tourism"~"^(museum|attraction)$"]',
        '["highway"="bus_stop"]',
        '["public_transport"~"^(platform|stop_position|station)$"]',
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

    results: dict[str, list] = {}
    seen = set()

    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=max(REQUEST_TIMEOUT + 20, 30),
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
            if uniq in seen:
                continue
            seen.add(uniq)

            elat = element.get("lat") or element.get("center", {}).get("lat")
            elon = element.get("lon") or element.get("center", {}).get("lon")
            if elat is None or elon is None:
                continue

            dist = int(round(haversine_distance(lat, lon, elat, elon)))
            name = _name_from_tags(tags)
            category, warning = _classify_place(tags, name)
            human_type = _human_type(tags)
            address = _address_from_tags(tags)

            item = {
                "name": name,
                "distance": dist,
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
                "importance_score": _importance_score(category, dist, name),
            }
            results.setdefault(category, []).append(item)

        ordered = {}
        for cat, items in results.items():
            cleaned = _dedupe_items(items)
            ordered[cat] = sorted(cleaned, key=lambda x: (x.get("importance_score", 999999), x.get("distance", 999999)))

        ordered = dict(sorted(
            ordered.items(),
            key=lambda kv: min([i.get("importance_score", 999999) for i in kv[1]]) if kv[1] else 999999
        ))

        ordered["_total"] = sum(len(v) for v in ordered.values())
        ordered["_radius"] = radius
        ordered["_source"] = "OpenStreetMap / Overpass API"
        ordered["_note"] = (
            "Категории определяются по OSM-тегам и названию. "
            "Данные OpenStreetMap могут быть неполными или неточными, поэтому важные объекты лучше проверять вручную."
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

# Replace from first helper/get_nearby block after Haversine to EOF
candidates = [i for i in [geo.find("\ndef _tag("), geo.find("\ndef get_nearby_places(")] if i != -1]
if not candidates:
    raise SystemExit("Не найден def get_nearby_places в src/geo_utils.py")
start = min(candidates) + 1
geo = geo[:start] + new_geo_tail.lstrip()
geo_path.write_text(geo, encoding="utf-8")
print("OK: src/geo_utils.py обновлён")

# ============================================================
# main.py
# ============================================================
main = main_path.read_text(encoding="utf-8", errors="replace")

# Add state if missing
if "self.nearby_show_all" not in main:
    main = main.replace("        self.nearby_places = {}\n", "        self.nearby_places = {}\n        self.nearby_show_all = False\n", 1)

# Add button if missing
if "self.nearby_more_btn" not in main:
    main = main.replace(
        "        self.nearby_text.setHtml(\"<p style='color:#888'>Будут загружены при выборе объекта</p>\")\n        layout.addWidget(self.nearby_text)\n",
        "        self.nearby_text.setHtml(\"<p style='color:#888'>Будут загружены при выборе объекта</p>\")\n        layout.addWidget(self.nearby_text)\n\n"
        "        self.nearby_more_btn = QPushButton(\"Показать все объекты рядом\")\n"
        "        self.nearby_more_btn.setObjectName(\"resetBtn\")\n"
        "        self.nearby_more_btn.clicked.connect(self._toggle_nearby_show_all)\n"
        "        self.nearby_more_btn.setVisible(False)\n"
        "        layout.addWidget(self.nearby_more_btn)\n"
    )

# Reset show all when selecting new property
main = main.replace(
    "        self.selected_prop = get_property_dict(row)\n        self.selected_prop[\"district\"] = row.get(\"district\", \"Район не определён точно\")\n",
    "        self.selected_prop = get_property_dict(row)\n        self.selected_prop[\"district\"] = row.get(\"district\", \"Район не определён точно\")\n"
    "        self.nearby_show_all = False\n"
    "        if hasattr(self, 'nearby_more_btn'):\n"
    "            self.nearby_more_btn.setVisible(False)\n"
    "            self.nearby_more_btn.setText('Показать все объекты рядом')\n"
)

# Insert toggle method before _update_nearby_panel
if "def _toggle_nearby_show_all" not in main:
    toggle_method = '''    def _toggle_nearby_show_all(self):
        """Переключает краткий/полный список объектов рядом."""
        self.nearby_show_all = not getattr(self, "nearby_show_all", False)
        if hasattr(self, "nearby_more_btn"):
            self.nearby_more_btn.setText(
                "Свернуть список объектов рядом" if self.nearby_show_all else "Показать все объекты рядом"
            )
        self._update_nearby_panel()

'''
    main = main.replace("    def _update_nearby_panel(self):", toggle_method + "    def _update_nearby_panel(self):", 1)

new_update_nearby = r'''    def _update_nearby_panel(self):
        """Подробный блок объектов рядом: ближайшие + категории + кнопка полного списка."""
        nearby = self.nearby_places

        if not nearby:
            if hasattr(self, "nearby_more_btn"):
                self.nearby_more_btn.setVisible(False)
            self.nearby_text.setHtml("<p style='color:#64748b'>Нет данных об объектах рядом.</p>")
            return

        if "_error" in nearby:
            if hasattr(self, "nearby_more_btn"):
                self.nearby_more_btn.setVisible(False)
            self.nearby_text.setHtml(f"<p style='color:#dc2626'>⚠️ {nearby['_error']}</p>")
            return

        radius = nearby.get("_radius", 1200)
        total = nearby.get("_total")
        if total is None:
            total = sum(len(items) for cat, items in nearby.items() if not cat.startswith("_") and isinstance(items, list))

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
            "Спорт и площадки": "🏟️",
            "Банки и банкоматы": "🏦",
            "Социальные учреждения / детские дома": "🏠",
            "Другие объекты": "📌",
        }

        all_items = []
        for cat, items in nearby.items():
            if cat.startswith("_") or not isinstance(items, list):
                continue
            for item in items:
                item_copy = dict(item)
                item_copy["_cat"] = cat
                all_items.append(item_copy)
        all_items = sorted(all_items, key=lambda x: x.get("distance", 999999))
        nearest = all_items[:10]

        html = [
            "<div style='font-family:Segoe UI,sans-serif;color:#111827;background:#ffffff;font-size:12px;'>",
            "<style>",
            ".near-card{border:1px solid #e2e8f0;border-radius:12px;padding:9px;margin:8px 0;background:#f8fafc;}",
            ".near-item{border-left:3px solid #1976d2;margin:7px 0;padding:7px 8px;background:#ffffff;border-radius:8px;}",
            ".near-name{font-weight:700;color:#0f172a;font-size:12px;}",
            ".near-meta{color:#475569;font-size:11px;margin-top:2px;}",
            ".near-warn{color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:5px;margin-top:5px;}",
            ".near-tag{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:10px;padding:2px 6px;margin:2px;font-size:10px;}",
            ".near-summary{background:#eef2ff;border:1px solid #c7d2fe;border-radius:12px;padding:9px;margin-bottom:8px;}",
            "</style>",
            "<h3 style='color:#1a237e;margin:4px 0 8px;'>📍 Объекты рядом</h3>",
            "<div class='near-summary'>",
            f"<b>Найдено объектов:</b> {total}<br>",
            f"<b>Радиус поиска:</b> примерно {radius} м<br>",
            "<b>Источник:</b> OpenStreetMap / Overpass API<br>",
            "<span style='color:#64748b'>Сначала показаны ближайшие объекты. Категории уточняются по OSM-тегам и названию.</span>",
            "</div>",
        ]

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

        for cat, items in nearby.items():
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
                    if k in tags and tags[k]:
                        tag_parts.append(f"{k}: {tags[k]}")
                if tag_parts:
                    html.append("<div class='near-meta'>OSM-теги: " + " ".join(f"<span class='near-tag'>{t}</span>" for t in tag_parts[:7]) + "</div>")
                html.append("</div>")

            if not show_all and len(items) > per_category_limit:
                html.append(f"<p style='color:#64748b;margin-left:8px;'>Ещё скрыто: {len(items) - per_category_limit}. Нажми кнопку «Показать все объекты рядом» ниже.</p>")
            html.append("</div>")

        html.append("<p style='color:#64748b;font-size:11px;margin-top:8px;'>Важно: данные берутся из OpenStreetMap. Если объект неправильно размечен в OSM, программа показывает предупреждение и уточняет категорию по названию.</p>")
        html.append("</div>")
        self.nearby_text.setHtml("".join(html))

'''

main, count = re.subn(r"    def _update_nearby_panel\(self\):[\s\S]*?(?=    def _update_stats_panel)", new_update_nearby, main, count=1)
if count == 0:
    raise SystemExit("Не найден метод _update_nearby_panel в main.py")

main_path.write_text(main, encoding="utf-8")
print("OK: main.py обновлён")

# Clear old corrupted OSM cache
cache_path.parent.mkdir(exist_ok=True)
cache_path.write_text("{}", encoding="utf-8")
print("OK: cache/osm_cache.json очищен")
print("ГОТОВО. Запусти приложение: python main.py")
