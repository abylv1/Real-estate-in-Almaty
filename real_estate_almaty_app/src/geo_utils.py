# -*- coding: utf-8 -*-
"""
Геоутилиты: определение района и микрорайона, обратное геокодирование,
поиск объектов рядом через Overpass API.
"""

import json
import math
import os
import time
import requests

from src.config import (
    GEOCODE_CACHE_PATH, OSM_CACHE_PATH,
    NOMINATIM_URL, OVERPASS_URL,
    REQUEST_TIMEOUT, NEARBY_RADIUS,
    ALMATY_DISTRICTS_APPROX, DISTRICTS_GEOJSON_PATH,
    OVERPASS_CATEGORIES
)

# ============================================================
# Загрузка geojson (если есть)
# ============================================================

_districts_geojson = None


def _load_districts_geojson():
    global _districts_geojson
    if _districts_geojson is not None:
        return _districts_geojson
    if os.path.exists(DISTRICTS_GEOJSON_PATH):
        try:
            with open(DISTRICTS_GEOJSON_PATH, encoding="utf-8") as f:
                _districts_geojson = json.load(f)
        except Exception:
            _districts_geojson = None
    return _districts_geojson


# ============================================================
# Вспомогательная геометрия: точка в полигоне (ray casting)
# ============================================================

def _point_in_polygon(lat, lon, polygon_coords) -> bool:
    """Проверяет, находится ли точка (lat, lon) внутри полигона."""
    x, y = lon, lat
    n = len(polygon_coords)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _check_geojson_district(lat, lon, geojson) -> str | None:
    """Определяет район по GeoJSON."""
    try:
        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            name = props.get("name") or props.get("NAME") or props.get("district", "")
            geom = feature.get("geometry", {})
            gtype = geom.get("type")
            coords = geom.get("coordinates", [])

            if gtype == "Polygon":
                rings = coords
                if rings and _point_in_polygon(lat, lon, rings[0]):
                    return name
            elif gtype == "MultiPolygon":
                for poly in coords:
                    if poly and _point_in_polygon(lat, lon, poly[0]):
                        return name
    except Exception:
        pass
    return None


# ============================================================
# Определение района
# ============================================================

def determine_district(lat: float, lon: float) -> str:
    # Район Алматы по координатам. Для точности лучше добавить официальный GeoJSON.
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return 'Район не определён точно'

    geojson = _load_districts_geojson()
    if geojson:
        result = _check_geojson_district(lat, lon, geojson)
        if result:
            result = str(result).replace(' (приближённо)', '').replace(' (??????????)', '').strip()
            for d in ['Алатауский', 'Алмалинский', 'Ауэзовский', 'Бостандыкский', 'Жетысуский', 'Медеуский', 'Наурызбайский', 'Турксибский']:
                if d in result:
                    return d
            return result

    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):
        return 'Район не определён точно'

    # Приближённые правила для 8 районов Алматы.
    # Южные/горные зоны
    if lon >= 76.97 and lat <= 43.28:
        return 'Медеуский'
    if lat <= 43.235 and 76.80 <= lon <= 76.97:
        return 'Бостандыкский'
    if lat <= 43.25 and lon < 76.80:
        return 'Наурызбайский'

    # Запад и северо-запад
    if lat >= 43.255 and lon < 76.84:
        return 'Алатауский'
    if 43.18 <= lat < 43.285 and 76.76 <= lon < 76.89:
        return 'Ауэзовский'

    # Центр
    if 43.235 <= lat < 43.285 and 76.86 <= lon < 76.965:
        return 'Алмалинский'

    # Север и северо-восток
    if lat >= 43.30 and lon >= 76.89:
        return 'Турксибский'
    if lat >= 43.255 and 76.84 <= lon < 76.98:
        return 'Жетысуский'

    # Восток
    if lon >= 76.94:
        return 'Медеуский'

    # Fallback: ближайший условный центр района.
    centers = {
        'Алатауский': (43.300, 76.790),
        'Алмалинский': (43.260, 76.920),
        'Ауэзовский': (43.235, 76.835),
        'Бостандыкский': (43.205, 76.900),
        'Жетысуский': (43.295, 76.910),
        'Медеуский': (43.220, 77.020),
        'Наурызбайский': (43.205, 76.745),
        'Турксибский': (43.335, 76.980),
    }
    best_name = None
    best_dist = 10 ** 9
    for name, (clat, clon) in centers.items():
        d = (lat - clat) ** 2 + ((lon - clon) * 0.73) ** 2
        if d < best_dist:
            best_dist = d
            best_name = name
    return best_name or 'Район не определён точно'


# ============================================================
# Кэш геокодирования
# ============================================================

def _load_geocode_cache() -> dict:
    try:
        if os.path.exists(GEOCODE_CACHE_PATH):
            with open(GEOCODE_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_geocode_cache(cache: dict):
    try:
        os.makedirs(os.path.dirname(GEOCODE_CACHE_PATH), exist_ok=True)
        with open(GEOCODE_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _cache_key(lat, lon) -> str:
    return f"{lat:.5f},{lon:.5f}"


# ============================================================
# Обратное геокодирование (Nominatim)
# ============================================================

def get_address(lat: float, lon: float) -> dict:
    """
    Определяет адрес по координатам через Nominatim.
    Результат кэшируется в geocode_cache.json.
    Возвращает словарь с полями: address, street, microdistrict.
    """
    cache = _load_geocode_cache()
    key = f"addr_{_cache_key(lat, lon)}"

    if key in cache:
        return cache[key]

    result = {
        "address": "Точный адрес не найден",
        "street": None,
        "microdistrict": "Не определён",
        "raw": {},
    }

    try:
        headers = {"User-Agent": "AlmatyRealEstateApp/1.0"}
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "lat": lat, "lon": lon,
                "format": "json",
                "accept-language": "ru",
                "addressdetails": 1,
            },
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        addr = data.get("address", {})

        # Строим читаемый адрес
        parts = []
        road = addr.get("road") or addr.get("pedestrian") or addr.get("footway")
        house = addr.get("house_number")
        if road:
            parts.append(road)
        if house:
            parts.append(house)

        microdistrict = (
            addr.get("suburb") or addr.get("neighbourhood") or
            addr.get("quarter") or addr.get("village") or
            addr.get("hamlet")
        )

        result["address"] = ", ".join(parts) if parts else "Точный адрес не найден"
        result["street"] = road
        result["microdistrict"] = microdistrict or "Не определён"
        result["raw"] = addr

    except requests.RequestException:
        pass
    except Exception:
        pass

    cache[key] = result
    _save_geocode_cache(cache)
    return result


def determine_microdistrict(lat: float, lon: float) -> str:
    """
    Определяет микрорайон по координатам.
    Использует кэшированный результат geocoding.
    """
    info = get_address(lat, lon)
    return info.get("microdistrict", "Не определён")


# ============================================================
# Кэш Overpass
# ============================================================

def _load_osm_cache() -> dict:
    try:
        if os.path.exists(OSM_CACHE_PATH):
            with open(OSM_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_osm_cache(cache: dict):
    try:
        os.makedirs(os.path.dirname(OSM_CACHE_PATH), exist_ok=True)
        with open(OSM_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================================================
# Расстояние между точками (формула Haversine)
# ============================================================

def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Возвращает расстояние в метрах."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ============================================================
# Поиск объектов рядом (Overpass API)
# ============================================================


# ============================================================
# ?????????? ????? ???????? ????? ????? Overpass API
# ============================================================

def _tag(tags: dict, key: str, default: str = "") -> str:
    """????????? ???????? ??? OSM."""
    val = tags.get(key, default)
    return "" if val is None else str(val)


def _name_from_tags(tags: dict) -> str:
    """??????? ???????? ???????? ???????? ???????."""
    return (
        _tag(tags, "name:ru") or
        _tag(tags, "name") or
        _tag(tags, "official_name:ru") or
        _tag(tags, "official_name") or
        _tag(tags, "brand:ru") or
        _tag(tags, "brand") or
        "??? ????????"
    )


def _address_from_tags(tags: dict) -> str:
    """???????? ????? ?? OSM-?????, ???? ?? ????."""
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
    """???????????? ???????? ???? ???????."""
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
        "school": "????? / ??????????????? ??????????",
        "kindergarten": "??????? ???",
        "university": "???????????",
        "college": "???????",
        "hospital": "????????",
        "clinic": "???????",
        "doctors": "????????? ???????",
        "pharmacy": "??????",
        "restaurant": "????????",
        "cafe": "????",
        "fast_food": "???????",
        "theatre": "?????",
        "cinema": "?????????",
        "bank": "????",
        "atm": "????????",
        "social_facility": "?????????? ??????????",
        "supermarket": "???????????",
        "convenience": "??????? ? ????",
        "mall": "???????? ?????",
        "department_store": "?????????",
        "park": "????",
        "sports_centre": "??????????",
        "fitness_centre": "??????",
        "museum": "?????",
        "bus_stop": "????????? ????????",
        "platform": "???????????? ?????????",
        "station": "???????",
        "subway_entrance": "???? ? ?????",
        "group_home": "??????? ??? / ?????????? ??????????",
        "assisted_living": "?????????? ??????????",
        "outreach": "?????????? ??????",
    }

    base = (
        mapping.get(amenity) or
        mapping.get(shop) or
        mapping.get(leisure) or
        mapping.get(tourism) or
        mapping.get(highway) or
        mapping.get(public_transport) or
        mapping.get(railway) or
        mapping.get(healthcare) or
        mapping.get(social) or
        amenity or shop or leisure or tourism or highway or public_transport or railway or healthcare or social or "??????"
    )

    if cuisine and amenity in ("restaurant", "cafe", "fast_food"):
        return f"{base}, ?????: {cuisine}"

    return base


def _classify_place(tags: dict, name: str) -> tuple[str, str]:
    """
    ?????????? (?????????, ??????????????).
    ?????: ???? ?????? ?????????? '??????? ???', ?? ??????? ??? ??????? ??????.
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

    # ??????? ???? / ????????? / ???. ?????????? ? ????????, ?? ??????? ?????
    social_keywords = [
        "??????? ???", "??? ???????", "??? ???????", "orphan", "orphanage",
        "????????", "????? ?????????", "????????? ?????", "????????"
    ]
    if any(k in name_l for k in social_keywords) or amenity == "social_facility" or social:
        return "Район не определён точно", (
            "?? ??????? ??????? ??????: ?? ????????/????? ??? ?????????? ??????????, "
            "??????? ???, ???????? ??? ??????? ???????????."
        )

    # ???????????
    if amenity == "school":
        warning = ""
        if any(k in name_l for k in ["????", "???????", "????????", "??????? ???"]):
            warning = "????????? ???: ?? ???????? ??? ????? ???? ?? ??????? ??????????????????? ?????."
        return "?????", warning

    if amenity == "kindergarten":
        return "??????? ????", ""

    if amenity in ("university", "college"):
        return "???????????? / ????????", ""

    # ????????
    if amenity in ("hospital", "clinic", "doctors") or _tag(tags, "healthcare"):
        return "????????", ""

    if amenity == "pharmacy":
        return "??????", ""

    # ????????
    if shop in ("mall", "department_store") or amenity == "marketplace":
        return "???????? ?????? / ?????", ""

    if shop in ("supermarket", "convenience", "grocery", "greengrocer", "bakery", "butcher", "deli"):
        return "???????? ? ????????", ""

    # ?????????
    if highway == "bus_stop" or public_transport in ("platform", "stop_position", "station"):
        return "????????? ??????????", ""

    if railway in ("station", "subway_entrance") or station == "subway":
        return "????? / ?/? ???????", ""

    # ?????
    if leisure == "park":
        return "????? ? ??????? ????", ""

    if leisure in ("sports_centre", "fitness_centre", "pitch", "stadium"):
        return "????? ? ??????", ""

    if amenity in ("restaurant", "cafe", "fast_food", "food_court"):
        return "???? ? ?????????", ""

    if amenity in ("theatre", "cinema") or tourism == "museum":
        return "???????? ? ?????", ""

    if amenity in ("bank", "atm"):
        return "????? ? ?????????", ""

    return "?????? ???????", ""


def _importance_score(category: str, distance: float, name: str) -> float:
    """
    ?????? ???????? ??? ?????????? ?????? UI.
    ??? ?????? score, ??? ???? ??????.
    """
    category_weight = {
        "????????? ??????????": 0.80,
        "????? / ?/? ???????": 0.60,
        "???????? ? ????????": 0.90,
        "??????": 0.95,
        "????????": 1.00,
        "?????": 1.05,
        "??????? ????": 1.10,
        "????? ? ??????? ????": 1.15,
        "???????? ?????? / ?????": 1.20,
        "???????????? / ????????": 1.25,
        "???? ? ?????????": 1.30,
        "????? ? ??????": 1.35,
        "???????? ? ?????": 1.40,
        "????? ? ?????????": 1.45,
        "?????????? ?????????? / ??????? ????": 1.50,
        "?????? ???????": 2.00,
    }.get(category, 2.00)

    no_name_penalty = 150 if not name or name == "??? ????????" else 0
    return distance * category_weight + no_name_penalty



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

# ============================================================
# MICRODISTRICTS PATCH START
# Улучшенное определение микрорайонов Алматы
# ============================================================

MICRODISTRICT_UNKNOWN = "Не определён"

ALMATY_MICRODISTRICTS = [
    "Аксай-1", "Аксай-2", "Аксай-3", "Аксай-4", "Аксай-5",
    "Айнабулак-1", "Айнабулак-2", "Айнабулак-3", "Айнабулак-4",
    "Алатау", "Алмагуль", "Алтын Бесик", "Алгабас", "Алгабас-1", "Алгабас-6",
    "Акбулак", "Акбулак-1", "Акбулак-2", "Атырау",
    "Баганашыл", "Баянаул", "Боралдай",
    "Горный Гигант", "Думан", "Думан-1", "Думан-2",
    "Достык", "Ерменсай", "Жас Канат", "Жетысу-1", "Жетысу-2", "Жетысу-3", "Жетысу-4",
    "Жулдыз-1", "Жулдыз-2", "Зердели",
    "Казахфильм", "Кайрат", "Калкаман-1", "Калкаман-2",
    "Каменка", "Карагайлы", "Кокжиек", "Коктем-1", "Коктем-2", "Коктем-3",
    "Кулагер", "Курылысшы",
    "Мамыр-1", "Мамыр-2", "Мамыр-3", "Мамыр-4", "Мамыр-5", "Мамыр-6", "Мамыр-7",
    "Мирас", "Нур Алатау", "Нуркент",
    "Орбита-1", "Орбита-2", "Орбита-3", "Орбита-4",
    "Рахат", "Сайран", "Самал-1", "Самал-2", "Самал-3",
    "Саялы", "Сулусай", "Таугуль-1", "Таугуль-2", "Таугуль-3",
    "Таусамалы", "Тастак-1", "Тастак-2", "Тастак-3",
    "Теректы", "Улжан-1", "Улжан-2", "Шанырак-1", "Шанырак-2",
    "Шугыла", "Юбилейный",
]

MICRODISTRICT_CENTERS = {
    "Самал-1": (43.2365, 76.9550, 900), "Самал-2": (43.2340, 76.9495, 900),
    "Самал-3": (43.2310, 76.9435, 900), "Коктем-1": (43.2305, 76.9280, 900),
    "Коктем-2": (43.2275, 76.9230, 900), "Коктем-3": (43.2240, 76.9175, 900),
    "Алмагуль": (43.2145, 76.8990, 1100), "Казахфильм": (43.2035, 76.9115, 1300),
    "Баганашыл": (43.1920, 76.9180, 1500), "Нур Алатау": (43.1855, 76.9060, 1600),
    "Мирас": (43.1910, 76.8950, 1400), "Ерменсай": (43.1720, 76.8920, 1700),
    "Горный Гигант": (43.2160, 76.9790, 1300), "Думан-1": (43.2460, 77.0500, 1500),
    "Думан-2": (43.2390, 77.0580, 1500),
    "Орбита-1": (43.1995, 76.8915, 1000), "Орбита-2": (43.1970, 76.8865, 1000),
    "Орбита-3": (43.1930, 76.8840, 1000), "Орбита-4": (43.1900, 76.8795, 1100),
    "Таугуль-1": (43.2160, 76.8540, 1000), "Таугуль-2": (43.2110, 76.8490, 1000),
    "Таугуль-3": (43.2070, 76.8440, 1000),
    "Мамыр-1": (43.2190, 76.8460, 900), "Мамыр-2": (43.2160, 76.8400, 900),
    "Мамыр-3": (43.2140, 76.8350, 900), "Мамыр-4": (43.2110, 76.8300, 900),
    "Мамыр-5": (43.2080, 76.8250, 900), "Мамыр-6": (43.2055, 76.8190, 900),
    "Мамыр-7": (43.2025, 76.8140, 900),
    "Аксай-1": (43.2335, 76.8340, 1000), "Аксай-2": (43.2380, 76.8280, 1000),
    "Аксай-3": (43.2420, 76.8220, 1000), "Аксай-4": (43.2470, 76.8170, 1000),
    "Аксай-5": (43.2520, 76.8120, 1000), "Алтын Бесик": (43.2405, 76.8040, 1300),
    "Жетысу-1": (43.2550, 76.8540, 1000), "Жетысу-2": (43.2600, 76.8580, 1000),
    "Жетысу-3": (43.2650, 76.8640, 1000), "Жетысу-4": (43.2700, 76.8700, 1000),
    "Тастак-1": (43.2520, 76.8890, 1100), "Тастак-2": (43.2490, 76.8810, 1100),
    "Тастак-3": (43.2450, 76.8750, 1100), "Сайран": (43.2380, 76.8760, 1300),
    "Айнабулак-1": (43.3100, 76.9250, 1100), "Айнабулак-2": (43.3160, 76.9300, 1100),
    "Айнабулак-3": (43.3220, 76.9360, 1100), "Айнабулак-4": (43.3280, 76.9420, 1100),
    "Кокжиек": (43.3380, 76.9450, 1600), "Кулагер": (43.3010, 76.9000, 1500),
    "Курылысшы": (43.2920, 76.8900, 1500),
    "Нуркент": (43.2800, 76.7600, 1800), "Саялы": (43.3040, 76.7820, 1800),
    "Акбулак": (43.2920, 76.8080, 1600), "Зердели": (43.2675, 76.8140, 1300),
    "Алгабас": (43.2590, 76.7850, 1800), "Алгабас-1": (43.2650, 76.7800, 1600),
    "Алгабас-6": (43.2520, 76.7740, 1600), "Улжан-1": (43.3180, 76.7900, 1800),
    "Улжан-2": (43.3280, 76.8000, 1800), "Шанырак-1": (43.3330, 76.8100, 1800),
    "Шанырак-2": (43.3430, 76.8200, 1800),
    "Калкаман-1": (43.2260, 76.7590, 1500), "Калкаман-2": (43.2170, 76.7480, 1500),
    "Каменка": (43.1810, 76.7590, 1800), "Карагайлы": (43.2020, 76.7440, 1800),
    "Таусамалы": (43.1900, 76.7820, 1700), "Шугыла": (43.2100, 76.7250, 1800),
    "Рахат": (43.2010, 76.7900, 1600),
    "Жулдыз-1": (43.3460, 77.0300, 1700), "Жулдыз-2": (43.3540, 77.0400, 1700),
    "Кайрат": (43.3470, 76.9950, 1800), "Жас Канат": (43.3520, 77.0200, 1700),
    "Алатау": (43.3500, 76.9800, 1800),
}

def get_all_microdistricts() -> list:
    return list(ALMATY_MICRODISTRICTS)

def extract_microdistrict_from_text(text: str) -> str:
    if not text:
        return ""
    low = str(text).lower()
    for name in sorted(ALMATY_MICRODISTRICTS, key=len, reverse=True):
        if name.lower() in low:
            return name
    import re as _re
    patterns = [
        (r"самал\s*[- ]?\s*([1-3])", "Самал-{}"), (r"орбита\s*[- ]?\s*([1-4])", "Орбита-{}"),
        (r"мамыр\s*[- ]?\s*([1-7])", "Мамыр-{}"), (r"аксай\s*[- ]?\s*([1-5])", "Аксай-{}"),
        (r"жетысу\s*[- ]?\s*([1-4])", "Жетысу-{}"), (r"айнабулак\s*[- ]?\s*([1-4])", "Айнабулак-{}"),
        (r"коктем\s*[- ]?\s*([1-3])", "Коктем-{}"), (r"таугуль\s*[- ]?\s*([1-3])", "Таугуль-{}"),
        (r"калкаман\s*[- ]?\s*([1-2])", "Калкаман-{}"), (r"жулдыз\s*[- ]?\s*([1-2])", "Жулдыз-{}"),
        (r"улжан\s*[- ]?\s*([1-2])", "Улжан-{}"), (r"шанырак\s*[- ]?\s*([1-2])", "Шанырак-{}"),
        (r"тастак\s*[- ]?\s*([1-3])", "Тастак-{}"),
    ]
    for pat, out in patterns:
        m = _re.search(pat, low)
        if m:
            return out.format(m.group(1))
    return ""

def determine_microdistrict(lat: float, lon: float, address_text: str = "") -> str:
    found = extract_microdistrict_from_text(address_text)
    if found:
        return found
    try:
        lat = float(lat); lon = float(lon)
    except Exception:
        return MICRODISTRICT_UNKNOWN
    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):
        return MICRODISTRICT_UNKNOWN
    best_name = ""; best_dist = 10**9; best_radius = 0
    for name, data in MICRODISTRICT_CENTERS.items():
        clat, clon, radius = data
        try:
            dist = haversine_distance(lat, lon, clat, clon)
        except Exception:
            import math
            r = 6371000
            p1 = math.radians(lat); p2 = math.radians(clat)
            dp = math.radians(clat - lat); dl = math.radians(clon - lon)
            a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
            dist = 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        if dist < best_dist:
            best_dist = dist; best_name = name; best_radius = radius
    if best_name and best_dist <= max(best_radius, 1400):
        return best_name
    return MICRODISTRICT_UNKNOWN

# ============================================================
# MICRODISTRICTS PATCH END
# ============================================================

def get_microdistrict_center(name: str):
    # Returns (lat, lon, radius_m) for microdistrict name.
    # Used by map filter when df["microdistrict"] is still empty.
    try:
        return MICRODISTRICT_CENTERS.get(str(name).strip())
    except Exception:
        return None

# ============================================================
# MICRODISTRICT GEOJSON / ACCURATE COORDINATES PATCH START
# ============================================================

# Самая правильная логика микрорайонов:
# - микрорайон — это НЕ одна точка, а территория/полигон;
# - если есть geo/microdistricts.geojson, программа определяет микрорайон по полигону;
# - если GeoJSON нет, программа использует приблизительные центры.

import json as _json
from pathlib import Path as _Path

MICRODISTRICT_GEOJSON_FILES = [
    "geo/microdistricts.geojson",
    "geo/almaty_microdistricts.geojson",
    "geo/almaty_microdistricts.json",
]

try:
    MICRODISTRICT_UNKNOWN
except NameError:
    MICRODISTRICT_UNKNOWN = "Не определён"

try:
    ALMATY_MICRODISTRICTS
except NameError:
    ALMATY_MICRODISTRICTS = []

try:
    MICRODISTRICT_CENTERS
except NameError:
    MICRODISTRICT_CENTERS = {}


def _md_norm_name(value: str) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    for x in ["микрорайон", "Микрорайон", "мкр.", "мкр", "МКР.", "МКР"]:
        s = s.replace(x, "")
    return s.replace("  ", " ").strip(" ,.-")


def _load_microdistrict_geojson():
    for file_name in MICRODISTRICT_GEOJSON_FILES:
        p = _Path(file_name)
        if p.exists():
            for enc in ["utf-8", "utf-8-sig"]:
                try:
                    with open(p, "r", encoding=enc) as f:
                        return _json.load(f)
                except Exception:
                    pass
    return None


def _microdistrict_feature_name(feature: dict) -> str:
    props = feature.get("properties", {}) or {}
    keys = [
        "microdistrict", "microdistrict_ru", "name", "name_ru", "name:ru",
        "NAME", "Name", "title", "TITLE", "mkr", "МКР", "district_name"
    ]
    for key in keys:
        if props.get(key):
            return _md_norm_name(props.get(key))
    return ""


def _point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    if len(ring) < 3:
        return False

    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)):
            x_intersect = (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
            if lon < x_intersect:
                inside = not inside
        j = i

    return inside


def _point_in_geometry(lat: float, lon: float, geom: dict) -> bool:
    if not geom:
        return False

    gtype = geom.get("type")
    coords = geom.get("coordinates", [])

    if gtype == "Polygon":
        if not coords:
            return False
        if not _point_in_ring(lon, lat, coords[0]):
            return False
        for hole in coords[1:]:
            if _point_in_ring(lon, lat, hole):
                return False
        return True

    if gtype == "MultiPolygon":
        for poly in coords:
            if not poly:
                continue
            if _point_in_ring(lon, lat, poly[0]):
                in_hole = False
                for hole in poly[1:]:
                    if _point_in_ring(lon, lat, hole):
                        in_hole = True
                        break
                if not in_hole:
                    return True
        return False

    return False


def _iter_geojson_points(geom: dict):
    if not geom:
        return
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])

    if gtype == "Polygon":
        for ring in coords:
            for point in ring:
                yield float(point[1]), float(point[0])

    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                for point in ring:
                    yield float(point[1]), float(point[0])


def _feature_center_and_radius(feature: dict):
    pts = list(_iter_geojson_points(feature.get("geometry", {})))
    if not pts:
        return None

    clat = sum(p[0] for p in pts) / len(pts)
    clon = sum(p[1] for p in pts) / len(pts)

    max_dist = 0
    for lat, lon in pts:
        try:
            d = haversine_distance(clat, clon, lat, lon)
        except Exception:
            dlat = (lat - clat) * 111000.0
            dlon = (lon - clon) * 81000.0
            d = (dlat * dlat + dlon * dlon) ** 0.5
        max_dist = max(max_dist, d)

    return (clat, clon, max(800, min(max_dist, 3500)))


def determine_microdistrict_from_geojson(lat: float, lon: float) -> str:
    geojson = _load_microdistrict_geojson()
    if not geojson:
        return ""

    for feature in geojson.get("features", []):
        name = _microdistrict_feature_name(feature)
        if name and _point_in_geometry(float(lat), float(lon), feature.get("geometry", {})):
            return name

    return ""


def get_microdistrict_center(name: str):
    name = _md_norm_name(name)

    geojson = _load_microdistrict_geojson()
    if geojson:
        for feature in geojson.get("features", []):
            fname = _microdistrict_feature_name(feature)
            if fname == name:
                center = _feature_center_and_radius(feature)
                if center:
                    return center

    try:
        return MICRODISTRICT_CENTERS.get(name)
    except Exception:
        return None


def determine_microdistrict(lat: float, lon: float, address_text: str = "") -> str:
    # 1. Try address text
    try:
        found = extract_microdistrict_from_text(address_text)
        if found:
            return found
    except Exception:
        pass

    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return MICRODISTRICT_UNKNOWN

    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):
        return MICRODISTRICT_UNKNOWN

    # 2. Exact polygon if GeoJSON exists
    found_geo = determine_microdistrict_from_geojson(lat, lon)
    if found_geo:
        return found_geo

    # 3. Fallback by nearest center
    best_name = ""
    best_dist = 10**9
    best_radius = 0

    for name, data in MICRODISTRICT_CENTERS.items():
        try:
            clat, clon, radius = data
        except Exception:
            continue

        try:
            dist = haversine_distance(lat, lon, clat, clon)
        except Exception:
            dlat = (lat - clat) * 111000.0
            dlon = (lon - clon) * 81000.0
            dist = (dlat * dlat + dlon * dlon) ** 0.5

        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_radius = radius

    if best_name and best_dist <= max(float(best_radius or 0), 1400.0):
        return best_name

    return MICRODISTRICT_UNKNOWN

# ============================================================
# MICRODISTRICT GEOJSON / ACCURATE COORDINATES PATCH END
# ============================================================

# ============================================================
# MICRODISTRICT NO-UNKNOWN OVERRIDE START
# ============================================================

_EXTRA_MICRODISTRICT_CENTERS = {
    "Самал-1": (43.2365, 76.9550, 900), "Самал-2": (43.2340, 76.9495, 900), "Самал-3": (43.2310, 76.9435, 900),
    "Коктем-1": (43.2305, 76.9280, 900), "Коктем-2": (43.2275, 76.9230, 900), "Коктем-3": (43.2240, 76.9175, 900),
    "Алмагуль": (43.2145, 76.8990, 1100), "Казахфильм": (43.2035, 76.9115, 1300),
    "Баганашыл": (43.1920, 76.9180, 1500), "Нур Алатау": (43.1855, 76.9060, 1700),
    "Мирас": (43.1910, 76.8950, 1500), "Ерменсай": (43.1720, 76.8920, 1900),
    "Горный Гигант": (43.2160, 76.9790, 1300), "Думан-1": (43.2460, 77.0500, 1700), "Думан-2": (43.2390, 77.0580, 1700),

    "Орбита-1": (43.1995, 76.8915, 1100), "Орбита-2": (43.1970, 76.8865, 1100),
    "Орбита-3": (43.1930, 76.8840, 1100), "Орбита-4": (43.1900, 76.8795, 1200),
    "Таугуль-1": (43.2160, 76.8540, 1100), "Таугуль-2": (43.2110, 76.8490, 1100), "Таугуль-3": (43.2070, 76.8440, 1100),

    "Мамыр-1": (43.2190, 76.8460, 1000), "Мамыр-2": (43.2160, 76.8400, 1000), "Мамыр-3": (43.2140, 76.8350, 1000),
    "Мамыр-4": (43.2110, 76.8300, 1000), "Мамыр-5": (43.2080, 76.8250, 1000), "Мамыр-6": (43.2055, 76.8190, 1000), "Мамыр-7": (43.2025, 76.8140, 1000),

    "Аксай-1": (43.2335, 76.8340, 1100), "Аксай-2": (43.2380, 76.8280, 1100), "Аксай-3": (43.2420, 76.8220, 1100),
    "Аксай-4": (43.2470, 76.8170, 1100), "Аксай-5": (43.2520, 76.8120, 1100),
    "Алтын Бесик": (43.2405, 76.8040, 1500),

    "Жетысу-1": (43.2550, 76.8540, 1100), "Жетысу-2": (43.2600, 76.8580, 1100),
    "Жетысу-3": (43.2650, 76.8640, 1100), "Жетысу-4": (43.2700, 76.8700, 1100),
    "Тастак-1": (43.2520, 76.8890, 1200), "Тастак-2": (43.2490, 76.8810, 1200),
    "Тастак-3": (43.2450, 76.8750, 1200), "Сайран": (43.2380, 76.8760, 1400),

    "Айнабулак-1": (43.3100, 76.9250, 1200), "Айнабулак-2": (43.3160, 76.9300, 1200),
    "Айнабулак-3": (43.3220, 76.9360, 1200), "Айнабулак-4": (43.3280, 76.9420, 1200),
    "Кокжиек": (43.3380, 76.9450, 1800), "Кулагер": (43.3010, 76.9000, 1700),
    "Курылысшы": (43.2920, 76.8900, 1700),

    "Нуркент": (43.2800, 76.7600, 2000), "Саялы": (43.3040, 76.7820, 2000),
    "Акбулак": (43.2920, 76.8080, 1800), "Зердели": (43.2675, 76.8140, 1500),
    "Алгабас": (43.2590, 76.7850, 2000), "Алгабас-1": (43.2650, 76.7800, 1800), "Алгабас-6": (43.2520, 76.7740, 1800),
    "Улжан-1": (43.3180, 76.7900, 2000), "Улжан-2": (43.3280, 76.8000, 2000),
    "Шанырак-1": (43.3330, 76.8100, 2000), "Шанырак-2": (43.3430, 76.8200, 2000),

    "Калкаман-1": (43.2260, 76.7590, 1700), "Калкаман-2": (43.2170, 76.7480, 1700),
    "Каменка": (43.1810, 76.7590, 2200), "Карагайлы": (43.2020, 76.7440, 2000),
    "Таусамалы": (43.1900, 76.7820, 1900), "Шугыла": (43.2100, 76.7250, 2200), "Рахат": (43.2010, 76.7900, 1800),

    "Жулдыз-1": (43.3460, 77.0300, 2000), "Жулдыз-2": (43.3540, 77.0400, 2000),
    "Кайрат": (43.3470, 76.9950, 2200), "Жас Канат": (43.3520, 77.0200, 2000), "Алатау": (43.3500, 76.9800, 2200),

    "Золотой квадрат": (43.2550, 76.9450, 1600),
    "Арбат": (43.2620, 76.9400, 1200),
    "Центр": (43.2500, 76.9300, 1800),
}

try:
    MICRODISTRICT_UNKNOWN
except NameError:
    MICRODISTRICT_UNKNOWN = "Не определён"

try:
    MICRODISTRICT_CENTERS.update(_EXTRA_MICRODISTRICT_CENTERS)
except Exception:
    MICRODISTRICT_CENTERS = dict(_EXTRA_MICRODISTRICT_CENTERS)

try:
    for _name in _EXTRA_MICRODISTRICT_CENTERS:
        if _name not in ALMATY_MICRODISTRICTS:
            ALMATY_MICRODISTRICTS.append(_name)
except Exception:
    ALMATY_MICRODISTRICTS = list(_EXTRA_MICRODISTRICT_CENTERS.keys())


def get_all_microdistricts() -> list:
    try:
        return sorted(set(ALMATY_MICRODISTRICTS))
    except Exception:
        return sorted(set(_EXTRA_MICRODISTRICT_CENTERS.keys()))


def _nearest_microdistrict_by_center(lat: float, lon: float) -> str:
    best_name = ""
    best_dist = 10**18

    for name, data in MICRODISTRICT_CENTERS.items():
        try:
            clat, clon, _radius = data
            try:
                dist = haversine_distance(lat, lon, clat, clon)
            except Exception:
                dlat = (lat - clat) * 111000.0
                dlon = (lon - clon) * 81000.0
                dist = (dlat * dlat + dlon * dlon) ** 0.5

            if dist < best_dist:
                best_dist = dist
                best_name = name
        except Exception:
            continue

    return best_name or MICRODISTRICT_UNKNOWN


def determine_microdistrict(lat: float, lon: float, address_text: str = "") -> str:
    try:
        found = extract_microdistrict_from_text(address_text)
        if found:
            return found
    except Exception:
        pass

    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return MICRODISTRICT_UNKNOWN

    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):
        return MICRODISTRICT_UNKNOWN

    try:
        found_geo = determine_microdistrict_from_geojson(lat, lon)
        if found_geo:
            return found_geo
    except Exception:
        pass

    return _nearest_microdistrict_by_center(lat, lon)


def get_microdistrict_center(name: str):
    try:
        name = str(name).strip()
    except Exception:
        return None

    try:
        center = MICRODISTRICT_CENTERS.get(name)
        if center:
            return center
    except Exception:
        pass

    try:
        geojson = _load_microdistrict_geojson()
        if geojson:
            for feature in geojson.get("features", []):
                fname = _microdistrict_feature_name(feature)
                if fname == name:
                    c = _feature_center_and_radius(feature)
                    if c:
                        return c
    except Exception:
        pass

    return None

# ============================================================
# MICRODISTRICT NO-UNKNOWN OVERRIDE END
# ============================================================

# ============================================================
# VERIFIED MICRODISTRICT CENTERS PATCH START
# ============================================================

# Исправленные центры микрорайонов.
# Главное: Жетысу-1/2/3/4 должны быть в Ауэзовском районе,
# рядом с Бауыржан Момышулы / Сарыарка, а не севернее.
_VERIFIED_MICRODISTRICT_CENTERS = {
    "Жетысу-1": (43.2241, 76.8381, 950),
    "Жетысу-2": (43.2215, 76.8460, 950),
    "Жетысу-3": (43.2194, 76.8424, 950),
    "Жетысу-4": (43.2203, 76.8365, 1050),

    # Варианты написания
    "Жетысу 1": (43.2241, 76.8381, 950),
    "Жетысу 2": (43.2215, 76.8460, 950),
    "Жетысу 3": (43.2194, 76.8424, 950),
    "Жетысу 4": (43.2203, 76.8365, 1050),

    # Частая опечатка пользователя
    "Жытысу-1": (43.2241, 76.8381, 950),
    "Жытысу-2": (43.2215, 76.8460, 950),
    "Жытысу-3": (43.2194, 76.8424, 950),
    "Жытысу-4": (43.2203, 76.8365, 1050),
}

try:
    MICRODISTRICT_CENTERS.update(_VERIFIED_MICRODISTRICT_CENTERS)
except Exception:
    MICRODISTRICT_CENTERS = dict(_VERIFIED_MICRODISTRICT_CENTERS)

try:
    for _n in ["Жетысу-1", "Жетысу-2", "Жетысу-3", "Жетысу-4"]:
        if _n not in ALMATY_MICRODISTRICTS:
            ALMATY_MICRODISTRICTS.append(_n)
except Exception:
    ALMATY_MICRODISTRICTS = ["Жетысу-1", "Жетысу-2", "Жетысу-3", "Жетысу-4"]


def _normalize_microdistrict_alias(name: str) -> str:
    """Нормализация названий: Жетысу 1 / Жытысу-1 -> Жетысу-1."""
    s = str(name or "").strip()
    s = s.replace("микрорайон", "").replace("Микрорайон", "")
    s = s.replace("мкр.", "").replace("мкр", "").strip(" ,.")

    replacements = {
        "Жетысу 1": "Жетысу-1",
        "Жетысу 2": "Жетысу-2",
        "Жетысу 3": "Жетысу-3",
        "Жетысу 4": "Жетысу-4",
        "жетысу 1": "Жетысу-1",
        "жетысу 2": "Жетысу-2",
        "жетысу 3": "Жетысу-3",
        "жетысу 4": "Жетысу-4",
        "Жытысу-1": "Жетысу-1",
        "Жытысу-2": "Жетысу-2",
        "Жытысу-3": "Жетысу-3",
        "Жытысу-4": "Жетысу-4",
        "Жытысу 1": "Жетысу-1",
        "Жытысу 2": "Жетысу-2",
        "Жытысу 3": "Жетысу-3",
        "Жытысу 4": "Жетысу-4",
    }
    return replacements.get(s, s)


def get_microdistrict_center(name: str):
    """
    Центр микрорайона для фильтра карты.
    Эта версия берёт исправленные координаты Жетысу-1/2/3/4.
    """
    name = _normalize_microdistrict_alias(name)

    try:
        center = MICRODISTRICT_CENTERS.get(name)
        if center:
            return center
    except Exception:
        pass

    try:
        geojson = _load_microdistrict_geojson()
        if geojson:
            for feature in geojson.get("features", []):
                fname = _microdistrict_feature_name(feature)
                if _normalize_microdistrict_alias(fname) == name:
                    c = _feature_center_and_radius(feature)
                    if c:
                        return c
    except Exception:
        pass

    return None


def determine_microdistrict(lat: float, lon: float, address_text: str = "") -> str:
    """
    Определение микрорайона с исправленными координатами Жетысу.
    Порядок:
    1) ищет микрорайон в адресе;
    2) если есть geo/microdistricts.geojson — ищет по полигону;
    3) иначе выбирает ближайший центр.
    """
    unknown = "Не определён"
    try:
        unknown = MICRODISTRICT_UNKNOWN
    except Exception:
        pass

    try:
        found = extract_microdistrict_from_text(address_text)
        found = _normalize_microdistrict_alias(found)
        if found:
            return found
    except Exception:
        pass

    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return unknown

    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):
        return unknown

    try:
        found_geo = determine_microdistrict_from_geojson(lat, lon)
        found_geo = _normalize_microdistrict_alias(found_geo)
        if found_geo:
            return found_geo
    except Exception:
        pass

    best_name = ""
    best_dist = 10**18

    try:
        centers = MICRODISTRICT_CENTERS
    except Exception:
        centers = _VERIFIED_MICRODISTRICT_CENTERS

    for name, data in centers.items():
        try:
            clat, clon, _radius = data
            try:
                dist = haversine_distance(lat, lon, clat, clon)
            except Exception:
                dlat = (lat - clat) * 111000.0
                dlon = (lon - clon) * 81000.0
                dist = (dlat * dlat + dlon * dlon) ** 0.5

            if dist < best_dist:
                best_dist = dist
                best_name = _normalize_microdistrict_alias(name)
        except Exception:
            continue

    return best_name or unknown

# ============================================================
# VERIFIED MICRODISTRICT CENTERS PATCH END
# ============================================================

# ============================================================
# OSM PRECISE MICRODISTRICT CENTERS OVERRIDE START
# ============================================================

import json as _precise_json
from pathlib import Path as _PrecisePath

_OSM_MICRO_CENTERS_FILE = _PrecisePath("geo/microdistrict_centers_osm.json")
_OSM_MICRO_GEOJSON_FILES = [
    "geo/microdistricts.geojson",
    "geo/microdistricts_osm_generated.geojson",
    "geo/almaty_microdistricts.geojson",
]

try:
    MICRODISTRICT_UNKNOWN
except NameError:
    MICRODISTRICT_UNKNOWN = "Не определён"

try:
    MICRODISTRICT_CENTERS
except NameError:
    MICRODISTRICT_CENTERS = {}

try:
    ALMATY_MICRODISTRICTS
except NameError:
    ALMATY_MICRODISTRICTS = []


def _md_alias(name: str) -> str:
    s = str(name or "").strip()
    s = s.replace("микрорайон", "").replace("Микрорайон", "")
    s = s.replace("мкр.", "").replace("мкр", "").strip(" ,.")
    s = s.replace("Жытысу", "Жетысу")
    aliases = {
        "Жетысу 1": "Жетысу-1", "Жетысу 2": "Жетысу-2",
        "Жетысу 3": "Жетысу-3", "Жетысу 4": "Жетысу-4",
        "жетысу 1": "Жетысу-1", "жетысу 2": "Жетысу-2",
        "жетысу 3": "Жетысу-3", "жетысу 4": "Жетысу-4",
        "Самал 1": "Самал-1", "Самал 2": "Самал-2", "Самал 3": "Самал-3",
        "Орбита 1": "Орбита-1", "Орбита 2": "Орбита-2",
        "Орбита 3": "Орбита-3", "Орбита 4": "Орбита-4",
        "Аксай 1": "Аксай-1", "Аксай 2": "Аксай-2", "Аксай 3": "Аксай-3",
        "Аксай 4": "Аксай-4", "Аксай 5": "Аксай-5",
        "Мамыр 1": "Мамыр-1", "Мамыр 2": "Мамыр-2", "Мамыр 3": "Мамыр-3",
        "Мамыр 4": "Мамыр-4", "Мамыр 5": "Мамыр-5", "Мамыр 6": "Мамыр-6", "Мамыр 7": "Мамыр-7",
        "Айнабулак 1": "Айнабулак-1", "Айнабулак 2": "Айнабулак-2",
        "Айнабулак 3": "Айнабулак-3", "Айнабулак 4": "Айнабулак-4",
    }
    return aliases.get(s, s)


def _load_osm_micro_centers():
    if not _OSM_MICRO_CENTERS_FILE.exists():
        return {}
    try:
        data = _precise_json.loads(_OSM_MICRO_CENTERS_FILE.read_text(encoding="utf-8"))
        out = {}
        for name, v in data.items():
            try:
                out[_md_alias(name)] = (
                    float(v["lat"]),
                    float(v["lon"]),
                    float(v.get("radius_m", 1200)),
                )
            except Exception:
                continue
        return out
    except Exception:
        return {}


def _load_microdistrict_geojson():
    for file_name in _OSM_MICRO_GEOJSON_FILES:
        p = _PrecisePath(file_name)
        if p.exists():
            for enc in ["utf-8", "utf-8-sig"]:
                try:
                    with open(p, "r", encoding=enc) as f:
                        return _precise_json.load(f)
                except Exception:
                    pass
    return None


def get_all_microdistricts() -> list:
    names = set()
    try:
        names.update([_md_alias(x) for x in ALMATY_MICRODISTRICTS])
    except Exception:
        pass
    names.update(_load_osm_micro_centers().keys())
    try:
        names.update([_md_alias(x) for x in MICRODISTRICT_CENTERS.keys()])
    except Exception:
        pass
    return sorted([x for x in names if x])


def get_microdistrict_center(name: str):
    name = _md_alias(name)

    precise = _load_osm_micro_centers()
    if name in precise:
        return precise[name]

    try:
        geojson = _load_microdistrict_geojson()
        if geojson:
            for feature in geojson.get("features", []):
                fname = _md_alias(_microdistrict_feature_name(feature))
                if fname == name:
                    try:
                        if feature.get("geometry", {}).get("type") == "Point":
                            lon, lat = feature["geometry"]["coordinates"][:2]
                            return (float(lat), float(lon), 1200)
                    except Exception:
                        pass
                    center = _feature_center_and_radius(feature)
                    if center:
                        return center
    except Exception:
        pass

    try:
        return MICRODISTRICT_CENTERS.get(name)
    except Exception:
        return None


def _nearest_microdistrict_precise(lat: float, lon: float) -> str:
    all_centers = {}
    try:
        all_centers.update(MICRODISTRICT_CENTERS)
    except Exception:
        pass
    all_centers.update(_load_osm_micro_centers())

    best_name = ""
    best_dist = 10**18

    for name, data in all_centers.items():
        try:
            clat, clon, _radius = data
            try:
                dist = haversine_distance(lat, lon, clat, clon)
            except Exception:
                dlat = (lat - clat) * 111000.0
                dlon = (lon - clon) * 81000.0
                dist = (dlat * dlat + dlon * dlon) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_name = _md_alias(name)
        except Exception:
            continue

    return best_name or "Не определён"


def determine_microdistrict(lat: float, lon: float, address_text: str = "") -> str:
    try:
        found = _md_alias(extract_microdistrict_from_text(address_text))
        if found:
            return found
    except Exception:
        pass

    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return "Не определён"

    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):
        return "Не определён"

    try:
        found_geo = determine_microdistrict_from_geojson(lat, lon)
        found_geo = _md_alias(found_geo)
        if found_geo:
            return found_geo
    except Exception:
        pass

    return _nearest_microdistrict_precise(lat, lon)

# ============================================================
# OSM PRECISE MICRODISTRICT CENTERS OVERRIDE END
# ============================================================

# ============================================================
# FAST START MICRODISTRICT CACHE PATCH START
# ============================================================

_FAST_OSM_CENTERS_CACHE = None
_FAST_GEOJSON_CACHE = None

def _load_osm_micro_centers():
    global _FAST_OSM_CENTERS_CACHE
    if _FAST_OSM_CENTERS_CACHE is not None:
        return _FAST_OSM_CENTERS_CACHE

    try:
        from pathlib import Path as _Path
        import json as _json

        p = _Path("geo/microdistrict_centers_osm.json")
        if not p.exists():
            _FAST_OSM_CENTERS_CACHE = {}
            return _FAST_OSM_CENTERS_CACHE

        data = _json.loads(p.read_text(encoding="utf-8"))
        out = {}

        for name, v in data.items():
            try:
                key = _md_alias(name) if "_md_alias" in globals() else str(name).strip()
                out[key] = (
                    float(v["lat"]),
                    float(v["lon"]),
                    float(v.get("radius_m", 1200)),
                )
            except Exception:
                continue

        _FAST_OSM_CENTERS_CACHE = out
        return _FAST_OSM_CENTERS_CACHE
    except Exception:
        _FAST_OSM_CENTERS_CACHE = {}
        return _FAST_OSM_CENTERS_CACHE


def _load_microdistrict_geojson():
    global _FAST_GEOJSON_CACHE
    if _FAST_GEOJSON_CACHE is not None:
        return _FAST_GEOJSON_CACHE

    try:
        from pathlib import Path as _Path
        import json as _json

        candidates = [
            "geo/microdistricts.geojson",
            "geo/almaty_microdistricts.geojson",
            "geo/almaty_microdistricts.json",
        ]

        for file_name in candidates:
            p = _Path(file_name)
            if p.exists():
                for enc in ["utf-8", "utf-8-sig"]:
                    try:
                        with open(p, "r", encoding=enc) as f:
                            _FAST_GEOJSON_CACHE = _json.load(f)
                            return _FAST_GEOJSON_CACHE
                    except Exception:
                        pass

        _FAST_GEOJSON_CACHE = None
        return None
    except Exception:
        _FAST_GEOJSON_CACHE = None
        return None


def determine_microdistrict(lat: float, lon: float, address_text: str = "") -> str:
    try:
        found = _md_alias(extract_microdistrict_from_text(address_text)) if "_md_alias" in globals() else extract_microdistrict_from_text(address_text)
        if found:
            return found
    except Exception:
        pass

    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return "Не определён"

    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):
        return "Не определён"

    try:
        found_geo = determine_microdistrict_from_geojson(lat, lon)
        found_geo = _md_alias(found_geo) if "_md_alias" in globals() else found_geo
        if found_geo:
            return found_geo
    except Exception:
        pass

    all_centers = {}
    try:
        all_centers.update(MICRODISTRICT_CENTERS)
    except Exception:
        pass

    try:
        all_centers.update(_load_osm_micro_centers())
    except Exception:
        pass

    best_name = ""
    best_dist = 10**18

    for name, data in all_centers.items():
        try:
            clat, clon, _radius = data
            try:
                dist = haversine_distance(lat, lon, clat, clon)
            except Exception:
                dlat = (lat - clat) * 111000.0
                dlon = (lon - clon) * 81000.0
                dist = (dlat * dlat + dlon * dlon) ** 0.5

            if dist < best_dist:
                best_dist = dist
                best_name = _md_alias(name) if "_md_alias" in globals() else str(name)
        except Exception:
            continue

    return best_name or "Не определён"

# ============================================================
# FAST START MICRODISTRICT CACHE PATCH END
# ============================================================
