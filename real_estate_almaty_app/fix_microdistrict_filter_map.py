# -*- coding: utf-8 -*-
from pathlib import Path
import re
import shutil

MAIN_PATH = Path("main.py")
GEO_PATH = Path("src/geo_utils.py")

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти файл из корня проекта real_estate_almaty_app.")
if not GEO_PATH.exists():
    raise FileNotFoundError("src/geo_utils.py не найден.")

backup = Path("main.py.backup_microdistrict_filter_map")
if not backup.exists():
    shutil.copyfile(MAIN_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

geo_backup = Path("src/geo_utils.py.backup_microdistrict_filter_map")
if not geo_backup.exists():
    shutil.copyfile(GEO_PATH, geo_backup)
    print("Backup created:", geo_backup)

HELPER_METHOD = '    def _filter_by_microdistrict_smart(self, df, micro_name):\n        # Smart microdistrict filter:\n        # 1) exact df["microdistrict"] match;\n        # 2) coordinate fallback around microdistrict center.\n        if df is None or len(df) == 0:\n            return df\n\n        micro_name = str(micro_name).strip()\n        if not micro_name or micro_name == "Все микрорайоны":\n            return df\n\n        result_parts = []\n\n        if "microdistrict" in df.columns:\n            exact = df[df["microdistrict"].astype(str).str.strip() == micro_name].copy()\n            if len(exact) > 0:\n                result_parts.append(exact)\n\n        center = None\n        try:\n            center = get_microdistrict_center(micro_name)\n        except Exception:\n            center = None\n\n        if center:\n            clat, clon, radius = center\n            radius = max(float(radius), 1400.0)\n\n            lat_col = "map_lat" if "map_lat" in df.columns else "latitude"\n            lon_col = "map_lon" if "map_lon" in df.columns else "longitude"\n\n            if lat_col in df.columns and lon_col in df.columns:\n                temp = df.copy()\n                dlat = (temp[lat_col].astype(float) - float(clat)) * 111000.0\n                dlon = (temp[lon_col].astype(float) - float(clon)) * 81000.0\n                temp["_micro_dist"] = (dlat * dlat + dlon * dlon) ** 0.5\n\n                near = temp[temp["_micro_dist"] <= radius].copy()\n                if "_micro_dist" in near.columns:\n                    near = near.drop(columns=["_micro_dist"])\n\n                if len(near) > 0:\n                    result_parts.append(near)\n\n        if result_parts:\n            merged = pd.concat(result_parts, ignore_index=False)\n            if "id" in merged.columns:\n                merged = merged.drop_duplicates(subset=["id"])\n            else:\n                merged = merged.drop_duplicates()\n            return merged\n\n        return df.iloc[0:0].copy()\n\n'
NEW_MICRO_BLOCK = '        # Микрорайон\n        micro = self.filter_microdistrict.currentText()\n        if micro and micro != "Все микрорайоны":\n            df = self._filter_by_microdistrict_smart(df, micro)\n\n'
RECALC_BLOCK = '        # microdistrict_auto_recalc_before_filter\n        # Если колонка microdistrict пустая/неопределённая, пересчитываем её по координатам.\n        if "microdistrict" not in df.columns or (\n            "microdistrict" in df.columns and df["microdistrict"].astype(str).isin(["", "Не определён", "nan", "None"]).mean() > 0.5\n        ):\n            lat_col = "map_lat" if "map_lat" in df.columns else "latitude"\n            lon_col = "map_lon" if "map_lon" in df.columns else "longitude"\n            if lat_col in df.columns and lon_col in df.columns:\n                df["microdistrict"] = df.apply(\n                    lambda r: determine_microdistrict(\n                        r.get(lat_col, 0),\n                        r.get(lon_col, 0),\n                        str(r.get("address", "")) + " " + str(r.get("location", "")) + " " + str(r.get("title", ""))\n                    ),\n                    axis=1\n                )\n\n'
GEO_FUNC = 'def get_microdistrict_center(name: str):\n    # Returns (lat, lon, radius_m) for microdistrict name.\n    # Used by map filter when df["microdistrict"] is still empty.\n    try:\n        return MICRODISTRICT_CENTERS.get(str(name).strip())\n    except Exception:\n        return None\n'

# 1) Patch geo_utils.py
geo = GEO_PATH.read_text(encoding="utf-8", errors="replace")
if "def get_microdistrict_center" not in geo:
    geo = geo.rstrip() + "\n\n" + GEO_FUNC.strip() + "\n"
    GEO_PATH.write_text(geo, encoding="utf-8")
    print("OK: get_microdistrict_center added to src/geo_utils.py")
else:
    print("OK: get_microdistrict_center already exists")

# 2) Patch main.py imports
text = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

def ensure_geo_import(source, name):
    # multiline import from src.geo_utils import (...)
    pattern = r"from src\.geo_utils import \(([\s\S]*?)\)"
    m = re.search(pattern, source)
    if m:
        inside = m.group(1)
        if name not in inside:
            source = source[:m.start(1)] + "    " + name + ",\n" + inside + source[m.end(1):]
            print("OK: imported", name)
        return source

    # one-line import
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
    print("OK: added src.geo_utils import", name)
    return source

text = ensure_geo_import(text, "get_microdistrict_center")
text = ensure_geo_import(text, "determine_microdistrict")

# 3) Add helper before _apply_filters
if "def _filter_by_microdistrict_smart" not in text:
    marker = "\n    def _apply_filters"
    if marker not in text:
        raise RuntimeError("Не найден метод _apply_filters в main.py")
    text = text.replace(marker, "\n" + HELPER_METHOD + marker, 1)
    print("OK: _filter_by_microdistrict_smart added")
else:
    print("OK: _filter_by_microdistrict_smart already exists")

# 4) Replace old microdistrict exact filter with smart filter
patterns = [
    r'''        # Микрорайон\s*
        micro = self\.filter_microdistrict\.currentText\(\)\s*
        if micro and micro != "Все микрорайоны" and "microdistrict" in df\.columns:\s*
            df = df\[df\["microdistrict"\]\.astype\(str\) == micro\]\s*
''',
    r'''        micro = self\.filter_microdistrict\.currentText\(\)\s*
        if micro and micro != "Все микрорайоны" and "microdistrict" in df\.columns:\s*
            df = df\[df\["microdistrict"\]\.astype\(str\) == micro\]\s*
''',
    r'''        # Микрорайон\s*
        micro = self\.filter_microdistrict\.currentText\(\)\s*
        if micro and micro != "Все микрорайоны":\s*
            df = self\._filter_by_microdistrict_smart\(df, micro\)\s*
''',
]

replaced = False
for pat in patterns:
    text2, count = re.subn(pat, NEW_MICRO_BLOCK, text, count=1, flags=re.DOTALL)
    if count:
        text = text2
        replaced = True
        print("OK: microdistrict filter block replaced")
        break

if not replaced and "self._filter_by_microdistrict_smart(df, micro)" not in text:
    # insert after district filter block
    district_pat = r'''        # Район\s*
        district = self\.filter_district\.currentText\(\)\s*
        if district[\s\S]*?df = df\[df\["district"\]\.astype\(str\) == district\]\s*
'''
    m = re.search(district_pat, text, flags=re.DOTALL)
    if m:
        text = text[:m.end()] + "\n" + NEW_MICRO_BLOCK + text[m.end():]
        replaced = True
        print("OK: smart microdistrict filter inserted after district block")
    else:
        print("WARNING: could not find district filter block")

# 5) Insert recalculation right before smart micro filter
if "microdistrict_auto_recalc_before_filter" not in text:
    idx = text.find("        # Микрорайон\n        micro = self.filter_microdistrict.currentText()")
    if idx != -1:
        text = text[:idx] + RECALC_BLOCK + text[idx:]
        print("OK: microdistrict recalculation inserted")
    else:
        print("WARNING: could not insert microdistrict recalculation")
else:
    print("OK: microdistrict recalculation already exists")

MAIN_PATH.write_text(text, encoding="utf-8")

print("DONE: microdistrict map filtering fixed.")
print("Now run: python main.py")
