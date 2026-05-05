
# -*- coding: utf-8 -*-
from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")
GEO_PATH = Path("src/geo_utils.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден.")
if not GEO_PATH.exists():
    raise FileNotFoundError("src/geo_utils.py не найден.")

for p in [MAIN_PATH, GEO_PATH]:
    b = p.with_suffix(p.suffix + ".backup_microdistrict_no_unknown")
    if not b.exists():
        shutil.copyfile(p, b)
        print("Backup:", b)

GEO_OVERRIDE = "\n# ============================================================\n# MICRODISTRICT NO-UNKNOWN OVERRIDE START\n# ============================================================\n\n_EXTRA_MICRODISTRICT_CENTERS = {\n    \"Самал-1\": (43.2365, 76.9550, 900), \"Самал-2\": (43.2340, 76.9495, 900), \"Самал-3\": (43.2310, 76.9435, 900),\n    \"Коктем-1\": (43.2305, 76.9280, 900), \"Коктем-2\": (43.2275, 76.9230, 900), \"Коктем-3\": (43.2240, 76.9175, 900),\n    \"Алмагуль\": (43.2145, 76.8990, 1100), \"Казахфильм\": (43.2035, 76.9115, 1300),\n    \"Баганашыл\": (43.1920, 76.9180, 1500), \"Нур Алатау\": (43.1855, 76.9060, 1700),\n    \"Мирас\": (43.1910, 76.8950, 1500), \"Ерменсай\": (43.1720, 76.8920, 1900),\n    \"Горный Гигант\": (43.2160, 76.9790, 1300), \"Думан-1\": (43.2460, 77.0500, 1700), \"Думан-2\": (43.2390, 77.0580, 1700),\n\n    \"Орбита-1\": (43.1995, 76.8915, 1100), \"Орбита-2\": (43.1970, 76.8865, 1100),\n    \"Орбита-3\": (43.1930, 76.8840, 1100), \"Орбита-4\": (43.1900, 76.8795, 1200),\n    \"Таугуль-1\": (43.2160, 76.8540, 1100), \"Таугуль-2\": (43.2110, 76.8490, 1100), \"Таугуль-3\": (43.2070, 76.8440, 1100),\n\n    \"Мамыр-1\": (43.2190, 76.8460, 1000), \"Мамыр-2\": (43.2160, 76.8400, 1000), \"Мамыр-3\": (43.2140, 76.8350, 1000),\n    \"Мамыр-4\": (43.2110, 76.8300, 1000), \"Мамыр-5\": (43.2080, 76.8250, 1000), \"Мамыр-6\": (43.2055, 76.8190, 1000), \"Мамыр-7\": (43.2025, 76.8140, 1000),\n\n    \"Аксай-1\": (43.2335, 76.8340, 1100), \"Аксай-2\": (43.2380, 76.8280, 1100), \"Аксай-3\": (43.2420, 76.8220, 1100),\n    \"Аксай-4\": (43.2470, 76.8170, 1100), \"Аксай-5\": (43.2520, 76.8120, 1100),\n    \"Алтын Бесик\": (43.2405, 76.8040, 1500),\n\n    \"Жетысу-1\": (43.2550, 76.8540, 1100), \"Жетысу-2\": (43.2600, 76.8580, 1100),\n    \"Жетысу-3\": (43.2650, 76.8640, 1100), \"Жетысу-4\": (43.2700, 76.8700, 1100),\n    \"Тастак-1\": (43.2520, 76.8890, 1200), \"Тастак-2\": (43.2490, 76.8810, 1200),\n    \"Тастак-3\": (43.2450, 76.8750, 1200), \"Сайран\": (43.2380, 76.8760, 1400),\n\n    \"Айнабулак-1\": (43.3100, 76.9250, 1200), \"Айнабулак-2\": (43.3160, 76.9300, 1200),\n    \"Айнабулак-3\": (43.3220, 76.9360, 1200), \"Айнабулак-4\": (43.3280, 76.9420, 1200),\n    \"Кокжиек\": (43.3380, 76.9450, 1800), \"Кулагер\": (43.3010, 76.9000, 1700),\n    \"Курылысшы\": (43.2920, 76.8900, 1700),\n\n    \"Нуркент\": (43.2800, 76.7600, 2000), \"Саялы\": (43.3040, 76.7820, 2000),\n    \"Акбулак\": (43.2920, 76.8080, 1800), \"Зердели\": (43.2675, 76.8140, 1500),\n    \"Алгабас\": (43.2590, 76.7850, 2000), \"Алгабас-1\": (43.2650, 76.7800, 1800), \"Алгабас-6\": (43.2520, 76.7740, 1800),\n    \"Улжан-1\": (43.3180, 76.7900, 2000), \"Улжан-2\": (43.3280, 76.8000, 2000),\n    \"Шанырак-1\": (43.3330, 76.8100, 2000), \"Шанырак-2\": (43.3430, 76.8200, 2000),\n\n    \"Калкаман-1\": (43.2260, 76.7590, 1700), \"Калкаман-2\": (43.2170, 76.7480, 1700),\n    \"Каменка\": (43.1810, 76.7590, 2200), \"Карагайлы\": (43.2020, 76.7440, 2000),\n    \"Таусамалы\": (43.1900, 76.7820, 1900), \"Шугыла\": (43.2100, 76.7250, 2200), \"Рахат\": (43.2010, 76.7900, 1800),\n\n    \"Жулдыз-1\": (43.3460, 77.0300, 2000), \"Жулдыз-2\": (43.3540, 77.0400, 2000),\n    \"Кайрат\": (43.3470, 76.9950, 2200), \"Жас Канат\": (43.3520, 77.0200, 2000), \"Алатау\": (43.3500, 76.9800, 2200),\n\n    \"Золотой квадрат\": (43.2550, 76.9450, 1600),\n    \"Арбат\": (43.2620, 76.9400, 1200),\n    \"Центр\": (43.2500, 76.9300, 1800),\n}\n\ntry:\n    MICRODISTRICT_UNKNOWN\nexcept NameError:\n    MICRODISTRICT_UNKNOWN = \"Не определён\"\n\ntry:\n    MICRODISTRICT_CENTERS.update(_EXTRA_MICRODISTRICT_CENTERS)\nexcept Exception:\n    MICRODISTRICT_CENTERS = dict(_EXTRA_MICRODISTRICT_CENTERS)\n\ntry:\n    for _name in _EXTRA_MICRODISTRICT_CENTERS:\n        if _name not in ALMATY_MICRODISTRICTS:\n            ALMATY_MICRODISTRICTS.append(_name)\nexcept Exception:\n    ALMATY_MICRODISTRICTS = list(_EXTRA_MICRODISTRICT_CENTERS.keys())\n\n\ndef get_all_microdistricts() -> list:\n    try:\n        return sorted(set(ALMATY_MICRODISTRICTS))\n    except Exception:\n        return sorted(set(_EXTRA_MICRODISTRICT_CENTERS.keys()))\n\n\ndef _nearest_microdistrict_by_center(lat: float, lon: float) -> str:\n    best_name = \"\"\n    best_dist = 10**18\n\n    for name, data in MICRODISTRICT_CENTERS.items():\n        try:\n            clat, clon, _radius = data\n            try:\n                dist = haversine_distance(lat, lon, clat, clon)\n            except Exception:\n                dlat = (lat - clat) * 111000.0\n                dlon = (lon - clon) * 81000.0\n                dist = (dlat * dlat + dlon * dlon) ** 0.5\n\n            if dist < best_dist:\n                best_dist = dist\n                best_name = name\n        except Exception:\n            continue\n\n    return best_name or MICRODISTRICT_UNKNOWN\n\n\ndef determine_microdistrict(lat: float, lon: float, address_text: str = \"\") -> str:\n    try:\n        found = extract_microdistrict_from_text(address_text)\n        if found:\n            return found\n    except Exception:\n        pass\n\n    try:\n        lat = float(lat)\n        lon = float(lon)\n    except Exception:\n        return MICRODISTRICT_UNKNOWN\n\n    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):\n        return MICRODISTRICT_UNKNOWN\n\n    try:\n        found_geo = determine_microdistrict_from_geojson(lat, lon)\n        if found_geo:\n            return found_geo\n    except Exception:\n        pass\n\n    return _nearest_microdistrict_by_center(lat, lon)\n\n\ndef get_microdistrict_center(name: str):\n    try:\n        name = str(name).strip()\n    except Exception:\n        return None\n\n    try:\n        center = MICRODISTRICT_CENTERS.get(name)\n        if center:\n            return center\n    except Exception:\n        pass\n\n    try:\n        geojson = _load_microdistrict_geojson()\n        if geojson:\n            for feature in geojson.get(\"features\", []):\n                fname = _microdistrict_feature_name(feature)\n                if fname == name:\n                    c = _feature_center_and_radius(feature)\n                    if c:\n                        return c\n    except Exception:\n        pass\n\n    return None\n\n# ============================================================\n# MICRODISTRICT NO-UNKNOWN OVERRIDE END\n# ============================================================\n"
MAIN_HELPER = "\n    def _ensure_selected_microdistrict(self):\n        # If selected object has no microdistrict, calculate it by coordinates.\n        if not hasattr(self, \"selected_prop\") or self.selected_prop is None:\n            return\n\n        current = str(self.selected_prop.get(\"microdistrict\", \"\")).strip()\n        if current and current not in [\"Не определён\", \"None\", \"nan\", \"\"]:\n            return\n\n        lat = (\n            self.selected_prop.get(\"lat_raw\")\n            or self.selected_prop.get(\"map_lat\")\n            or self.selected_prop.get(\"latitude\")\n            or self.selected_prop.get(\"lat\")\n        )\n        lon = (\n            self.selected_prop.get(\"lon_raw\")\n            or self.selected_prop.get(\"map_lon\")\n            or self.selected_prop.get(\"longitude\")\n            or self.selected_prop.get(\"lon\")\n        )\n\n        address_text = \" \".join([\n            str(self.selected_prop.get(\"address\", \"\")),\n            str(self.selected_prop.get(\"location\", \"\")),\n            str(self.selected_prop.get(\"title\", \"\")),\n            str(self.selected_prop.get(\"complex_name\", \"\")),\n        ])\n\n        micro = determine_microdistrict(lat, lon, address_text)\n        if micro:\n            self.selected_prop[\"microdistrict\"] = micro\n\n            try:\n                prop_id = self.selected_prop.get(\"id\")\n                if prop_id is not None and self.df is not None and \"id\" in self.df.columns:\n                    self.df.loc[self.df[\"id\"] == prop_id, \"microdistrict\"] = micro\n                if prop_id is not None and hasattr(self, \"filtered_df\") and self.filtered_df is not None and \"id\" in self.filtered_df.columns:\n                    self.filtered_df.loc[self.filtered_df[\"id\"] == prop_id, \"microdistrict\"] = micro\n            except Exception:\n                pass\n\n"

# Patch geo_utils.py
geo = GEO_PATH.read_text(encoding="utf-8", errors="replace")
geo = re.sub(
    r"\n# ============================================================\n# MICRODISTRICT NO-UNKNOWN OVERRIDE START[\s\S]*?# MICRODISTRICT NO-UNKNOWN OVERRIDE END\n# ============================================================\n",
    "\n",
    geo,
    count=1,
)
geo = geo.rstrip() + "\n\n" + GEO_OVERRIDE.strip() + "\n"
GEO_PATH.write_text(geo, encoding="utf-8")
print("OK: geo_utils.py patched — microdistrict now chooses nearest known area inside Almaty")

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

method_pat = r"\n    def _ensure_selected_microdistrict\(self\):[\s\S]*?(?=\n    def |\n# ============================================================|\Z)"
if "def _ensure_selected_microdistrict" in main:
    main, count = re.subn(method_pat, "\n" + MAIN_HELPER.rstrip() + "\n", main, count=1)
    print("OK: _ensure_selected_microdistrict replaced")
else:
    marker = "\n    def _update_property_panel_basic"
    if marker in main:
        main = main.replace(marker, "\n" + MAIN_HELPER.rstrip() + "\n" + marker, 1)
        print("OK: _ensure_selected_microdistrict added")
    else:
        print("WARNING: could not insert _ensure_selected_microdistrict")

for method_name in ["_update_property_panel_basic", "_update_property_panel_full"]:
    if f"def {method_name}" in main:
        idx = main.find(f"def {method_name}")
        sample = main[idx:idx+350]
        if "self._ensure_selected_microdistrict()" not in sample:
            main = re.sub(
                rf"(    def {method_name}\(self\):\n)",
                r"\1        self._ensure_selected_microdistrict()\n",
                main,
                count=1
            )
            print("OK:", method_name, "calls _ensure_selected_microdistrict")

cache = Path("cache/geocode_cache.json")
if cache.exists():
    cache.write_text("{}", encoding="utf-8")
    print("Cleared:", cache)

MAIN_PATH.write_text(main, encoding="utf-8")
print("DONE. Run: python main.py")
