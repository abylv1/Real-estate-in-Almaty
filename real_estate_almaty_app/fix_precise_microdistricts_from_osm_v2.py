# -*- coding: utf-8 -*-
"""
fix_precise_microdistricts_from_osm_v2.py

Исправленная версия. Не содержит ошибки GEO_OVERRIDE = r.
Также восстанавливает отсутствующий метод _update_ai_context_panel.
"""

from pathlib import Path
import json
import math
import re
import shutil
import time
import urllib.parse
import urllib.request

ROOT = Path(".")
MAIN_PATH = ROOT / "main.py"
GEO_UTILS_PATH = ROOT / "src" / "geo_utils.py"
GEO_DIR = ROOT / "geo"
CENTERS_JSON = GEO_DIR / "microdistrict_centers_osm.json"
GENERATED_GEOJSON = GEO_DIR / "microdistricts_osm_generated.geojson"

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти файл из корня проекта.")
if not GEO_UTILS_PATH.exists():
    raise FileNotFoundError("src/geo_utils.py не найден.")

GEO_DIR.mkdir(exist_ok=True)

for p in [MAIN_PATH, GEO_UTILS_PATH]:
    b = p.with_suffix(p.suffix + ".backup_precise_microdistricts_osm_v2")
    if not b.exists():
        shutil.copyfile(p, b)
        print("Backup:", b)

GEO_OVERRIDE = "\n# ============================================================\n# OSM PRECISE MICRODISTRICT CENTERS OVERRIDE START\n# ============================================================\n\nimport json as _precise_json\nfrom pathlib import Path as _PrecisePath\n\n_OSM_MICRO_CENTERS_FILE = _PrecisePath(\"geo/microdistrict_centers_osm.json\")\n_OSM_MICRO_GEOJSON_FILES = [\n    \"geo/microdistricts.geojson\",\n    \"geo/microdistricts_osm_generated.geojson\",\n    \"geo/almaty_microdistricts.geojson\",\n]\n\ntry:\n    MICRODISTRICT_UNKNOWN\nexcept NameError:\n    MICRODISTRICT_UNKNOWN = \"Не определён\"\n\ntry:\n    MICRODISTRICT_CENTERS\nexcept NameError:\n    MICRODISTRICT_CENTERS = {}\n\ntry:\n    ALMATY_MICRODISTRICTS\nexcept NameError:\n    ALMATY_MICRODISTRICTS = []\n\n\ndef _md_alias(name: str) -> str:\n    s = str(name or \"\").strip()\n    s = s.replace(\"микрорайон\", \"\").replace(\"Микрорайон\", \"\")\n    s = s.replace(\"мкр.\", \"\").replace(\"мкр\", \"\").strip(\" ,.\")\n    s = s.replace(\"Жытысу\", \"Жетысу\")\n    aliases = {\n        \"Жетысу 1\": \"Жетысу-1\", \"Жетысу 2\": \"Жетысу-2\",\n        \"Жетысу 3\": \"Жетысу-3\", \"Жетысу 4\": \"Жетысу-4\",\n        \"жетысу 1\": \"Жетысу-1\", \"жетысу 2\": \"Жетысу-2\",\n        \"жетысу 3\": \"Жетысу-3\", \"жетысу 4\": \"Жетысу-4\",\n        \"Самал 1\": \"Самал-1\", \"Самал 2\": \"Самал-2\", \"Самал 3\": \"Самал-3\",\n        \"Орбита 1\": \"Орбита-1\", \"Орбита 2\": \"Орбита-2\",\n        \"Орбита 3\": \"Орбита-3\", \"Орбита 4\": \"Орбита-4\",\n        \"Аксай 1\": \"Аксай-1\", \"Аксай 2\": \"Аксай-2\", \"Аксай 3\": \"Аксай-3\",\n        \"Аксай 4\": \"Аксай-4\", \"Аксай 5\": \"Аксай-5\",\n        \"Мамыр 1\": \"Мамыр-1\", \"Мамыр 2\": \"Мамыр-2\", \"Мамыр 3\": \"Мамыр-3\",\n        \"Мамыр 4\": \"Мамыр-4\", \"Мамыр 5\": \"Мамыр-5\", \"Мамыр 6\": \"Мамыр-6\", \"Мамыр 7\": \"Мамыр-7\",\n        \"Айнабулак 1\": \"Айнабулак-1\", \"Айнабулак 2\": \"Айнабулак-2\",\n        \"Айнабулак 3\": \"Айнабулак-3\", \"Айнабулак 4\": \"Айнабулак-4\",\n    }\n    return aliases.get(s, s)\n\n\ndef _load_osm_micro_centers():\n    if not _OSM_MICRO_CENTERS_FILE.exists():\n        return {}\n    try:\n        data = _precise_json.loads(_OSM_MICRO_CENTERS_FILE.read_text(encoding=\"utf-8\"))\n        out = {}\n        for name, v in data.items():\n            try:\n                out[_md_alias(name)] = (\n                    float(v[\"lat\"]),\n                    float(v[\"lon\"]),\n                    float(v.get(\"radius_m\", 1200)),\n                )\n            except Exception:\n                continue\n        return out\n    except Exception:\n        return {}\n\n\ndef _load_microdistrict_geojson():\n    for file_name in _OSM_MICRO_GEOJSON_FILES:\n        p = _PrecisePath(file_name)\n        if p.exists():\n            for enc in [\"utf-8\", \"utf-8-sig\"]:\n                try:\n                    with open(p, \"r\", encoding=enc) as f:\n                        return _precise_json.load(f)\n                except Exception:\n                    pass\n    return None\n\n\ndef get_all_microdistricts() -> list:\n    names = set()\n    try:\n        names.update([_md_alias(x) for x in ALMATY_MICRODISTRICTS])\n    except Exception:\n        pass\n    names.update(_load_osm_micro_centers().keys())\n    try:\n        names.update([_md_alias(x) for x in MICRODISTRICT_CENTERS.keys()])\n    except Exception:\n        pass\n    return sorted([x for x in names if x])\n\n\ndef get_microdistrict_center(name: str):\n    name = _md_alias(name)\n\n    precise = _load_osm_micro_centers()\n    if name in precise:\n        return precise[name]\n\n    try:\n        geojson = _load_microdistrict_geojson()\n        if geojson:\n            for feature in geojson.get(\"features\", []):\n                fname = _md_alias(_microdistrict_feature_name(feature))\n                if fname == name:\n                    try:\n                        if feature.get(\"geometry\", {}).get(\"type\") == \"Point\":\n                            lon, lat = feature[\"geometry\"][\"coordinates\"][:2]\n                            return (float(lat), float(lon), 1200)\n                    except Exception:\n                        pass\n                    center = _feature_center_and_radius(feature)\n                    if center:\n                        return center\n    except Exception:\n        pass\n\n    try:\n        return MICRODISTRICT_CENTERS.get(name)\n    except Exception:\n        return None\n\n\ndef _nearest_microdistrict_precise(lat: float, lon: float) -> str:\n    all_centers = {}\n    try:\n        all_centers.update(MICRODISTRICT_CENTERS)\n    except Exception:\n        pass\n    all_centers.update(_load_osm_micro_centers())\n\n    best_name = \"\"\n    best_dist = 10**18\n\n    for name, data in all_centers.items():\n        try:\n            clat, clon, _radius = data\n            try:\n                dist = haversine_distance(lat, lon, clat, clon)\n            except Exception:\n                dlat = (lat - clat) * 111000.0\n                dlon = (lon - clon) * 81000.0\n                dist = (dlat * dlat + dlon * dlon) ** 0.5\n            if dist < best_dist:\n                best_dist = dist\n                best_name = _md_alias(name)\n        except Exception:\n            continue\n\n    return best_name or \"Не определён\"\n\n\ndef determine_microdistrict(lat: float, lon: float, address_text: str = \"\") -> str:\n    try:\n        found = _md_alias(extract_microdistrict_from_text(address_text))\n        if found:\n            return found\n    except Exception:\n        pass\n\n    try:\n        lat = float(lat)\n        lon = float(lon)\n    except Exception:\n        return \"Не определён\"\n\n    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):\n        return \"Не определён\"\n\n    try:\n        found_geo = determine_microdistrict_from_geojson(lat, lon)\n        found_geo = _md_alias(found_geo)\n        if found_geo:\n            return found_geo\n    except Exception:\n        pass\n\n    return _nearest_microdistrict_precise(lat, lon)\n\n# ============================================================\n# OSM PRECISE MICRODISTRICT CENTERS OVERRIDE END\n# ============================================================\n"
AI_CONTEXT_METHOD = "\n    def _update_ai_context_panel(self):\n        \"\"\"Safe AI context updater. Prevents AttributeError after geocoding updates.\"\"\"\n        if not hasattr(self, \"ai_context_label\"):\n            return\n\n        prop = getattr(self, \"selected_prop\", None)\n        if not prop:\n            self.ai_context_label.setText(\"Сначала выберите объект на карте\")\n            return\n\n        try:\n            micro = str(prop.get(\"microdistrict\", \"\")).strip()\n            if (not micro) or micro in [\"Не определён\", \"None\", \"nan\"]:\n                lat = prop.get(\"lat_raw\") or prop.get(\"map_lat\") or prop.get(\"latitude\") or prop.get(\"lat\")\n                lon = prop.get(\"lon_raw\") or prop.get(\"map_lon\") or prop.get(\"longitude\") or prop.get(\"lon\")\n                address_text = \" \".join([\n                    str(prop.get(\"address\", \"\")),\n                    str(prop.get(\"location\", \"\")),\n                    str(prop.get(\"title\", \"\")),\n                    str(prop.get(\"complex_name\", \"\")),\n                ])\n                micro = determine_microdistrict(lat, lon, address_text)\n                prop[\"microdistrict\"] = micro\n        except Exception:\n            micro = str(prop.get(\"microdistrict\", \"Не определён\"))\n\n        district = str(prop.get(\"district\", \"Не определён\"))\n        price = prop.get(\"price_mln\", prop.get(\"price\", \"\"))\n        ppm2 = prop.get(\"price_per_m2\", prop.get(\"price_m2\", \"\"))\n\n        parts = [\n            f\"Выбран объект: район — {district}\",\n            f\"микрорайон — {micro or 'Не определён'}\",\n        ]\n\n        if price not in [\"\", None]:\n            parts.append(f\"цена — {price}\")\n        if ppm2 not in [\"\", None]:\n            parts.append(f\"цена за м² — {ppm2}\")\n\n        self.ai_context_label.setText(\" | \".join(parts))\n"

MICRODISTRICTS = [
    "Аксай-1", "Аксай-2", "Аксай-3", "Аксай-4", "Аксай-5",
    "Айнабулак-1", "Айнабулак-2", "Айнабулак-3", "Айнабулак-4",
    "Алатау", "Алмагуль", "Алтын Бесик", "Алгабас", "Алгабас-1", "Алгабас-6",
    "Акбулак", "Акбулак-1", "Акбулак-2", "Баганашыл", "Горный Гигант",
    "Думан", "Думан-1", "Думан-2", "Ерменсай", "Жас Канат",
    "Жетысу-1", "Жетысу-2", "Жетысу-3", "Жетысу-4",
    "Жулдыз-1", "Жулдыз-2", "Зердели", "Казахфильм", "Кайрат",
    "Калкаман-1", "Калкаман-2", "Каменка", "Карагайлы",
    "Кокжиек", "Коктем-1", "Коктем-2", "Коктем-3",
    "Кулагер", "Курылысшы", "Мамыр-1", "Мамыр-2", "Мамыр-3", "Мамыр-4",
    "Мамыр-5", "Мамыр-6", "Мамыр-7", "Мирас", "Нур Алатау", "Нуркент",
    "Орбита-1", "Орбита-2", "Орбита-3", "Орбита-4", "Рахат", "Сайран",
    "Самал-1", "Самал-2", "Самал-3", "Саялы",
    "Таугуль-1", "Таугуль-2", "Таугуль-3", "Таусамалы",
    "Тастак-1", "Тастак-2", "Тастак-3", "Улжан-1", "Улжан-2",
    "Шанырак-1", "Шанырак-2", "Шугыла",
    "Золотой квадрат", "Арбат", "Центр",
]

VERIFIED_FALLBACKS = {
    "Жетысу-1": (43.2241, 76.8381, 950, "verified_fallback"),
    "Жетысу-2": (43.2215, 76.8460, 950, "verified_fallback"),
    "Жетысу-3": (43.2194, 76.8424, 950, "verified_fallback"),
    "Жетысу-4": (43.2203, 76.8365, 1050, "verified_fallback"),
    "Золотой квадрат": (43.2550, 76.9450, 1600, "verified_fallback"),
    "Арбат": (43.2620, 76.9400, 1200, "verified_fallback"),
    "Центр": (43.2500, 76.9300, 1800, "verified_fallback"),
}

def norm_name(name: str) -> str:
    s = str(name or "").strip()
    s = s.replace("микрорайон", "").replace("Микрорайон", "")
    s = s.replace("мкр.", "").replace("мкр", "").strip(" ,.")
    s = s.replace("Жытысу", "Жетысу")
    pairs = {
        "Жетысу 1": "Жетысу-1", "Жетысу 2": "Жетысу-2",
        "Жетысу 3": "Жетысу-3", "Жетысу 4": "Жетысу-4",
        "Самал 1": "Самал-1", "Самал 2": "Самал-2", "Самал 3": "Самал-3",
        "Орбита 1": "Орбита-1", "Орбита 2": "Орбита-2", "Орбита 3": "Орбита-3", "Орбита 4": "Орбита-4",
    }
    return pairs.get(s, s)

def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1-a))

def bbox_radius(lat, lon, bbox):
    try:
        south, north, west, east = [float(x) for x in bbox]
        corners = [(south, west), (south, east), (north, west), (north, east)]
        radius = max(haversine(lat, lon, a, b) for a, b in corners)
        return max(650, min(radius, 3500))
    except Exception:
        return 1200

def result_score(name, result):
    display = str(result.get("display_name", "")).lower()
    typ = str(result.get("type", "")).lower()
    cls = str(result.get("class", "")).lower()
    score = 0
    name_low = name.lower()
    compact_name = name_low.replace("-", " ")

    if "алматы" in display or "almaty" in display:
        score += 6
    else:
        score -= 100

    if name_low in display or compact_name in display:
        score += 12

    digits = "".join(ch for ch in name if ch.isdigit())
    if digits:
        if digits in display:
            score += 4
        else:
            score -= 15

    if cls == "place":
        score += 4
    if typ in ["neighbourhood", "quarter", "suburb", "residential", "city_block"]:
        score += 6
    if typ in ["administrative", "district"] and any(ch.isdigit() for ch in name):
        score -= 8

    if result.get("boundingbox"):
        score += 2
    if result.get("geojson"):
        score += 2
    return score

def nominatim_search(name):
    queries = [
        f"{name}, микрорайон, Алматы, Казахстан",
        f"мкр {name}, Алматы, Казахстан",
        f"{name}, Almaty, Kazakhstan",
    ]
    headers = {
        "User-Agent": "real-estate-almaty-student-app/1.0",
        "Accept-Language": "ru",
    }
    best = None
    best_score = -10**9

    for q in queries:
        params = urllib.parse.urlencode({
            "q": q,
            "format": "jsonv2",
            "polygon_geojson": 1,
            "addressdetails": 1,
            "limit": 5,
            "accept-language": "ru",
        })
        url = "https://nominatim.openstreetmap.org/search?" + params
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as e:
            print(f"  ! Nominatim error for {name}: {e}")
            data = []

        for r in data:
            try:
                lat = float(r.get("lat"))
                lon = float(r.get("lon"))
            except Exception:
                continue
            if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):
                continue
            sc = result_score(name, r)
            if sc > best_score:
                best_score = sc
                best = r

        if best and best_score >= 10:
            break
        time.sleep(1.05)
    return best, best_score

def make_feature(name, result, center):
    geojson = result.get("geojson") if result else None
    props = {
        "name": name,
        "source": center.get("source", "unknown"),
        "display_name": center.get("display_name", ""),
    }
    if geojson and geojson.get("type") in ["Polygon", "MultiPolygon"]:
        return {"type": "Feature", "properties": props, "geometry": geojson}
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "Point", "coordinates": [center["lon"], center["lat"]]},
    }

def fetch_centers():
    centers = {}
    features = []
    print("Fetching microdistrict coordinates from OSM/Nominatim...")
    print("This can take 1-3 minutes.")

    for i, raw_name in enumerate(MICRODISTRICTS, start=1):
        name = norm_name(raw_name)
        print(f"[{i}/{len(MICRODISTRICTS)}] {name}")
        result, score = nominatim_search(name)

        if result and score >= 5:
            lat = float(result["lat"])
            lon = float(result["lon"])
            radius = bbox_radius(lat, lon, result.get("boundingbox"))
            center = {
                "lat": lat, "lon": lon, "radius_m": radius,
                "source": "nominatim", "score": score,
                "display_name": result.get("display_name", ""),
                "class": result.get("class", ""),
                "type": result.get("type", ""),
            }
            centers[name] = center
            features.append(make_feature(name, result, center))
            print(f"  OK: {lat:.6f}, {lon:.6f} | {result.get('type')} | score={score}")
        elif name in VERIFIED_FALLBACKS:
            lat, lon, radius, source = VERIFIED_FALLBACKS[name]
            center = {
                "lat": lat, "lon": lon, "radius_m": radius,
                "source": source, "score": score,
                "display_name": "manual verified fallback",
            }
            centers[name] = center
            features.append(make_feature(name, {}, center))
            print(f"  fallback: {lat:.6f}, {lon:.6f}")
        else:
            print("  not found; old fallback will be used")

        time.sleep(1.05)

    CENTERS_JSON.write_text(json.dumps(centers, ensure_ascii=False, indent=2), encoding="utf-8")
    GENERATED_GEOJSON.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": features,
        "properties": {"source": "Nominatim / OpenStreetMap generated"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved:", CENTERS_JSON)
    print("Saved:", GENERATED_GEOJSON)
    print("Fetched centers:", len(centers))

fetch_centers()

# Patch geo_utils.py
geo = GEO_UTILS_PATH.read_text(encoding="utf-8", errors="replace")
geo = re.sub(
    r"\n# ============================================================\n# OSM PRECISE MICRODISTRICT CENTERS OVERRIDE START[\s\S]*?# OSM PRECISE MICRODISTRICT CENTERS OVERRIDE END\n# ============================================================\n",
    "\n",
    geo,
    count=1,
)
geo = geo.rstrip() + "\n\n" + GEO_OVERRIDE.strip() + "\n"
GEO_UTILS_PATH.write_text(geo, encoding="utf-8")
print("OK: src/geo_utils.py patched")

# Patch main.py
main = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

def ensure_import(source, name):
    pat = r"from src\.geo_utils import \(([\s\S]*?)\)"
    m = re.search(pat, source)
    if m:
        inside = m.group(1)
        if name not in inside:
            source = source[:m.start(1)] + "    " + name + ",\n" + inside + source[m.end(1):]
            print("OK: imported", name)
        return source
    pat2 = r"from src\.geo_utils import ([^\n]+)"
    m2 = re.search(pat2, source)
    if m2:
        names = [x.strip() for x in m2.group(1).split(",")]
        if name not in names:
            names.append(name)
            source = source[:m2.start(1)] + ", ".join(names) + source[m2.end(1):]
            print("OK: imported", name)
        return source
    return "from src.geo_utils import " + name + "\n" + source

for nm in ["determine_microdistrict", "get_all_microdistricts", "get_microdistrict_center"]:
    main = ensure_import(main, nm)

# Add missing _update_ai_context_panel
def method_bounds(source, method_name):
    matches = list(re.finditer(rf"(?m)^    def {re.escape(method_name)}\s*\(", source))
    bounds = []
    for m in matches:
        next_m = re.search(r"(?m)^    def \w+\s*\(", source[m.end():])
        end = m.end() + next_m.start() if next_m else len(source)
        bounds.append((m.start(), end))
    return bounds

if "def _update_ai_context_panel" not in main:
    marker = "\n    def _on_geo_result"
    if marker in main:
        main = main.replace(marker, "\n" + AI_CONTEXT_METHOD.rstrip() + "\n" + marker, 1)
        print("OK: added missing _update_ai_context_panel before _on_geo_result")
    else:
        # fallback before closeEvent or at end of class methods
        marker = "\n    def closeEvent"
        if marker in main:
            main = main.replace(marker, "\n" + AI_CONTEXT_METHOD.rstrip() + "\n" + marker, 1)
            print("OK: added missing _update_ai_context_panel before closeEvent")
        else:
            print("WARNING: could not insert _update_ai_context_panel")
else:
    print("OK: _update_ai_context_panel already exists")

MAIN_PATH.write_text(main, encoding="utf-8")

for cache_file in ["cache/geocode_cache.json", "cache/osm_cache.json"]:
    p = Path(cache_file)
    if p.exists():
        p.write_text("{}", encoding="utf-8")
        print("Cleared:", p)

print("DONE.")
print("Run: python main.py")
