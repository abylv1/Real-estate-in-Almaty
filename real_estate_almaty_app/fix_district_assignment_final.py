# -*- coding: utf-8 -*-
"""
fix_district_assignment_final.py

Исправляет пустые районы в фильтре карты.
Если Алмалинский / Жетысуский / Турксибский пустые, значит районы
были рассчитаны старыми неточными правилами или сохранились как ????.

Запускать из корня проекта:
python fix_district_assignment_final.py
"""

from pathlib import Path
import re
import shutil

D_ALATAU = "\u0410\u043b\u0430\u0442\u0430\u0443\u0441\u043a\u0438\u0439"
D_ALMALY = "\u0410\u043b\u043c\u0430\u043b\u0438\u043d\u0441\u043a\u0438\u0439"
D_AUEZOV = "\u0410\u0443\u044d\u0437\u043e\u0432\u0441\u043a\u0438\u0439"
D_BOSTANDYK = "\u0411\u043e\u0441\u0442\u0430\u043d\u0434\u044b\u043a\u0441\u043a\u0438\u0439"
D_ZHETYSU = "\u0416\u0435\u0442\u044b\u0441\u0443\u0441\u043a\u0438\u0439"
D_MEDEU = "\u041c\u0435\u0434\u0435\u0443\u0441\u043a\u0438\u0439"
D_NAURYZBAY = "\u041d\u0430\u0443\u0440\u044b\u0437\u0431\u0430\u0439\u0441\u043a\u0438\u0439"
D_TURKSIB = "\u0422\u0443\u0440\u043a\u0441\u0438\u0431\u0441\u043a\u0438\u0439"
UNKNOWN = "\u0420\u0430\u0439\u043e\u043d \u043d\u0435 \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0451\u043d \u0442\u043e\u0447\u043d\u043e"
ALL_DISTRICTS = "\u0412\u0441\u0435 \u0440\u0430\u0439\u043e\u043d\u044b"

DISTRICTS = [
    D_ALATAU,
    D_ALMALY,
    D_AUEZOV,
    D_BOSTANDYK,
    D_ZHETYSU,
    D_MEDEU,
    D_NAURYZBAY,
    D_TURKSIB,
]


def backup(path: Path):
    if path.exists():
        b = path.with_suffix(path.suffix + ".backup_district_assignment_final")
        if not b.exists():
            shutil.copyfile(path, b)
            print("Backup:", b)


def build_new_determine_district() -> str:
    lines = [
        "def determine_district(lat: float, lon: float) -> str:",
        "    # Район Алматы по координатам. Для точности лучше добавить официальный GeoJSON.",
        "    try:",
        "        lat = float(lat)",
        "        lon = float(lon)",
        "    except Exception:",
        f"        return {UNKNOWN!r}",
        "",
        "    geojson = _load_districts_geojson()",
        "    if geojson:",
        "        result = _check_geojson_district(lat, lon, geojson)",
        "        if result:",
        "            result = str(result).replace(' (приближённо)', '').replace(' (??????????)', '').strip()",
        f"            for d in {DISTRICTS!r}:",
        "                if d in result:",
        "                    return d",
        "            return result",
        "",
        "    if not (43.00 <= lat <= 43.45 and 76.65 <= lon <= 77.20):",
        f"        return {UNKNOWN!r}",
        "",
        "    # Приближённые правила для 8 районов Алматы.",
        "    # Южные/горные зоны",
        "    if lon >= 76.97 and lat <= 43.28:",
        f"        return {D_MEDEU!r}",
        "    if lat <= 43.235 and 76.80 <= lon <= 76.97:",
        f"        return {D_BOSTANDYK!r}",
        "    if lat <= 43.25 and lon < 76.80:",
        f"        return {D_NAURYZBAY!r}",
        "",
        "    # Запад и северо-запад",
        "    if lat >= 43.255 and lon < 76.84:",
        f"        return {D_ALATAU!r}",
        "    if 43.18 <= lat < 43.285 and 76.76 <= lon < 76.89:",
        f"        return {D_AUEZOV!r}",
        "",
        "    # Центр",
        "    if 43.235 <= lat < 43.285 and 76.86 <= lon < 76.965:",
        f"        return {D_ALMALY!r}",
        "",
        "    # Север и северо-восток",
        "    if lat >= 43.30 and lon >= 76.89:",
        f"        return {D_TURKSIB!r}",
        "    if lat >= 43.255 and 76.84 <= lon < 76.98:",
        f"        return {D_ZHETYSU!r}",
        "",
        "    # Восток",
        "    if lon >= 76.94:",
        f"        return {D_MEDEU!r}",
        "",
        "    # Fallback: ближайший условный центр района.",
        "    centers = {",
        f"        {D_ALATAU!r}: (43.300, 76.790),",
        f"        {D_ALMALY!r}: (43.260, 76.920),",
        f"        {D_AUEZOV!r}: (43.235, 76.835),",
        f"        {D_BOSTANDYK!r}: (43.205, 76.900),",
        f"        {D_ZHETYSU!r}: (43.295, 76.910),",
        f"        {D_MEDEU!r}: (43.220, 77.020),",
        f"        {D_NAURYZBAY!r}: (43.205, 76.745),",
        f"        {D_TURKSIB!r}: (43.335, 76.980),",
        "    }",
        "    best_name = None",
        "    best_dist = 10 ** 9",
        "    for name, (clat, clon) in centers.items():",
        "        d = (lat - clat) ** 2 + ((lon - clon) * 0.73) ** 2",
        "        if d < best_dist:",
        "            best_dist = d",
        "            best_name = name",
        f"    return best_name or {UNKNOWN!r}",
        "",
    ]
    return "\n".join(lines)


def patch_geo_utils():
    path = Path("src/geo_utils.py")
    if not path.exists():
        raise FileNotFoundError("src/geo_utils.py not found")

    backup(path)
    s = path.read_text(encoding="utf-8", errors="replace")
    new_func = build_new_determine_district()

    pattern = r"def determine_district\(lat: float, lon: float\) -> str:[\s\S]*?(?=\n# ============================================================\n# Кэш геокодирования|\n# ============================================================\n# Обратное геокодирование|\n# ============================================================\n# Кэш Overpass|\Z)"
    s2, count = re.subn(pattern, new_func + "\n", s, count=1)

    if count == 0:
        raise RuntimeError("Could not find determine_district() in src/geo_utils.py")

    path.write_text(s2, encoding="utf-8")
    print("OK: determine_district replaced")


def patch_main():
    path = Path("main.py")
    if not path.exists():
        raise FileNotFoundError("main.py not found")

    backup(path)
    s = path.read_text(encoding="utf-8", errors="replace")

    district_list_code = "DISTRICT_FILTER_ITEMS = " + repr(DISTRICTS) + "\n"
    if "DISTRICT_FILTER_ITEMS" not in s:
        marker = "from src.ai_assistant import answer_question\n"
        if marker in s:
            s = s.replace(marker, marker + "\n" + district_list_code, 1)
        else:
            s = district_list_code + "\n" + s
        print("OK: DISTRICT_FILTER_ITEMS added")
    else:
        s = re.sub(r"DISTRICT_FILTER_ITEMS\s*=\s*\[[\s\S]*?\]\s*\n", district_list_code, s, count=1)
        print("OK: DISTRICT_FILTER_ITEMS replaced")

    # В фильтре районов должен быть только список из 8 районов
    replacement = "districts = DISTRICT_FILTER_ITEMS\n        self.filter_district.addItems(districts)"
    patterns = [
        r"if\s+\"district\"\s+in\s+df\.columns:\s*\n\s*districts\s*=\s*sorted\(\[[\s\S]*?\]\)\s*\n\s*self\.filter_district\.addItems\(districts\)",
        r"districts\s*=\s*sorted\(\[[\s\S]*?df\[\"district\"\][\s\S]*?\]\)\s*\n\s*self\.filter_district\.addItems\(districts\)",
        r"districts\s*=\s*\[[\s\S]*?\]\s*\n\s*self\.filter_district\.addItems\(districts\)",
    ]
    for pat in patterns:
        s2, count = re.subn(pat, replacement, s, count=1)
        if count:
            s = s2
            print("OK: district filter list replaced")
            break

    # Исправляем "Все районы", если оно стало ????
    s = re.sub(r"self\.filter_district\.addItem\(\"[^\"]*\?{2,}[^\"]*\"\)", f"self.filter_district.addItem({ALL_DISTRICTS!r})", s)
    s = s.replace('self.filter_district.addItem("Все районы")', f"self.filter_district.addItem({ALL_DISTRICTS!r})")
    s = re.sub(r"district\s*!=\s*\"[^\"]*\?{2,}[^\"]*\"", f"district != {ALL_DISTRICTS!r}", s)
    s = s.replace('district != "Все районы"', f"district != {ALL_DISTRICTS!r}")

    # После пересчёта district чистим старые хвосты
    target = (
        '            df["district"] = df.apply(\n'
        '                lambda r: determine_district(r["map_lat"], r["map_lon"]), axis=1\n'
        '            )\n'
    )
    clean = (
        '            df["district"] = df.apply(\n'
        '                lambda r: determine_district(r["map_lat"], r["map_lon"]), axis=1\n'
        '            )\n'
        '            df["district"] = (\n'
        '                df["district"].astype(str)\n'
        '                .str.replace(" (приближённо)", "", regex=False)\n'
        '                .str.replace(" (??????????)", "", regex=False)\n'
        '                .str.strip()\n'
        '            )\n'
    )
    if target in s and '.str.replace(" (??????????)", "", regex=False)' not in s:
        s = s.replace(target, clean, 1)
        print("OK: district cleanup after load added")

    path.write_text(s, encoding="utf-8")
    print("OK: main.py patched")


def clear_caches():
    for file in ["cache/geocode_cache.json", "cache/osm_cache.json"]:
        p = Path(file)
        if p.exists():
            p.write_text("{}", encoding="utf-8")
            print("Cleared:", p)


if __name__ == "__main__":
    patch_geo_utils()
    patch_main()
    clear_caches()
    print("DONE. Restart the app: python main.py")
