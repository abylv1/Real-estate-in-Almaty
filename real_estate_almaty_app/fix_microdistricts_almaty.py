# -*- coding: utf-8 -*-
from pathlib import Path
import re
import shutil

ROOT = Path(".")
MAIN_PATH = ROOT / "main.py"
GEO_PATH = ROOT / "src" / "geo_utils.py"

if not MAIN_PATH.exists():
    raise FileNotFoundError("main.py не найден. Запусти файл из корня проекта real_estate_almaty_app.")
if not GEO_PATH.exists():
    raise FileNotFoundError("src/geo_utils.py не найден.")

def backup(path: Path):
    b = path.with_suffix(path.suffix + ".backup_microdistricts")
    if not b.exists():
        shutil.copyfile(path, b)
        print("Backup:", b)

backup(MAIN_PATH)
backup(GEO_PATH)

MICRO_BLOCK = '\n# ============================================================\n# MICRODISTRICTS PATCH START\n# Улучшенное определение микрорайонов Алматы\n# ============================================================\n\nMICRODISTRICT_UNKNOWN = "Не определён"\n\nALMATY_MICRODISTRICTS = [\n    "Аксай-1", "Аксай-2", "Аксай-3", "Аксай-4", "Аксай-5",\n    "Айнабулак-1", "Айнабулак-2", "Айнабулак-3", "Айнабулак-4",\n    "Алатау", "Алмагуль", "Алтын Бесик", "Алгабас", "Алгабас-1", "Алгабас-6",\n    "Акбулак", "Акбулак-1", "Акбулак-2", "Атырау",\n    "Баганашыл", "Баянаул", "Боралдай",\n    "Горный Гигант", "Думан", "Думан-1", "Думан-2",\n    "Достык", "Ерменсай", "Жас Канат", "Жетысу-1", "Жетысу-2", "Жетысу-3", "Жетысу-4",\n    "Жулдыз-1", "Жулдыз-2", "Зердели",\n    "Казахфильм", "Кайрат", "Калкаман-1", "Калкаман-2",\n    "Каменка", "Карагайлы", "Кокжиек", "Коктем-1", "Коктем-2", "Коктем-3",\n    "Кулагер", "Курылысшы",\n    "Мамыр-1", "Мамыр-2", "Мамыр-3", "Мамыр-4", "Мамыр-5", "Мамыр-6", "Мамыр-7",\n    "Мирас", "Нур Алатау", "Нуркент",\n    "Орбита-1", "Орбита-2", "Орбита-3", "Орбита-4",\n    "Рахат", "Сайран", "Самал-1", "Самал-2", "Самал-3",\n    "Саялы", "Сулусай", "Таугуль-1", "Таугуль-2", "Таугуль-3",\n    "Таусамалы", "Тастак-1", "Тастак-2", "Тастак-3",\n    "Теректы", "Улжан-1", "Улжан-2", "Шанырак-1", "Шанырак-2",\n    "Шугыла", "Юбилейный",\n]\n\nMICRODISTRICT_CENTERS = {\n    "Самал-1": (43.2365, 76.9550, 900), "Самал-2": (43.2340, 76.9495, 900),\n    "Самал-3": (43.2310, 76.9435, 900), "Коктем-1": (43.2305, 76.9280, 900),\n    "Коктем-2": (43.2275, 76.9230, 900), "Коктем-3": (43.2240, 76.9175, 900),\n    "Алмагуль": (43.2145, 76.8990, 1100), "Казахфильм": (43.2035, 76.9115, 1300),\n    "Баганашыл": (43.1920, 76.9180, 1500), "Нур Алатау": (43.1855, 76.9060, 1600),\n    "Мирас": (43.1910, 76.8950, 1400), "Ерменсай": (43.1720, 76.8920, 1700),\n    "Горный Гигант": (43.2160, 76.9790, 1300), "Думан-1": (43.2460, 77.0500, 1500),\n    "Думан-2": (43.2390, 77.0580, 1500),\n    "Орбита-1": (43.1995, 76.8915, 1000), "Орбита-2": (43.1970, 76.8865, 1000),\n    "Орбита-3": (43.1930, 76.8840, 1000), "Орбита-4": (43.1900, 76.8795, 1100),\n    "Таугуль-1": (43.2160, 76.8540, 1000), "Таугуль-2": (43.2110, 76.8490, 1000),\n    "Таугуль-3": (43.2070, 76.8440, 1000),\n    "Мамыр-1": (43.2190, 76.8460, 900), "Мамыр-2": (43.2160, 76.8400, 900),\n    "Мамыр-3": (43.2140, 76.8350, 900), "Мамыр-4": (43.2110, 76.8300, 900),\n    "Мамыр-5": (43.2080, 76.8250, 900), "Мамыр-6": (43.2055, 76.8190, 900),\n    "Мамыр-7": (43.2025, 76.8140, 900),\n    "Аксай-1": (43.2335, 76.8340, 1000), "Аксай-2": (43.2380, 76.8280, 1000),\n    "Аксай-3": (43.2420, 76.8220, 1000), "Аксай-4": (43.2470, 76.8170, 1000),\n    "Аксай-5": (43.2520, 76.8120, 1000), "Алтын Бесик": (43.2405, 76.8040, 1300),\n    "Жетысу-1": (43.2550, 76.8540, 1000), "Жетысу-2": (43.2600, 76.8580, 1000),\n    "Жетысу-3": (43.2650, 76.8640, 1000), "Жетысу-4": (43.2700, 76.8700, 1000),\n    "Тастак-1": (43.2520, 76.8890, 1100), "Тастак-2": (43.2490, 76.8810, 1100),\n    "Тастак-3": (43.2450, 76.8750, 1100), "Сайран": (43.2380, 76.8760, 1300),\n    "Айнабулак-1": (43.3100, 76.9250, 1100), "Айнабулак-2": (43.3160, 76.9300, 1100),\n    "Айнабулак-3": (43.3220, 76.9360, 1100), "Айнабулак-4": (43.3280, 76.9420, 1100),\n    "Кокжиек": (43.3380, 76.9450, 1600), "Кулагер": (43.3010, 76.9000, 1500),\n    "Курылысшы": (43.2920, 76.8900, 1500),\n    "Нуркент": (43.2800, 76.7600, 1800), "Саялы": (43.3040, 76.7820, 1800),\n    "Акбулак": (43.2920, 76.8080, 1600), "Зердели": (43.2675, 76.8140, 1300),\n    "Алгабас": (43.2590, 76.7850, 1800), "Алгабас-1": (43.2650, 76.7800, 1600),\n    "Алгабас-6": (43.2520, 76.7740, 1600), "Улжан-1": (43.3180, 76.7900, 1800),\n    "Улжан-2": (43.3280, 76.8000, 1800), "Шанырак-1": (43.3330, 76.8100, 1800),\n    "Шанырак-2": (43.3430, 76.8200, 1800),\n    "Калкаман-1": (43.2260, 76.7590, 1500), "Калкаман-2": (43.2170, 76.7480, 1500),\n    "Каменка": (43.1810, 76.7590, 1800), "Карагайлы": (43.2020, 76.7440, 1800),\n    "Таусамалы": (43.1900, 76.7820, 1700), "Шугыла": (43.2100, 76.7250, 1800),\n    "Рахат": (43.2010, 76.7900, 1600),\n    "Жулдыз-1": (43.3460, 77.0300, 1700), "Жулдыз-2": (43.3540, 77.0400, 1700),\n    "Кайрат": (43.3470, 76.9950, 1800), "Жас Канат": (43.3520, 77.0200, 1700),\n    "Алатау": (43.3500, 76.9800, 1800),\n}\n\ndef get_all_microdistricts() -> list:\n    return list(ALMATY_MICRODISTRICTS)\n\ndef extract_microdistrict_from_text(text: str) -> str:\n    if not text:\n        return ""\n    low = str(text).lower()\n    for name in sorted(ALMATY_MICRODISTRICTS, key=len, reverse=True):\n        if name.lower() in low:\n            return name\n    import re as _re\n    patterns = [\n        (r"самал\\s*[- ]?\\s*([1-3])", "Самал-{}"), (r"орбита\\s*[- ]?\\s*([1-4])", "Орбита-{}"),\n        (r"мамыр\\s*[- ]?\\s*([1-7])", "Мамыр-{}"), (r"аксай\\s*[- ]?\\s*([1-5])", "Аксай-{}"),\n        (r"жетысу\\s*[- ]?\\s*([1-4])", "Жетысу-{}"), (r"айнабулак\\s*[- ]?\\s*([1-4])", "Айнабулак-{}"),\n        (r"коктем\\s*[- ]?\\s*([1-3])", "Коктем-{}"), (r"таугуль\\s*[- ]?\\s*([1-3])", "Таугуль-{}"),\n        (r"калкаман\\s*[- ]?\\s*([1-2])", "Калкаман-{}"), (r"жулдыз\\s*[- ]?\\s*([1-2])", "Жулдыз-{}"),\n        (r"улжан\\s*[- ]?\\s*([1-2])", "Улжан-{}"), (r"шанырак\\s*[- ]?\\s*([1-2])", "Шанырак-{}"),\n        (r"тастак\\s*[- ]?\\s*([1-3])", "Тастак-{}"),\n    ]\n    for pat, out in patterns:\n        m = _re.search(pat, low)\n        if m:\n            return out.format(m.group(1))\n    return ""\n\ndef determine_microdistrict(lat: float, lon: float, address_text: str = "") -> str:\n    found = extract_microdistrict_from_text(address_text)\n    if found:\n        return found\n    try:\n        lat = float(lat); lon = float(lon)\n    except Exception:\n        return MICRODISTRICT_UNKNOWN\n    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):\n        return MICRODISTRICT_UNKNOWN\n    best_name = ""; best_dist = 10**9; best_radius = 0\n    for name, data in MICRODISTRICT_CENTERS.items():\n        clat, clon, radius = data\n        try:\n            dist = haversine_distance(lat, lon, clat, clon)\n        except Exception:\n            import math\n            r = 6371000\n            p1 = math.radians(lat); p2 = math.radians(clat)\n            dp = math.radians(clat - lat); dl = math.radians(clon - lon)\n            a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2\n            dist = 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))\n        if dist < best_dist:\n            best_dist = dist; best_name = name; best_radius = radius\n    if best_name and best_dist <= max(best_radius, 1400):\n        return best_name\n    return MICRODISTRICT_UNKNOWN\n\n# ============================================================\n# MICRODISTRICTS PATCH END\n# ============================================================\n'
MICRO_CALC_CODE = '            # Определяем микрорайон по координатам, чтобы фильтр "Микрорайон" не был пустым\n            df["microdistrict"] = df.apply(\n                lambda r: determine_microdistrict(\n                    r.get("map_lat", r.get("latitude", 0)),\n                    r.get("map_lon", r.get("longitude", 0)),\n                    str(r.get("address", "")) + " " + str(r.get("location", ""))\n                ),\n                axis=1\n            )\n'
TARGET_DISTRICT = '            df["district"] = df.apply(\n                lambda r: determine_district(r["map_lat"], r["map_lon"]), axis=1\n            )\n'
MICRO_COMBO_NEW = '        # Микрорайоны: показываем полный список популярных микрорайонов Алматы,\n        # а также найденные в данных значения\n        self.filter_microdistrict.clear()\n        self.filter_microdistrict.addItem("Все микрорайоны")\n\n        micros = list(get_all_microdistricts())\n        if "microdistrict" in df.columns:\n            discovered = sorted([\n                str(x).strip() for x in df["microdistrict"].dropna().unique()\n                if str(x).strip() and str(x).strip() != "Не определён"\n            ])\n            for m in discovered:\n                if m not in micros:\n                    micros.append(m)\n\n        self.filter_microdistrict.addItems(micros)\n'
HELPER_METHOD = '    def _ensure_selected_microdistrict(self):\n        """Если у выбранного объекта микрорайон не определён, определяем его по координатам."""\n        if not hasattr(self, "selected_prop") or self.selected_prop is None:\n            return\n\n        current = str(self.selected_prop.get("microdistrict", "")).strip()\n        if current and current != "Не определён":\n            return\n\n        lat = self.selected_prop.get("lat_raw") or self.selected_prop.get("map_lat") or self.selected_prop.get("latitude")\n        lon = self.selected_prop.get("lon_raw") or self.selected_prop.get("map_lon") or self.selected_prop.get("longitude")\n        address_text = " ".join([str(self.selected_prop.get("address", "")), str(self.selected_prop.get("location", "")), str(self.selected_prop.get("title", ""))])\n        micro = determine_microdistrict(lat, lon, address_text)\n        if micro:\n            self.selected_prop["microdistrict"] = micro\n            try:\n                prop_id = self.selected_prop.get("id")\n                if prop_id is not None and self.df is not None and "id" in self.df.columns:\n                    self.df.loc[self.df["id"] == prop_id, "microdistrict"] = micro\n                    if hasattr(self, "filtered_df") and self.filtered_df is not None and "id" in self.filtered_df.columns:\n                        self.filtered_df.loc[self.filtered_df["id"] == prop_id, "microdistrict"] = micro\n            except Exception:\n                pass\n            if hasattr(self, "_refresh_microdistrict_filter_values"):\n                try:\n                    self._refresh_microdistrict_filter_values()\n                except Exception:\n                    pass\n\n'
REFRESH_NEW = '    def _refresh_microdistrict_filter_values(self):\n        """Обновляет список микрорайонов в фильтре, сохраняя полный список Алматы."""\n        if self.df is None or not hasattr(self, "filter_microdistrict"):\n            return\n        current = self.filter_microdistrict.currentText()\n        self.filter_microdistrict.blockSignals(True)\n        self.filter_microdistrict.clear()\n        self.filter_microdistrict.addItem("Все микрорайоны")\n        micros = list(get_all_microdistricts())\n        if "microdistrict" in self.df.columns:\n            discovered = sorted([str(x).strip() for x in self.df["microdistrict"].dropna().unique() if str(x).strip() and str(x).strip() != "Не определён"])\n            for m in discovered:\n                if m not in micros:\n                    micros.append(m)\n        self.filter_microdistrict.addItems(micros)\n        idx = self.filter_microdistrict.findText(current)\n        if idx >= 0:\n            self.filter_microdistrict.setCurrentIndex(idx)\n        self.filter_microdistrict.blockSignals(False)\n'

geo = GEO_PATH.read_text(encoding="utf-8", errors="replace")
geo = re.sub(
    r"\n# ============================================================\n# MICRODISTRICTS PATCH START[\s\S]*?# MICRODISTRICTS PATCH END\n# ============================================================\n",
    "\n",
    geo,
    count=1,
)
geo = geo.rstrip() + "\n\n" + MICRO_BLOCK.strip() + "\n"
GEO_PATH.write_text(geo, encoding="utf-8")
print("OK: src/geo_utils.py patched with microdistrict functions")

main = MAIN_PATH.read_text(encoding="utf-8", errors="replace")

if "determine_microdistrict" not in main or "get_all_microdistricts" not in main:
    pattern = r"from src\.geo_utils import \(([\s\S]*?)\)"
    m = re.search(pattern, main)
    if m:
        inside = m.group(1)
        add = ""
        if "determine_microdistrict" not in inside:
            add += "    determine_microdistrict,\n"
        if "get_all_microdistricts" not in inside:
            add += "    get_all_microdistricts,\n"
        main = main[:m.start(1)] + add + inside + main[m.end(1):]
        print("OK: geo_utils multiline import patched")
    else:
        pattern2 = r"from src\.geo_utils import ([^\n]+)"
        m2 = re.search(pattern2, main)
        if m2:
            line = m2.group(1)
            names = [x.strip() for x in line.split(",")]
            if "determine_microdistrict" not in names:
                names.append("determine_microdistrict")
            if "get_all_microdistricts" not in names:
                names.append("get_all_microdistricts")
            main = main[:m2.start(1)] + ", ".join(names) + main[m2.end(1):]
            print("OK: geo_utils one-line import patched")
        else:
            main = "from src.geo_utils import determine_microdistrict, get_all_microdistricts\n" + main
            print("OK: geo_utils import added at top")

if "Определяем микрорайон по координатам" not in main:
    if TARGET_DISTRICT in main:
        main = main.replace(TARGET_DISTRICT, TARGET_DISTRICT + MICRO_CALC_CODE, 1)
        print("OK: microdistrict calculation inserted after district calculation")
    else:
        pat = r'(df\["district"\]\s*=\s*df\.apply\([\s\S]*?determine_district[\s\S]*?axis=1\s*\)\s*)'
        main, count = re.subn(lambda m: m.group(1) + "\n" + MICRO_CALC_CODE, pat, main, count=1)
        if count:
            print("OK: microdistrict calculation inserted flexibly")
        else:
            print("WARNING: district calculation block not found")

pat = r'        # Микрорайоны[\s\S]*?self\.filter_microdistrict\.addItems\(micros\)\n'
main2, count = re.subn(pat, MICRO_COMBO_NEW, main, count=1)
if count:
    main = main2
    print("OK: _init_filter_ranges microdistrict block replaced")
else:
    pat2 = r'        self\.filter_microdistrict\.clear\(\)\s*\n        self\.filter_microdistrict\.addItem\("Все микрорайоны"\)[\s\S]*?self\.filter_microdistrict\.addItems\(micros\)\n'
    main2, count = re.subn(pat2, MICRO_COMBO_NEW, main, count=1)
    if count:
        main = main2
        print("OK: _init_filter_ranges microdistrict block replaced by fallback")
    else:
        print("WARNING: microdistrict combobox block not found")

if "def _ensure_selected_microdistrict" not in main:
    marker = "\n    def _update_property_panel_basic"
    if marker in main:
        main = main.replace(marker, "\n" + HELPER_METHOD + marker, 1)
        print("OK: _ensure_selected_microdistrict helper added")
    else:
        print("WARNING: could not find _update_property_panel_basic insertion point")

for method_name in ["_update_property_panel_basic", "_update_property_panel_full"]:
    pat = rf"(    def {method_name}\(self\):\n)"
    if f"def {method_name}" in main:
        idx = main.find(f"def {method_name}")
        sample = main[idx:idx+300]
        if "self._ensure_selected_microdistrict()" not in sample:
            main = re.sub(pat, r"\1        self._ensure_selected_microdistrict()\n", main, count=1)
            print(f"OK: {method_name} now calls _ensure_selected_microdistrict")

pat = r"\n    def _refresh_microdistrict_filter_values\(self\):[\s\S]*?(?=\n    def |\n# ============================================================|\Z)"
if "def _refresh_microdistrict_filter_values" in main:
    main, count = re.subn(pat, "\n" + REFRESH_NEW, main, count=1)
    if count:
        print("OK: _refresh_microdistrict_filter_values replaced")
else:
    marker = "\n    def _update_ai_context_panel"
    if marker in main:
        main = main.replace(marker, "\n" + REFRESH_NEW + marker, 1)
        print("OK: _refresh_microdistrict_filter_values added")

MAIN_PATH.write_text(main, encoding="utf-8")

p = ROOT / "cache" / "geocode_cache.json"
if p.exists():
    p.write_text("{}", encoding="utf-8")
    print("Cleared:", p)

print("DONE: microdistrict filter and object location improved.")
print("Now run: python main.py")
