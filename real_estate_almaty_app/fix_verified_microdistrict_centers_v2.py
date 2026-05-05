# -*- coding: utf-8 -*-
"""
fix_verified_microdistrict_centers_v2.py

Исправляет координаты Жетысу-1/2/3/4.
Запускать из корня проекта:
python fix_verified_microdistrict_centers_v2.py
"""

from pathlib import Path
import re
import shutil

GEO_PATH = Path("src/geo_utils.py")
MAIN_PATH = Path("main.py")

if not GEO_PATH.exists():
    raise FileNotFoundError("Не найден src/geo_utils.py. Запусти файл из корня проекта.")
if not MAIN_PATH.exists():
    raise FileNotFoundError("Не найден main.py. Запусти файл из корня проекта.")

for p in [GEO_PATH, MAIN_PATH]:
    b = p.with_suffix(p.suffix + ".backup_verified_microdistrict_centers_v2")
    if not b.exists():
        shutil.copyfile(p, b)
        print("Backup:", b)

OVERRIDE_CODE = '\n# ============================================================\n# VERIFIED MICRODISTRICT CENTERS PATCH START\n# ============================================================\n\n# Исправленные центры микрорайонов.\n# Главное: Жетысу-1/2/3/4 должны быть в Ауэзовском районе,\n# рядом с Бауыржан Момышулы / Сарыарка, а не севернее.\n_VERIFIED_MICRODISTRICT_CENTERS = {\n    "Жетысу-1": (43.2241, 76.8381, 950),\n    "Жетысу-2": (43.2215, 76.8460, 950),\n    "Жетысу-3": (43.2194, 76.8424, 950),\n    "Жетысу-4": (43.2203, 76.8365, 1050),\n\n    # Варианты написания\n    "Жетысу 1": (43.2241, 76.8381, 950),\n    "Жетысу 2": (43.2215, 76.8460, 950),\n    "Жетысу 3": (43.2194, 76.8424, 950),\n    "Жетысу 4": (43.2203, 76.8365, 1050),\n\n    # Частая опечатка пользователя\n    "Жытысу-1": (43.2241, 76.8381, 950),\n    "Жытысу-2": (43.2215, 76.8460, 950),\n    "Жытысу-3": (43.2194, 76.8424, 950),\n    "Жытысу-4": (43.2203, 76.8365, 1050),\n}\n\ntry:\n    MICRODISTRICT_CENTERS.update(_VERIFIED_MICRODISTRICT_CENTERS)\nexcept Exception:\n    MICRODISTRICT_CENTERS = dict(_VERIFIED_MICRODISTRICT_CENTERS)\n\ntry:\n    for _n in ["Жетысу-1", "Жетысу-2", "Жетысу-3", "Жетысу-4"]:\n        if _n not in ALMATY_MICRODISTRICTS:\n            ALMATY_MICRODISTRICTS.append(_n)\nexcept Exception:\n    ALMATY_MICRODISTRICTS = ["Жетысу-1", "Жетысу-2", "Жетысу-3", "Жетысу-4"]\n\n\ndef _normalize_microdistrict_alias(name: str) -> str:\n    """Нормализация названий: Жетысу 1 / Жытысу-1 -> Жетысу-1."""\n    s = str(name or "").strip()\n    s = s.replace("микрорайон", "").replace("Микрорайон", "")\n    s = s.replace("мкр.", "").replace("мкр", "").strip(" ,.")\n\n    replacements = {\n        "Жетысу 1": "Жетысу-1",\n        "Жетысу 2": "Жетысу-2",\n        "Жетысу 3": "Жетысу-3",\n        "Жетысу 4": "Жетысу-4",\n        "жетысу 1": "Жетысу-1",\n        "жетысу 2": "Жетысу-2",\n        "жетысу 3": "Жетысу-3",\n        "жетысу 4": "Жетысу-4",\n        "Жытысу-1": "Жетысу-1",\n        "Жытысу-2": "Жетысу-2",\n        "Жытысу-3": "Жетысу-3",\n        "Жытысу-4": "Жетысу-4",\n        "Жытысу 1": "Жетысу-1",\n        "Жытысу 2": "Жетысу-2",\n        "Жытысу 3": "Жетысу-3",\n        "Жытысу 4": "Жетысу-4",\n    }\n    return replacements.get(s, s)\n\n\ndef get_microdistrict_center(name: str):\n    """\n    Центр микрорайона для фильтра карты.\n    Эта версия берёт исправленные координаты Жетысу-1/2/3/4.\n    """\n    name = _normalize_microdistrict_alias(name)\n\n    try:\n        center = MICRODISTRICT_CENTERS.get(name)\n        if center:\n            return center\n    except Exception:\n        pass\n\n    try:\n        geojson = _load_microdistrict_geojson()\n        if geojson:\n            for feature in geojson.get("features", []):\n                fname = _microdistrict_feature_name(feature)\n                if _normalize_microdistrict_alias(fname) == name:\n                    c = _feature_center_and_radius(feature)\n                    if c:\n                        return c\n    except Exception:\n        pass\n\n    return None\n\n\ndef determine_microdistrict(lat: float, lon: float, address_text: str = "") -> str:\n    """\n    Определение микрорайона с исправленными координатами Жетысу.\n    Порядок:\n    1) ищет микрорайон в адресе;\n    2) если есть geo/microdistricts.geojson — ищет по полигону;\n    3) иначе выбирает ближайший центр.\n    """\n    unknown = "Не определён"\n    try:\n        unknown = MICRODISTRICT_UNKNOWN\n    except Exception:\n        pass\n\n    try:\n        found = extract_microdistrict_from_text(address_text)\n        found = _normalize_microdistrict_alias(found)\n        if found:\n            return found\n    except Exception:\n        pass\n\n    try:\n        lat = float(lat)\n        lon = float(lon)\n    except Exception:\n        return unknown\n\n    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):\n        return unknown\n\n    try:\n        found_geo = determine_microdistrict_from_geojson(lat, lon)\n        found_geo = _normalize_microdistrict_alias(found_geo)\n        if found_geo:\n            return found_geo\n    except Exception:\n        pass\n\n    best_name = ""\n    best_dist = 10**18\n\n    try:\n        centers = MICRODISTRICT_CENTERS\n    except Exception:\n        centers = _VERIFIED_MICRODISTRICT_CENTERS\n\n    for name, data in centers.items():\n        try:\n            clat, clon, _radius = data\n            try:\n                dist = haversine_distance(lat, lon, clat, clon)\n            except Exception:\n                dlat = (lat - clat) * 111000.0\n                dlon = (lon - clon) * 81000.0\n                dist = (dlat * dlat + dlon * dlon) ** 0.5\n\n            if dist < best_dist:\n                best_dist = dist\n                best_name = _normalize_microdistrict_alias(name)\n        except Exception:\n            continue\n\n    return best_name or unknown\n\n# ============================================================\n# VERIFIED MICRODISTRICT CENTERS PATCH END\n# ============================================================\n'

geo = GEO_PATH.read_text(encoding="utf-8", errors="replace")

geo = re.sub(
    r"\n# ============================================================\n# VERIFIED MICRODISTRICT CENTERS PATCH START[\s\S]*?# VERIFIED MICRODISTRICT CENTERS PATCH END\n# ============================================================\n",
    "\n",
    geo,
    count=1,
)

geo = geo.rstrip() + "\n\n" + OVERRIDE_CODE.strip() + "\n"
GEO_PATH.write_text(geo, encoding="utf-8")
print("OK: src/geo_utils.py updated with corrected Жетысу-1/2/3/4 centers")

for cache_file in ["cache/geocode_cache.json", "cache/osm_cache.json"]:
    p = Path(cache_file)
    if p.exists():
        p.write_text("{}", encoding="utf-8")
        print("Cleared:", p)

print("DONE. Now run: python main.py")
