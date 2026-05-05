
# -*- coding: utf-8 -*-
"""
fix_app_not_open_fast_start.py

Fixes app hanging before window opens after heavy microdistrict patches.
Run from project root:
python fix_app_not_open_fast_start.py
"""

from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")
GEO_PATH = Path("src/geo_utils.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py not found. Run from project root.")
if not GEO_PATH.exists():
    raise FileNotFoundError("src/geo_utils.py not found.")

for p in [MAIN_PATH, GEO_PATH]:
    b = p.with_suffix(p.suffix + ".backup_fast_start")
    if not b.exists():
        shutil.copyfile(p, b)
        print("Backup:", b)

FAST_GEO_PATCH = "\n# ============================================================\n# FAST START MICRODISTRICT CACHE PATCH START\n# ============================================================\n\n_FAST_OSM_CENTERS_CACHE = None\n_FAST_GEOJSON_CACHE = None\n\ndef _load_osm_micro_centers():\n    global _FAST_OSM_CENTERS_CACHE\n    if _FAST_OSM_CENTERS_CACHE is not None:\n        return _FAST_OSM_CENTERS_CACHE\n\n    try:\n        from pathlib import Path as _Path\n        import json as _json\n\n        p = _Path(\"geo/microdistrict_centers_osm.json\")\n        if not p.exists():\n            _FAST_OSM_CENTERS_CACHE = {}\n            return _FAST_OSM_CENTERS_CACHE\n\n        data = _json.loads(p.read_text(encoding=\"utf-8\"))\n        out = {}\n\n        for name, v in data.items():\n            try:\n                key = _md_alias(name) if \"_md_alias\" in globals() else str(name).strip()\n                out[key] = (\n                    float(v[\"lat\"]),\n                    float(v[\"lon\"]),\n                    float(v.get(\"radius_m\", 1200)),\n                )\n            except Exception:\n                continue\n\n        _FAST_OSM_CENTERS_CACHE = out\n        return _FAST_OSM_CENTERS_CACHE\n    except Exception:\n        _FAST_OSM_CENTERS_CACHE = {}\n        return _FAST_OSM_CENTERS_CACHE\n\n\ndef _load_microdistrict_geojson():\n    global _FAST_GEOJSON_CACHE\n    if _FAST_GEOJSON_CACHE is not None:\n        return _FAST_GEOJSON_CACHE\n\n    try:\n        from pathlib import Path as _Path\n        import json as _json\n\n        candidates = [\n            \"geo/microdistricts.geojson\",\n            \"geo/almaty_microdistricts.geojson\",\n            \"geo/almaty_microdistricts.json\",\n        ]\n\n        for file_name in candidates:\n            p = _Path(file_name)\n            if p.exists():\n                for enc in [\"utf-8\", \"utf-8-sig\"]:\n                    try:\n                        with open(p, \"r\", encoding=enc) as f:\n                            _FAST_GEOJSON_CACHE = _json.load(f)\n                            return _FAST_GEOJSON_CACHE\n                    except Exception:\n                        pass\n\n        _FAST_GEOJSON_CACHE = None\n        return None\n    except Exception:\n        _FAST_GEOJSON_CACHE = None\n        return None\n\n\ndef determine_microdistrict(lat: float, lon: float, address_text: str = \"\") -> str:\n    try:\n        found = _md_alias(extract_microdistrict_from_text(address_text)) if \"_md_alias\" in globals() else extract_microdistrict_from_text(address_text)\n        if found:\n            return found\n    except Exception:\n        pass\n\n    try:\n        lat = float(lat)\n        lon = float(lon)\n    except Exception:\n        return \"Не определён\"\n\n    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):\n        return \"Не определён\"\n\n    try:\n        found_geo = determine_microdistrict_from_geojson(lat, lon)\n        found_geo = _md_alias(found_geo) if \"_md_alias\" in globals() else found_geo\n        if found_geo:\n            return found_geo\n    except Exception:\n        pass\n\n    all_centers = {}\n    try:\n        all_centers.update(MICRODISTRICT_CENTERS)\n    except Exception:\n        pass\n\n    try:\n        all_centers.update(_load_osm_micro_centers())\n    except Exception:\n        pass\n\n    best_name = \"\"\n    best_dist = 10**18\n\n    for name, data in all_centers.items():\n        try:\n            clat, clon, _radius = data\n            try:\n                dist = haversine_distance(lat, lon, clat, clon)\n            except Exception:\n                dlat = (lat - clat) * 111000.0\n                dlon = (lon - clon) * 81000.0\n                dist = (dlat * dlat + dlon * dlon) ** 0.5\n\n            if dist < best_dist:\n                best_dist = dist\n                best_name = _md_alias(name) if \"_md_alias\" in globals() else str(name)\n        except Exception:\n            continue\n\n    return best_name or \"Не определён\"\n\n# ============================================================\n# FAST START MICRODISTRICT CACHE PATCH END\n# ============================================================\n"
AI_CONTEXT_METHOD = "\n    def _update_ai_context_panel(self):\n        \"\"\"Safe AI context updater.\"\"\"\n        if not hasattr(self, \"ai_context_label\"):\n            return\n\n        prop = getattr(self, \"selected_prop\", None)\n        if not prop:\n            self.ai_context_label.setText(\"Сначала выберите объект на карте\")\n            return\n\n        try:\n            micro = str(prop.get(\"microdistrict\", \"\")).strip()\n            if (not micro) or micro in [\"Не определён\", \"None\", \"nan\"]:\n                lat = prop.get(\"lat_raw\") or prop.get(\"map_lat\") or prop.get(\"latitude\") or prop.get(\"lat\")\n                lon = prop.get(\"lon_raw\") or prop.get(\"map_lon\") or prop.get(\"longitude\") or prop.get(\"lon\")\n                address_text = \" \".join([\n                    str(prop.get(\"address\", \"\")),\n                    str(prop.get(\"location\", \"\")),\n                    str(prop.get(\"title\", \"\")),\n                    str(prop.get(\"complex_name\", \"\")),\n                ])\n                micro = determine_microdistrict(lat, lon, address_text)\n                prop[\"microdistrict\"] = micro\n        except Exception:\n            micro = str(prop.get(\"microdistrict\", \"Не определён\"))\n\n        district = str(prop.get(\"district\", \"Не определён\"))\n        self.ai_context_label.setText(f\"Выбран объект: район — {district} | микрорайон — {micro or 'Не определён'}\")\n"

# Patch geo_utils.py
geo = GEO_PATH.read_text(encoding="utf-8", errors="replace")
geo = re.sub(
    r"\n# ============================================================\n# FAST START MICRODISTRICT CACHE PATCH START[\s\S]*?# FAST START MICRODISTRICT CACHE PATCH END\n# ============================================================\n",
    "\n",
    geo,
    count=1,
)
geo = geo.rstrip() + "\n\n" + FAST_GEO_PATCH.strip() + "\n"
GEO_PATH.write_text(geo, encoding="utf-8")
print("OK: geo_utils.py cached microdistrict loading")

# Patch main.py
main = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

# Comment deprecated HighDPI lines
main = re.sub(
    r"^\s*app\.setAttribute\(Qt\.AA_EnableHighDpiScaling,\s*True\)\s*$",
    "    # app.setAttribute(Qt.AA_EnableHighDpiScaling, True)",
    main,
    flags=re.MULTILINE,
)
main = re.sub(
    r"^\s*app\.setAttribute\(Qt\.AA_UseHighDpiPixmaps,\s*True\)\s*$",
    "    # app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)",
    main,
    flags=re.MULTILINE,
)
print("OK: deprecated Qt HighDPI lines commented")

# Remove startup heavy microdistrict recalculation
startup_pattern = (
    r'            # Определяем микрорайон по координатам, чтобы фильтр "Микрорайон" не был пустым\s*'
    r'df\["microdistrict"\]\s*=\s*df\.apply\(\s*'
    r'lambda r:\s*determine_microdistrict\([\s\S]*?\),\s*'
    r'axis=1\s*\)\s*'
)
startup_replacement = (
    '            # Fast start: do not calculate microdistrict for all rows during startup.\\n'
    '            # It will be calculated only for selected object or selected microdistrict filter.\\n'
    '            if "microdistrict" not in df.columns:\\n'
    '                df["microdistrict"] = "Не определён"\\n\\n'
)
main, c1 = re.subn(startup_pattern, startup_replacement, main, count=1)
print("Startup heavy microdistrict block replaced:", c1)

# Remove heavy recalculation inside _apply_filters
filter_pattern = (
    r'        # microdistrict_auto_recalc_before_filter[\s\S]*?'
    r'axis=1\s*\)\s*\n'
)
filter_replacement = (
    '        # Fast start: skip full microdistrict recalculation during every filter update.\\n'
    '        if "microdistrict" not in df.columns:\\n'
    '            df["microdistrict"] = "Не определён"\\n\\n'
)
main, c2 = re.subn(filter_pattern, filter_replacement, main, count=1)
print("Filter heavy microdistrict block replaced:", c2)

# Add missing AI context method
if "def _update_ai_context_panel" not in main:
    marker = "\n    def _on_geo_result"
    if marker in main:
        main = main.replace(marker, "\n" + AI_CONTEXT_METHOD.rstrip() + "\n" + marker, 1)
        print("OK: _update_ai_context_panel added before _on_geo_result")
    else:
        marker = "\n    def closeEvent"
        if marker in main:
            main = main.replace(marker, "\n" + AI_CONTEXT_METHOD.rstrip() + "\n" + marker, 1)
            print("OK: _update_ai_context_panel added before closeEvent")
        else:
            print("WARNING: could not insert _update_ai_context_panel")
else:
    print("OK: _update_ai_context_panel exists")

MAIN_PATH.write_text(main, encoding="utf-8")

for cache_file in ["cache/geocode_cache.json", "cache/osm_cache.json"]:
    p = Path(cache_file)
    if p.exists():
        p.write_text("{}", encoding="utf-8")
        print("Cleared:", p)

print("DONE.")
print("Run now: python main.py")
