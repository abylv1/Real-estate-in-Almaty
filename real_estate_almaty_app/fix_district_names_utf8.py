# -*- coding: utf-8 -*-
"""
fix_district_names_utf8.py

Исправляет вопросительные знаки в названиях районов Алматы.
Делает так, чтобы в фильтре были строго 8 районов:
Алатауский, Алмалинский, Ауэзовский, Бостандыкский,
Жетысуский, Медеуский, Наурызбайский, Турксибский.

Запускать из корня проекта:
python fix_district_names_utf8.py
"""

from pathlib import Path
import re
import shutil

DISTRICTS = [
    "\u0410\u043b\u0430\u0442\u0430\u0443\u0441\u043a\u0438\u0439",      # Алатауский
    "\u0410\u043b\u043c\u0430\u043b\u0438\u043d\u0441\u043a\u0438\u0439", # Алмалинский
    "\u0410\u0443\u044d\u0437\u043e\u0432\u0441\u043a\u0438\u0439",      # Ауэзовский
    "\u0411\u043e\u0441\u0442\u0430\u043d\u0434\u044b\u043a\u0441\u043a\u0438\u0439", # Бостандыкский
    "\u0416\u0435\u0442\u044b\u0441\u0443\u0441\u043a\u0438\u0439",      # Жетысуский
    "\u041c\u0435\u0434\u0435\u0443\u0441\u043a\u0438\u0439",           # Медеуский
    "\u041d\u0430\u0443\u0440\u044b\u0437\u0431\u0430\u0439\u0441\u043a\u0438\u0439", # Наурызбайский
    "\u0422\u0443\u0440\u043a\u0441\u0438\u0431\u0441\u043a\u0438\u0439", # Турксибский
]

ALL_DISTRICTS = "\u0412\u0441\u0435 \u0440\u0430\u0439\u043e\u043d\u044b"
UNKNOWN_DISTRICT = "\u0420\u0430\u0439\u043e\u043d \u043d\u0435 \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0451\u043d \u0442\u043e\u0447\u043d\u043e"


def backup_file(path: Path):
    if path.exists():
        backup = path.with_suffix(path.suffix + ".backup_district_utf8")
        if not backup.exists():
            shutil.copyfile(path, backup)
            print("Backup:", backup)


def patch_geo_utils():
    path = Path("src/geo_utils.py")
    if not path.exists():
        print("SKIP: src/geo_utils.py not found")
        return

    backup_file(path)
    s = path.read_text(encoding="utf-8", errors="replace")

    # Убираем добавление "(приближённо)" к району
    s = s.replace(
        '    if best:\n        suffix = "" if geojson else " (приближённо)"\n        return best + suffix',
        '    if best:\n        return best'
    )
    s = s.replace(
        '    if best:\n        suffix = "" if geojson else " (??????????)"\n        return best + suffix',
        '    if best:\n        return best'
    )

    s = re.sub(
        r'if best:\s*\n\s*suffix\s*=\s*""\s*if\s*geojson\s*else\s*"[^"]*"\s*\n\s*return\s+best\s*\+\s*suffix',
        "if best:\n        return best",
        s,
        count=1,
    )

    # Исправляем возвращаемую строку неизвестного района
    s = re.sub(
        r'return\s+"[^"]*\?{3,}[^"]*"',
        f'return "{UNKNOWN_DISTRICT}"',
        s,
        count=1,
    )

    path.write_text(s, encoding="utf-8")
    print("OK: src/geo_utils.py patched")


def patch_main():
    path = Path("main.py")
    if not path.exists():
        print("SKIP: main.py not found")
        return

    backup_file(path)
    s = path.read_text(encoding="utf-8", errors="replace")

    district_list_code = "DISTRICT_FILTER_ITEMS = " + repr(DISTRICTS) + "\n"

    if "DISTRICT_FILTER_ITEMS" not in s:
        marker = "from src.ai_assistant import answer_question\n"
        if marker in s:
            s = s.replace(marker, marker + "\n" + district_list_code, 1)
        else:
            s = district_list_code + "\n" + s
        print("OK: added DISTRICT_FILTER_ITEMS")
    else:
        s = re.sub(
            r'DISTRICT_FILTER_ITEMS\s*=\s*\[[\s\S]*?\]\s*\n',
            district_list_code,
            s,
            count=1,
        )
        print("OK: replaced DISTRICT_FILTER_ITEMS")

    # Исправляем "Все районы"
    s = re.sub(
        r'self\.filter_district\.addItem\("[^"]*\?{2,}[^"]*"\)',
        f'self.filter_district.addItem("{ALL_DISTRICTS}")',
        s,
    )
    s = s.replace('self.filter_district.addItem("Все районы")', f'self.filter_district.addItem("{ALL_DISTRICTS}")')

    # Заменяем блок со списком районов на строго 8 районов
    replacement = "districts = DISTRICT_FILTER_ITEMS\n        self.filter_district.addItems(districts)"
    patterns = [
        r'if\s+"district"\s+in\s+df\.columns:\s*\n\s*districts\s*=\s*sorted\(\[[\s\S]*?\]\)\s*\n\s*self\.filter_district\.addItems\(districts\)',
        r'districts\s*=\s*sorted\(\[[\s\S]*?df\["district"\][\s\S]*?\]\)\s*\n\s*self\.filter_district\.addItems\(districts\)',
        r'districts\s*=\s*\[[\s\S]*?\]\s*\n\s*self\.filter_district\.addItems\(districts\)',
    ]

    changed = False
    for pat in patterns:
        s2, count = re.subn(pat, replacement, s, count=1)
        if count:
            s = s2
            changed = True
            print("OK: district list block replaced")
            break

    if not changed:
        print("NOTE: district list block not found. It may already be patched.")

    # В сравнении фильтра с "Все районы" могли появиться ????
    s = re.sub(
        r'district\s*!=\s*"[^"]*\?{2,}[^"]*"',
        f'district != "{ALL_DISTRICTS}"',
        s,
    )
    s = s.replace('district != "Все районы"', f'district != "{ALL_DISTRICTS}"')

    # Добавляем нормализацию района после df = self.df.copy() в _apply_filters, если ещё нет
    normalize_code = (
        '        if "district" in df.columns:\n'
        '            df["district"] = (\n'
        '                df["district"].astype(str)\n'
        '                .str.replace(" (приближённо)", "", regex=False)\n'
        '                .str.replace(" (??????????)", "", regex=False)\n'
        '                .str.strip()\n'
        '            )\n'
    )

    if '.str.replace(" (??????????)", "", regex=False)' not in s:
        s = s.replace("        df = self.df.copy()\n", "        df = self.df.copy()\n" + normalize_code, 1)
        print("OK: district normalization added")

    path.write_text(s, encoding="utf-8")
    print("OK: main.py patched")


def clear_cache():
    for file in ["cache/geocode_cache.json", "cache/osm_cache.json"]:
        p = Path(file)
        if p.exists():
            p.write_text("{}", encoding="utf-8")
            print("Cleared:", p)


if __name__ == "__main__":
    patch_geo_utils()
    patch_main()
    clear_cache()
    print("DONE. Now run: python main.py")
