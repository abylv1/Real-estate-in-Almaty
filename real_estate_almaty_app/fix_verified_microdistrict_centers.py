# -*- coding: utf-8 -*-
"""
fix_verified_microdistrict_centers.py

Исправляет неправильные координаты некоторых микрорайонов.
Главное исправление: Жетысу-1/2/3/4 были ошибочно поставлены севернее.
Теперь они находятся в Ауэзовском районе рядом с Бауыржан Момышулы / Сарыарка.

Запускать из корня проекта:
python fix_verified_microdistrict_centers.py
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
    b = p.with_suffix(p.suffix + ".backup_verified_microdistrict_centers")
    if not b.exists():
        shutil.copyfile(p, b)
        print("Backup:", b)

override = r