# -*- coding: utf-8 -*-
"""
Improves microdistrict detection for the Almaty real estate app.
Run from the project root:
    python fix_microdistrict_improved.py

What it does:
- improves Nominatim microdistrict extraction;
- parses display_name / namedetails for Алматы микрорайоны;
- adds coordinate fallback for common Almaty microdistricts;
- clears old geocode cache;
- optionally shows microdistrict source in the Object tab.
"""
from pathlib import Path
import re

ROOT = Path.cwd()
geo_path = ROOT / "src" / "geo_utils.py"
main_path = ROOT / "main.py"
cache_path = ROOT / "cache" / "geocode_cache.json"

if not geo_path.exists() or not main_path.exists():
    raise SystemExit("Запусти этот файл из корня проекта, где есть main.py и папка src/")

# Backups
for p in [geo_path, main_path]:
    backup = p.with_suffix(p.suffix + ".backup_microdistrict")
    if not backup.exists():
        backup.write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

geo = geo_path.read_text(encoding="utf-8", errors="replace")

# Add re import if not exists
if "import re" not in geo:
    geo = geo.replace("import json\n", "import json\nimport re\n", 1)

new_geocode_block = r'''
# ============================================================
# Обратное геокодирование (Nominatim) + улучшенное определение микрорайона
# ============================================================

# Приближённые центры популярных микрорайонов Алматы.
# Это НЕ официальные границы, а fallback, когда Nominatim не возвращает suburb/neighbourhood.
# Поэтому такие результаты помечаются как "приближённо".
ALMATY_MICRODISTRICT_CENTERS = [
    ("Самал-1", 43.2349, 76.9545, 900),
    ("Самал-2", 43.2319, 76.9490, 1000),
    ("Самал-3", 43.2295, 76.9415, 1000),
    ("Коктем-1", 43.2375, 76.9210, 1000),
    ("Коктем-2", 43.2346, 76.9135, 1000),
    ("Коктем-3", 43.2298, 76.9120, 1000),
    ("Алмагуль", 43.2215, 76.9050, 1300),
    ("Казахфильм", 43.1995, 76.8980, 1500),
    ("Таугуль", 43.2070, 76.8835, 1500),
    ("Орбита-1", 43.2090, 76.8750, 1100),
    ("Орбита-2", 43.2050, 76.8820, 1100),
    ("Орбита-3", 43.2020, 76.8890, 1100),
    ("Орбита-4", 43.2060, 76.8960, 1100),
    ("Аксай-1", 43.2350, 76.8320, 1200),
    ("Аксай-2", 43.2310, 76.8440, 1200),
    ("Аксай-3", 43.2270, 76.8550, 1200),
    ("Аксай-4", 43.2225, 76.8640, 1200),
    ("Аксай-5", 43.2185, 76.8730, 1200),
    ("Мамыр-1", 43.2140, 76.8420, 1300),
    ("Мамыр-2", 43.2100, 76.8520, 1300),
    ("Мамыр-3", 43.2060, 76.8620, 1300),
    ("Мамыр-4", 43.2020, 76.8720, 1300),
    ("Мамыр-7", 43.2020, 76.8320, 1300),
    ("Жетысу-1", 43.2425, 76.8350, 1200),
    ("Жетысу-2", 43.2475, 76.8420, 1200),
    ("Жетысу-3", 43.2520, 76.8500, 1200),
    ("Айнабулак-1", 43.3160, 76.9260, 1400),
    ("Айнабулак-2", 43.3210, 76.9350, 1400),
    ("Айнабулак-3", 43.3260, 76.9440, 1400),
    ("Жулдыз", 43.3420, 77.0060, 1700),
    ("Думан", 43.2065, 77.0150, 1700),
    ("Калкаман", 43.2680, 76.8020, 1700),
    ("Шанырак", 43.3340, 76.8330, 2000),
    ("Акбулак", 43.3110, 76.8060, 1700),
    ("Кокжиек", 43.3450, 76.9320, 1700),
    ("Шугыла", 43.2160, 76.7700, 1800),
    ("Нуркент", 43.2700, 76.7900, 1800),
]


def _geo_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Локальная Haversine-функция, чтобы fallback работал до определения haversine_distance."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _normalize_microdistrict_name(text: str) -> str:
    """Приводит найденное название микрорайона к нормальному виду."""
    if not text:
        return ""

    t = str(text).strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace("мкр.", "микрорайон")
    t = t.replace("мкр", "микрорайон")
    t = t.replace("микрорайоны", "микрорайон")
    t = t.strip(" ,.;:-")

    # Убираем лишние слова, но оставляем само имя.
    t = re.sub(r"^(микрорайон|район)\s+", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\s+(микрорайон)$", "", t, flags=re.IGNORECASE).strip()

    aliases = {
        "samal 1": "Самал-1", "samal-1": "Самал-1", "самал 1": "Самал-1", "самал-1": "Самал-1",
        "samal 2": "Самал-2", "samal-2": "Самал-2", "самал 2": "Самал-2", "самал-2": "Самал-2",
        "samal 3": "Самал-3", "samal-3": "Самал-3", "самал 3": "Самал-3", "самал-3": "Самал-3",
        "aksai 1": "Аксай-1", "aksai-1": "Аксай-1", "аксай 1": "Аксай-1", "аксай-1": "Аксай-1",
        "aksai 2": "Аксай-2", "aksai-2": "Аксай-2", "аксай 2": "Аксай-2", "аксай-2": "Аксай-2",
        "aksai 3": "Аксай-3", "aksai-3": "Аксай-3", "аксай 3": "Аксай-3", "аксай-3": "Аксай-3",
        "aksai 4": "Аксай-4", "aksai-4": "Аксай-4", "аксай 4": "Аксай-4", "аксай-4": "Аксай-4",
        "aksai 5": "Аксай-5", "aksai-5": "Аксай-5", "аксай 5": "Аксай-5", "аксай-5": "Аксай-5",
        "orbita 1": "Орбита-1", "orbita-1": "Орбита-1", "орбита 1": "Орбита-1", "орбита-1": "Орбита-1",
        "orbita 2": "Орбита-2", "orbita-2": "Орбита-2", "орбита 2": "Орбита-2", "орбита-2": "Орбита-2",
        "orbita 3": "Орбита-3", "orbita-3": "Орбита-3", "орбита 3": "Орбита-3", "орбита-3": "Орбита-3",
        "orbita 4": "Орбита-4", "orbita-4": "Орбита-4", "орбита 4": "Орбита-4", "орбита-4": "Орбита-4",
    }

    key = t.lower().replace("–", "-").replace("—", "-")
    key = re.sub(r"\s+", " ", key)
    if key in aliases:
        return aliases[key]

    # Красивое оформление известных шаблонов
    patterns = [
        (r"самал\s*[- ]?([123])", "Самал-{}"),
        (r"орбита\s*[- ]?([1234])", "Орбита-{}"),
        (r"аксай\s*[- ]?([1-5])", "Аксай-{}"),
        (r"мамыр\s*[- ]?([1-9])", "Мамыр-{}"),
        (r"жетысу\s*[- ]?([1-4])", "Жетысу-{}"),
        (r"айнабулак\s*[- ]?([1-4])", "Айнабулак-{}"),
    ]
    for pat, fmt in patterns:
        m = re.search(pat, key, flags=re.IGNORECASE)
        if m:
            return fmt.format(m.group(1))

    # Если начинается с известных названий без номера
    known = [
        "Алмагуль", "Казахфильм", "Таугуль", "Коктем", "Жулдыз", "Думан",
        "Калкаман", "Шанырак", "Акбулак", "Кокжиек", "Шугыла", "Нуркент", "Самал", "Сайран"
    ]
    for k in known:
        if k.lower() in key:
            return k

    # Не возвращаем слишком технические/общие значения
    banned = ["алматы", "казахстан", "город", "район", "область", "акимат", "улица", "проспект"]
    if key in banned or len(t) < 3:
        return ""

    return t[0].upper() + t[1:]


def _extract_microdistrict_from_text(text: str) -> str:
    """Пытается найти микрорайон в display_name или другом текстовом поле."""
    if not text:
        return ""

    candidates = []
    raw = str(text)

    # Частые шаблоны: 2-й микрорайон, микрорайон Самал-2, мкр. Орбита-1
    regexes = [
        r"(?:микрорайон|мкр\.?|мкр-н)\s*([A-Za-zА-Яа-яЁё0-9\- ]{2,40})",
        r"([A-Za-zА-Яа-яЁё]+\s*[- ]?\d+)\s*(?:микрорайон|мкр\.?)",
        r"(Самал\s*[- ]?[123])",
        r"(Орбита\s*[- ]?[1234])",
        r"(Аксай\s*[- ]?[1-5])",
        r"(Мамыр\s*[- ]?[1-9])",
        r"(Жетысу\s*[- ]?[1-4])",
        r"(Айнабулак\s*[- ]?[1-4])",
        r"(Коктем\s*[- ]?[123]?)",
        r"(Алмагуль|Казахфильм|Таугуль|Жулдыз|Думан|Калкаман|Шанырак|Акбулак|Кокжиек|Шугыла|Нуркент|Сайран)",
    ]

    for rgx in regexes:
        for m in re.finditer(rgx, raw, flags=re.IGNORECASE):
            val = _normalize_microdistrict_name(m.group(1))
            if val:
                candidates.append(val)

    return candidates[0] if candidates else ""


def _extract_microdistrict_from_addr(addr: dict, display_name: str = "", namedetails: dict | None = None) -> tuple[str, str]:
    """Достаёт микрорайон из Nominatim address/namedetails/display_name."""
    namedetails = namedetails or {}

    # Nominatim иногда кладёт микрорайон в разные поля.
    fields_priority = [
        "suburb", "neighbourhood", "quarter", "residential", "city_district",
        "borough", "allotments", "village", "hamlet", "locality"
    ]

    for field in fields_priority:
        value = addr.get(field)
        md = _normalize_microdistrict_name(value)
        if md:
            return md, f"Nominatim: {field}"

    # Иногда микрорайон попадает в road/pedestrian или display name.
    for field in ["road", "pedestrian", "footway", "address29", "address30"]:
        md = _extract_microdistrict_from_text(addr.get(field, ""))
        if md:
            return md, f"Nominatim text: {field}"

    for field in ["name", "name:ru", "official_name", "official_name:ru"]:
        md = _extract_microdistrict_from_text(namedetails.get(field, ""))
        if md:
            return md, f"Nominatim namedetails: {field}"

    md = _extract_microdistrict_from_text(display_name)
    if md:
        return md, "Nominatim display_name"

    return "", ""


def _fallback_microdistrict_by_coordinates(lat: float, lon: float) -> tuple[str, str]:
    """Если Nominatim не дал микрорайон, берём ближайший известный микрорайон по координатам."""
    best_name = ""
    best_dist = 10**9
    best_radius = 0

    for name, c_lat, c_lon, radius in ALMATY_MICRODISTRICT_CENTERS:
        dist = _geo_distance_m(lat, lon, c_lat, c_lon)
        if dist < best_dist:
            best_name = name
            best_dist = dist
            best_radius = radius

    if best_name and best_dist <= best_radius:
        return f"{best_name} (приближённо)", f"Координатный fallback, расстояние до центра ≈ {int(best_dist)} м"

    return "Не определён", "Нет данных в Nominatim и нет близкого fallback-микрорайона"


def get_address(lat: float, lon: float) -> dict:
    """
    Определяет адрес и микрорайон по координатам через Nominatim.
    Улучшенная версия: проверяет suburb/neighbourhood/quarter/display_name/namedetails,
    а если Nominatim не дал микрорайон — использует приближённый fallback по координатам.
    """
    cache = _load_geocode_cache()
    key = f"addr_v2_{_cache_key(lat, lon)}"

    if key in cache:
        return cache[key]

    result = {
        "address": "Точный адрес не найден",
        "street": None,
        "microdistrict": "Не определён",
        "microdistrict_source": "Не определён",
        "raw": {},
    }

    try:
        headers = {"User-Agent": "AlmatyRealEstateApp/1.0 (student project)"}
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "accept-language": "ru",
                "addressdetails": 1,
                "namedetails": 1,
                "extratags": 1,
                "zoom": 18,
            },
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        addr = data.get("address", {}) or {}
        namedetails = data.get("namedetails", {}) or {}
        display_name = data.get("display_name", "") or ""

        # Адрес
        parts = []
        road = addr.get("road") or addr.get("pedestrian") or addr.get("footway") or addr.get("street")
        house = addr.get("house_number")
        if road:
            parts.append(str(road))
        if house:
            parts.append(str(house))

        result["address"] = ", ".join(parts) if parts else (display_name.split(",")[0] if display_name else "Точный адрес не найден")
        result["street"] = road

        # Улучшенный микрорайон
        microdistrict, source = _extract_microdistrict_from_addr(addr, display_name, namedetails)
        if not microdistrict:
            microdistrict, source = _fallback_microdistrict_by_coordinates(lat, lon)

        result["microdistrict"] = microdistrict or "Не определён"
        result["microdistrict_source"] = source or "Не определён"
        result["raw"] = addr

    except requests.RequestException:
        # Если интернет/сервер не ответил, всё равно пробуем fallback по координатам.
        microdistrict, source = _fallback_microdistrict_by_coordinates(lat, lon)
        result["microdistrict"] = microdistrict
        result["microdistrict_source"] = source
    except Exception as e:
        microdistrict, source = _fallback_microdistrict_by_coordinates(lat, lon)
        result["microdistrict"] = microdistrict
        result["microdistrict_source"] = f"Fallback после ошибки: {str(e)}"

    cache[key] = result
    _save_geocode_cache(cache)
    return result


def determine_microdistrict(lat: float, lon: float) -> str:
    """
    Определяет микрорайон по координатам.
    Использует get_address(), потому что там уже есть Nominatim + fallback.
    """
    info = get_address(lat, lon)
    return info.get("microdistrict", "Не определён")


# ============================================================
# Кэш Overpass
# ============================================================
'''

pattern = r"# ============================================================\n# Обратное геокодирование \(Nominatim\)[\s\S]*?# ============================================================\n# Кэш Overpass\n# ============================================================"
geo2, count = re.subn(pattern, new_geocode_block.strip(), geo, count=1)

if count == 0:
    # fallback: replace from def get_address to def _load_osm_cache marker
    pattern2 = r"def get_address\(lat: float, lon: float\)[\s\S]*?(?=def _load_osm_cache)"
    geo2, count = re.subn(pattern2, new_geocode_block + "\n", geo, count=1)

if count == 0:
    raise SystemExit("Не удалось найти блок get_address/determine_microdistrict в src/geo_utils.py")

geo_path.write_text(geo2, encoding="utf-8")
print("OK: src/geo_utils.py improved")

# Patch main.py so it carries microdistrict_source and optionally shows it
main = main_path.read_text(encoding="utf-8", errors="replace")

# GeoWorker: pass source
if 'result["microdistrict_source"] = addr_info.get("microdistrict_source"' not in main:
    main = main.replace(
        'result["microdistrict"] = addr_info.get("microdistrict", "Не определён")',
        'result["microdistrict"] = addr_info.get("microdistrict", "Не определён")\n            result["microdistrict_source"] = addr_info.get("microdistrict_source", "Не определён")',
        1,
    )

# exception fallback
if 'result["microdistrict_source"] = "Ошибка получения адреса"' not in main:
    main = main.replace(
        'result["microdistrict"] = "Не определён"\n\n        try:',
        'result["microdistrict"] = "Не определён"\n            result["microdistrict_source"] = "Ошибка получения адреса"\n\n        try:',
        1,
    )

# _on_geo_result: store source
if 'self.selected_prop["microdistrict_source"] = result.get("microdistrict_source"' not in main:
    main = main.replace(
        'self.selected_prop["microdistrict"] = result.get("microdistrict", "Не определён")',
        'self.selected_prop["microdistrict"] = result.get("microdistrict", "Не определён")\n        self.selected_prop["microdistrict_source"] = result.get("microdistrict_source", "Не определён")',
        1,
    )

# _build_property_html: show source under microdistrict if possible
if "Источник микрорайона" not in main:
    main = main.replace(
        "{row('Микрорайон', microdistrict)}",
        "{row('Микрорайон', microdistrict)}\n{row('Источник микрорайона', p.get('microdistrict_source', '—'))}",
        1,
    )

main_path.write_text(main, encoding="utf-8")
print("OK: main.py patched")

# Clear geocode cache so old 'Не определён' values do not stay
cache_path.parent.mkdir(exist_ok=True)
cache_path.write_text("{}", encoding="utf-8")
print("OK: cache/geocode_cache.json cleared")
print("DONE. Now run: python main.py")
