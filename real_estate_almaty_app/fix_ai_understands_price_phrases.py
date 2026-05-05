# -*- coding: utf-8 -*-
"""
fix_ai_understands_price_phrases.py

Исправляет классификацию вопросов типа:
- Почему такие цены?
- Почему цена такая высокая?
- Почему дорого?
- Откуда такая стоимость?
- Это дорого?
- Цена нормальная?

Раньше "цены" не проходило, потому что проверялось только "цена".

Запуск:
python fix_ai_understands_price_phrases.py
"""

from pathlib import Path
import re
import shutil
import py_compile

AI_PATH = Path("src/ai_assistant.py")
if not AI_PATH.exists():
    raise FileNotFoundError("src/ai_assistant.py не найден. Запусти из папки проекта.")

backup = Path("src/ai_assistant.py.backup_price_phrases")
if not backup.exists():
    shutil.copyfile(AI_PATH, backup)
    print("Backup created:", backup)
else:
    print("Backup already exists:", backup)

text = AI_PATH.read_text(encoding="utf-8", errors="replace")

NEW_FUNC = "def _ore_v3_is_real_estate(question: str) -> bool:\n    \"\"\"\n    Улучшенная проверка темы недвижимости.\n\n    Важно:\n    - \"Почему такие цены?\" теперь считается вопросом по недвижимости,\n      потому что пользователь находится внутри приложения недвижимости.\n    - Но явные не-недвижимые темы вроде \"курс валют\", \"погода\", \"столица Венгрии\"\n      всё равно не проходят.\n    \"\"\"\n    import re\n\n    q = _ore_v3_norm(question)\n\n    # Явные оффтопики — сразу False\n    hard_offtopic = [\n        \"столица\", \"венгрии\", \"погода\", \"курс валют\", \"футбол\", \"баскетбол\",\n        \"политика\", \"президент\", \"война\", \"напиши код\", \"реши пример\",\n        \"переведи\", \"рецепт\", \"фильм\", \"музыка\"\n    ]\n    if any(x in q for x in hard_offtopic):\n        return False\n\n    # Сильные признаки недвижимости\n    real_estate_stems = [\n        \"недвиж\", \"квартир\", \"объект\", \"жиль\", \"дом\", \"жк\", \"комнат\", \"площад\",\n        \"м2\", \"м²\", \"район\", \"микрорайон\", \"адрес\", \"локац\", \"карта\", \"алматы\",\n        \"инфраструкт\", \"рядом\", \"школ\", \"сад\", \"магазин\", \"трц\", \"аптек\", \"клиник\",\n        \"больниц\", \"парк\", \"метро\", \"останов\", \"университет\", \"кафе\", \"ресторан\",\n        \"риск\", \"торг\", \"скид\", \"покуп\", \"документ\", \"ипотек\", \"инвест\", \"аренд\",\n        \"ликвид\", \"ремонт\", \"мебель\", \"этаж\", \"год\", \"жить\", \"жизни\", \"провер\",\n        \"доход\", \"окупаем\", \"сравни\", \"анализ\", \"отчет\", \"отчёт\", \"паркинг\",\n        \"подъезд\", \"лифт\", \"двор\", \"шум\", \"безопас\", \"новострой\", \"застрой\"\n    ]\n    if any(s in q for s in real_estate_stems):\n        return True\n\n    # Цена/стоимость — в этом приложении трактуем как вопрос про недвижимость,\n    # если нет явного оффтопика выше.\n    price_phrases = [\n        \"цена\", \"цены\", \"цену\", \"ценой\", \"ценам\", \"ценах\", \"ценник\",\n        \"стоимость\", \"стоимости\", \"дорого\", \"дешево\", \"дёшево\",\n        \"дороже\", \"дешевле\", \"почему так дорого\", \"почему такие цены\",\n        \"почему такая цена\", \"откуда такая цена\", \"это дорого\",\n        \"нормальная цена\", \"рыночная цена\", \"переплата\", \"переоцен\"\n    ]\n    if any(p in q for p in price_phrases):\n        return True\n\n    # Короткие естественные фразы после выбора объекта\n    ambiguous_real_estate_phrases = [\n        \"почему так\", \"стоит брать\", \"стоит покупать\", \"нормальный вариант\",\n        \"хороший вариант\", \"плюсы\", \"минусы\", \"что скажешь\", \"оцени\"\n    ]\n    if any(p in q for p in ambiguous_real_estate_phrases):\n        return True\n\n    return False\n"

pattern = r"def _ore_v3_is_real_estate\(question: str\) -> bool:\n[\s\S]*?\n\ndef _ore_v3_warning\("
m = re.search(pattern, text)
if not m:
    raise RuntimeError("Не найден def _ore_v3_is_real_estate(...) в src/ai_assistant.py")

replacement = NEW_FUNC.rstrip() + "\n\n\ndef _ore_v3_warning("
text = text[:m.start()] + replacement + text[m.end():]

AI_PATH.write_text(text, encoding="utf-8")
py_compile.compile(str(AI_PATH), doraise=True)

print("OK: AI now understands price phrases like 'Почему такие цены?'")
print("Run: python main.py")
