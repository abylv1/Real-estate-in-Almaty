
# -*- coding: utf-8 -*-
from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")
GEO_PATH = Path("src/geo_utils.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py not found. Run this file from project root.")
if not GEO_PATH.exists():
    raise FileNotFoundError("src/geo_utils.py not found.")

for p in [MAIN_PATH, GEO_PATH]:
    backup = p.with_suffix(p.suffix + ".backup_microdistrict_geojson")
    if not backup.exists():
        shutil.copyfile(p, backup)
        print("Backup:", backup)

GEO_BLOCK = "\n# ============================================================\n# MICRODISTRICT GEOJSON / ACCURATE COORDINATES PATCH START\n# ============================================================\n\n# Самая правильная логика микрорайонов:\n# - микрорайон — это НЕ одна точка, а территория/полигон;\n# - если есть geo/microdistricts.geojson, программа определяет микрорайон по полигону;\n# - если GeoJSON нет, программа использует приблизительные центры.\n\nimport json as _json\nfrom pathlib import Path as _Path\n\nMICRODISTRICT_GEOJSON_FILES = [\n    \"geo/microdistricts.geojson\",\n    \"geo/almaty_microdistricts.geojson\",\n    \"geo/almaty_microdistricts.json\",\n]\n\ntry:\n    MICRODISTRICT_UNKNOWN\nexcept NameError:\n    MICRODISTRICT_UNKNOWN = \"Не определён\"\n\ntry:\n    ALMATY_MICRODISTRICTS\nexcept NameError:\n    ALMATY_MICRODISTRICTS = []\n\ntry:\n    MICRODISTRICT_CENTERS\nexcept NameError:\n    MICRODISTRICT_CENTERS = {}\n\n\ndef _md_norm_name(value: str) -> str:\n    if value is None:\n        return \"\"\n    s = str(value).strip()\n    for x in [\"микрорайон\", \"Микрорайон\", \"мкр.\", \"мкр\", \"МКР.\", \"МКР\"]:\n        s = s.replace(x, \"\")\n    return s.replace(\"  \", \" \").strip(\" ,.-\")\n\n\ndef _load_microdistrict_geojson():\n    for file_name in MICRODISTRICT_GEOJSON_FILES:\n        p = _Path(file_name)\n        if p.exists():\n            for enc in [\"utf-8\", \"utf-8-sig\"]:\n                try:\n                    with open(p, \"r\", encoding=enc) as f:\n                        return _json.load(f)\n                except Exception:\n                    pass\n    return None\n\n\ndef _microdistrict_feature_name(feature: dict) -> str:\n    props = feature.get(\"properties\", {}) or {}\n    keys = [\n        \"microdistrict\", \"microdistrict_ru\", \"name\", \"name_ru\", \"name:ru\",\n        \"NAME\", \"Name\", \"title\", \"TITLE\", \"mkr\", \"МКР\", \"district_name\"\n    ]\n    for key in keys:\n        if props.get(key):\n            return _md_norm_name(props.get(key))\n    return \"\"\n\n\ndef _point_in_ring(lon: float, lat: float, ring: list) -> bool:\n    inside = False\n    if len(ring) < 3:\n        return False\n\n    j = len(ring) - 1\n    for i in range(len(ring)):\n        xi, yi = ring[i][0], ring[i][1]\n        xj, yj = ring[j][0], ring[j][1]\n        if ((yi > lat) != (yj > lat)):\n            x_intersect = (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi\n            if lon < x_intersect:\n                inside = not inside\n        j = i\n\n    return inside\n\n\ndef _point_in_geometry(lat: float, lon: float, geom: dict) -> bool:\n    if not geom:\n        return False\n\n    gtype = geom.get(\"type\")\n    coords = geom.get(\"coordinates\", [])\n\n    if gtype == \"Polygon\":\n        if not coords:\n            return False\n        if not _point_in_ring(lon, lat, coords[0]):\n            return False\n        for hole in coords[1:]:\n            if _point_in_ring(lon, lat, hole):\n                return False\n        return True\n\n    if gtype == \"MultiPolygon\":\n        for poly in coords:\n            if not poly:\n                continue\n            if _point_in_ring(lon, lat, poly[0]):\n                in_hole = False\n                for hole in poly[1:]:\n                    if _point_in_ring(lon, lat, hole):\n                        in_hole = True\n                        break\n                if not in_hole:\n                    return True\n        return False\n\n    return False\n\n\ndef _iter_geojson_points(geom: dict):\n    if not geom:\n        return\n    gtype = geom.get(\"type\")\n    coords = geom.get(\"coordinates\", [])\n\n    if gtype == \"Polygon\":\n        for ring in coords:\n            for point in ring:\n                yield float(point[1]), float(point[0])\n\n    elif gtype == \"MultiPolygon\":\n        for poly in coords:\n            for ring in poly:\n                for point in ring:\n                    yield float(point[1]), float(point[0])\n\n\ndef _feature_center_and_radius(feature: dict):\n    pts = list(_iter_geojson_points(feature.get(\"geometry\", {})))\n    if not pts:\n        return None\n\n    clat = sum(p[0] for p in pts) / len(pts)\n    clon = sum(p[1] for p in pts) / len(pts)\n\n    max_dist = 0\n    for lat, lon in pts:\n        try:\n            d = haversine_distance(clat, clon, lat, lon)\n        except Exception:\n            dlat = (lat - clat) * 111000.0\n            dlon = (lon - clon) * 81000.0\n            d = (dlat * dlat + dlon * dlon) ** 0.5\n        max_dist = max(max_dist, d)\n\n    return (clat, clon, max(800, min(max_dist, 3500)))\n\n\ndef determine_microdistrict_from_geojson(lat: float, lon: float) -> str:\n    geojson = _load_microdistrict_geojson()\n    if not geojson:\n        return \"\"\n\n    for feature in geojson.get(\"features\", []):\n        name = _microdistrict_feature_name(feature)\n        if name and _point_in_geometry(float(lat), float(lon), feature.get(\"geometry\", {})):\n            return name\n\n    return \"\"\n\n\ndef get_microdistrict_center(name: str):\n    name = _md_norm_name(name)\n\n    geojson = _load_microdistrict_geojson()\n    if geojson:\n        for feature in geojson.get(\"features\", []):\n            fname = _microdistrict_feature_name(feature)\n            if fname == name:\n                center = _feature_center_and_radius(feature)\n                if center:\n                    return center\n\n    try:\n        return MICRODISTRICT_CENTERS.get(name)\n    except Exception:\n        return None\n\n\ndef determine_microdistrict(lat: float, lon: float, address_text: str = \"\") -> str:\n    # 1. Try address text\n    try:\n        found = extract_microdistrict_from_text(address_text)\n        if found:\n            return found\n    except Exception:\n        pass\n\n    try:\n        lat = float(lat)\n        lon = float(lon)\n    except Exception:\n        return MICRODISTRICT_UNKNOWN\n\n    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):\n        return MICRODISTRICT_UNKNOWN\n\n    # 2. Exact polygon if GeoJSON exists\n    found_geo = determine_microdistrict_from_geojson(lat, lon)\n    if found_geo:\n        return found_geo\n\n    # 3. Fallback by nearest center\n    best_name = \"\"\n    best_dist = 10**9\n    best_radius = 0\n\n    for name, data in MICRODISTRICT_CENTERS.items():\n        try:\n            clat, clon, radius = data\n        except Exception:\n            continue\n\n        try:\n            dist = haversine_distance(lat, lon, clat, clon)\n        except Exception:\n            dlat = (lat - clat) * 111000.0\n            dlon = (lon - clon) * 81000.0\n            dist = (dlat * dlat + dlon * dlon) ** 0.5\n\n        if dist < best_dist:\n            best_dist = dist\n            best_name = name\n            best_radius = radius\n\n    if best_name and best_dist <= max(float(best_radius or 0), 1400.0):\n        return best_name\n\n    return MICRODISTRICT_UNKNOWN\n\n# ============================================================\n# MICRODISTRICT GEOJSON / ACCURATE COORDINATES PATCH END\n# ============================================================\n"
SMART_METHOD = "    def _filter_by_microdistrict_smart(self, df, micro_name):\n        \"\"\"\n        Smart microdistrict filter.\n\n        If geo/microdistricts.geojson exists, determine_microdistrict() uses real polygons.\n        If not, it uses approximate centers.\n        \"\"\"\n        if df is None or len(df) == 0:\n            return df\n\n        micro_name = str(micro_name).strip()\n        if not micro_name or micro_name == \"Все микрорайоны\":\n            return df\n\n        lat_col = \"map_lat\" if \"map_lat\" in df.columns else \"latitude\"\n        lon_col = \"map_lon\" if \"map_lon\" in df.columns else \"longitude\"\n\n        temp = df.copy()\n\n        if lat_col in temp.columns and lon_col in temp.columns:\n            temp[\"microdistrict\"] = temp.apply(\n                lambda r: determine_microdistrict(\n                    r.get(lat_col, 0),\n                    r.get(lon_col, 0),\n                    str(r.get(\"address\", \"\")) + \" \" + str(r.get(\"location\", \"\")) + \" \" + str(r.get(\"title\", \"\"))\n                ),\n                axis=1\n            )\n\n        if \"microdistrict\" in temp.columns:\n            exact = temp[temp[\"microdistrict\"].astype(str).str.strip() == micro_name].copy()\n            if len(exact) > 0:\n                return exact\n\n        center = None\n        try:\n            center = get_microdistrict_center(micro_name)\n        except Exception:\n            center = None\n\n        if center and lat_col in temp.columns and lon_col in temp.columns:\n            clat, clon, radius = center\n            radius = max(float(radius or 0), 1400.0)\n\n            dlat = (temp[lat_col].astype(float) - float(clat)) * 111000.0\n            dlon = (temp[lon_col].astype(float) - float(clon)) * 81000.0\n            temp[\"_micro_dist\"] = (dlat * dlat + dlon * dlon) ** 0.5\n\n            near = temp[temp[\"_micro_dist\"] <= radius].copy()\n            if \"_micro_dist\" in near.columns:\n                near = near.drop(columns=[\"_micro_dist\"])\n            return near\n\n        return temp.iloc[0:0].copy()\n\n"

# Patch geo_utils.py
geo = GEO_PATH.read_text(encoding="utf-8", errors="replace")
geo = re.sub(
    r"\n# ============================================================\n# MICRODISTRICT GEOJSON / ACCURATE COORDINATES PATCH START[\s\S]*?# MICRODISTRICT GEOJSON / ACCURATE COORDINATES PATCH END\n# ============================================================\n",
    "\n",
    geo,
    count=1,
)
geo = geo.rstrip() + "\n\n" + GEO_BLOCK.strip() + "\n"
GEO_PATH.write_text(geo, encoding="utf-8")
print("OK: src/geo_utils.py supports GeoJSON microdistrict boundaries")

# Patch main.py
text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

def ensure_geo_import(source, name):
    pattern = r"from src\.geo_utils import \(([\s\S]*?)\)"
    m = re.search(pattern, source)
    if m:
        inside = m.group(1)
        if name not in inside:
            source = source[:m.start(1)] + "    " + name + ",\n" + inside + source[m.end(1):]
            print("OK: imported", name)
        return source

    pattern2 = r"from src\.geo_utils import ([^\n]+)"
    m2 = re.search(pattern2, source)
    if m2:
        names = [x.strip() for x in m2.group(1).split(",")]
        if name not in names:
            names.append(name)
            source = source[:m2.start(1)] + ", ".join(names) + source[m2.end(1):]
            print("OK: imported", name)
        return source

    source = "from src.geo_utils import " + name + "\n" + source
    print("OK: added import", name)
    return source

for name in ["determine_microdistrict", "get_microdistrict_center"]:
    text = ensure_geo_import(text, name)

def method_bounds(source, method_name):
    matches = list(re.finditer(rf"(?m)^    def {re.escape(method_name)}\s*\(", source))
    bounds = []
    for m in matches:
        next_m = re.search(r"(?m)^    def \w+\s*\(", source[m.end():])
        end = m.end() + next_m.start() if next_m else len(source)
        bounds.append((m.start(), end))
    return bounds

bounds = method_bounds(text, "_filter_by_microdistrict_smart")
if bounds:
    insert_at = bounds[0][0]
    for start, end in reversed(bounds):
        text = text[:start] + text[end:]
    text = text[:insert_at] + SMART_METHOD.rstrip() + "\n" + text[insert_at:]
    print("OK: replaced _filter_by_microdistrict_smart")
else:
    marker = "\n    def _apply_filters"
    if marker in text:
        text = text.replace(marker, "\n" + SMART_METHOD.rstrip() + "\n" + marker, 1)
        print("OK: added _filter_by_microdistrict_smart")
    else:
        print("WARNING: cannot find _apply_filters")

# Make exact old microdistrict filter call smart helper
text = text.replace(
    'df = df[df["microdistrict"].astype(str) == micro]',
    'df = self._filter_by_microdistrict_smart(df, micro)'
)
text = text.replace(
    'df = df[df["microdistrict"].astype(str).str.strip() == micro]',
    'df = self._filter_by_microdistrict_smart(df, micro)'
)

if "df = self._filter_by_microdistrict_smart(df, micro)" not in text:
    district_marker = '        # Район\n        district = self.filter_district.currentText()'
    idx = text.find(district_marker)
    if idx != -1:
        # Put after the district block by finding next comment "# Микрорайон" or before price category
        micro_marker = '        # Микрорайон'
        midx = text.find(micro_marker, idx)
        if midx != -1:
            smart_block = '        # Микрорайон\n        micro = self.filter_microdistrict.currentText()\n        if micro and micro != "Все микрорайоны":\n            df = self._filter_by_microdistrict_smart(df, micro)\n\n'
            # Remove the old micro comment block roughly up to next "# Категория" if possible
            next_cat = text.find('        # Категория', midx)
            if next_cat != -1:
                text = text[:midx] + smart_block + text[next_cat:]
                print("OK: inserted smart microdistrict filter block")
        else:
            print("WARNING: could not find microdistrict block")
    else:
        print("WARNING: could not find district block")

MAIN_PATH.write_text(text, encoding="utf-8")

print("DONE.")
print("For real accuracy, add official polygons here: geo/microdistricts.geojson")
print("Then run: python main.py")
