# -*- coding: utf-8 -*-
"""
ИИ-ассистент для анализа недвижимости.
Без API-ключа работает на основе шаблонных правил.
При наличии ANTHROPIC_API_KEY использует Claude API.
"""

import os
import math
import requests
import json

# Попытка загрузить .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================================
# Вспомогательные функции форматирования
# ============================================================

def _fmt(val, suffix="") -> str:
    if val is None:
        return "нет данных"
    try:
        return f"{int(val):,}{suffix}".replace(",", " ")
    except (ValueError, TypeError):
        return str(val)


def _pct_diff(val, avg) -> str:
    if val is None or avg is None or avg == 0:
        return ""
    diff = (val - avg) / avg * 100
    if diff > 0:
        return f"на {abs(diff):.1f}% дороже среднего"
    elif diff < 0:
        return f"на {abs(diff):.1f}% дешевле среднего"
    return "примерно равно среднему"


# ============================================================
# Контекст о районах Алматы
# ============================================================

DISTRICT_CONTEXT = {
    "Медеуский": (
        "Медеуский район — один из самых престижных и дорогих в Алматы. "
        "Расположен у подножия гор, включает горнолыжный курорт Шымбулак, каток Медеу, "
        "живописные ущелья. Чистый воздух, развитая инфраструктура, близость к природе "
        "и статусный имидж обусловливают высокие цены на недвижимость."
    ),
    "Бостандыкский": (
        "Бостандыкский район — престижный и хорошо развитый район Алматы. "
        "Здесь расположены проспект Аль-Фараби, КИМЭП, крупные торговые центры, "
        "бизнес-центры и современные жилые комплексы. "
        "Отличная транспортная доступность и развитая инфраструктура делают этот район "
        "привлекательным для покупателей с высоким уровнем дохода."
    ),
    "Алмалинский": (
        "Алмалинский район — исторический центр Алматы. "
        "Здесь находится 'Золотой квадрат', улица Арбат, ЦУМ, Центральный парк, "
        "театры, музеи, посольства. "
        "Центральное расположение, насыщенная инфраструктура и культурные объекты "
        "традиционно поддерживают высокие цены на жильё."
    ),
    "Жетысуский": (
        "Жетысуский район расположен в восточной части Алматы. "
        "Это жилой район с развитой инфраструктурой, крупными микрорайонами "
        "и хорошей транспортной связью с центром. "
        "Цены умеренные по сравнению с центральными районами."
    ),
    "Ауэзовский": (
        "Ауэзовский район — один из крупнейших по населению в Алматы. "
        "Здесь расположены крупные базары (Алтын Орда), промышленные объекты, "
        "а также много жилых кварталов советской постройки. "
        "Цены, как правило, ниже, чем в центральных и горных районах."
    ),
    "Алатауский": (
        "Алатауский район — южный район, активно застраиваемый. "
        "Новые жилые комплексы и доступные цены привлекают молодые семьи. "
        "Инфраструктура активно развивается."
    ),
    "Наурызбайский": (
        "Наурызбайский район — юго-западный район Алматы, "
        "активно развивается. "
        "Относительно доступные цены и новые жилые массивы."
    ),
    "Турксибский": (
        "Турксибский район — северный район Алматы, исторически промышленный. "
        "Цены на жильё здесь традиционно ниже, чем в центральных районах."
    ),
}


INFRASTRUCTURE_POSITIVE = {
    "Школы", "Университеты", "Детские сады",
    "Торговые центры", "Парки", "Театры", "Музеи",
    "Больницы", "Клиники"
}

# ============================================================
# Основная функция: генерация ответа
# ============================================================

def answer_question(
    selected_property: dict,
    question: str,
    district_stats: dict,
    microdistrict_stats: dict | None,
    nearby_places: dict,
) -> str:
    """
    Генерирует ответ ИИ-ассистента на вопрос о выбранном объекте.
    Сначала пробует Anthropic Claude API, затем правиловую логику.
    """
    # Пробуем Anthropic API
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _answer_with_anthropic(
                api_key, selected_property, question,
                district_stats, microdistrict_stats, nearby_places
            )
        except Exception:
            pass

    # Правиловая логика
    return _answer_rule_based(
        selected_property, question, district_stats, microdistrict_stats, nearby_places
    )


def _build_context_text(
    selected_property: dict,
    district_stats: dict,
    microdistrict_stats: dict | None,
    nearby_places: dict
) -> str:
    """Строит текстовый контекст для ИИ."""
    prop = selected_property
    district = prop.get("district", "Неизвестный район")
    d_avg = district_stats.get(district, {}).get("avg")
    ppm2 = prop.get("price_per_m2_raw")

    lines = [
        f"Объект недвижимости:",
        f"  Тип: {prop.get('priv_dorm', '—')}",
        f"  Цена: {prop.get('price', '—')}",
        f"  Цена за м²: {prop.get('price_per_m2', '—')}",
        f"  Площадь: {prop.get('square', '—')} м²",
        f"  Комнат: {prop.get('rooms', '—')}",
        f"  Этаж: {prop.get('floor', '—')}",
        f"  Год постройки: {prop.get('year', '—')}",
        f"  Ремонт: {prop.get('renovation', '—')}",
        f"  Мебель: {prop.get('furniture', '—')}",
        f"  Тип здания: {prop.get('building', '—')}",
        f"  Ипотека: {prop.get('mortgage', '—')}",
        f"  ЖК: {prop.get('complex', '—')}",
        f"  Район: {district}",
        f"  Микрорайон: {prop.get('microdistrict', '—')}",
        f"  Адрес: {prop.get('address', '—')}",
    ]

    if d_avg:
        lines.append(f"  Средняя цена/м² по району {district}: {_fmt(d_avg)} ₸/м²")
        if ppm2:
            lines.append(f"  Сравнение с районом: {_pct_diff(ppm2, d_avg)}")

    # Объекты рядом
    if nearby_places and "_error" not in nearby_places:
        lines.append("\nОбъекты рядом:")
        for cat, items in nearby_places.items():
            if cat.startswith("_"):
                continue
            names = [f'{i["name"]} ({i["distance"]}м)' for i in items[:2]]
            lines.append(f"  {cat}: {', '.join(names)} (всего: {len(items)})")
    elif "_error" in nearby_places:
        lines.append(f"\nОбъекты рядом: {nearby_places['_error']}")

    return "\n".join(lines)


def _answer_with_anthropic(
    api_key: str,
    selected_property: dict,
    question: str,
    district_stats: dict,
    microdistrict_stats: dict | None,
    nearby_places: dict,
) -> str:
    """Отправляет запрос в Anthropic Claude API."""
    context = _build_context_text(selected_property, district_stats, microdistrict_stats or {}, nearby_places)
    district = selected_property.get("district", "")
    district_info = DISTRICT_CONTEXT.get(district, "")

    system_prompt = (
        "Ты — ИИ-ассистент по анализу рынка недвижимости Алматы, Казахстан. "
        "Ты отвечаешь только на русском языке. "
        "Ты анализируешь данные об объектах недвижимости и даёшь содержательные, честные ответы. "
        "Не выдумывай факты, которых нет в данных. "
        "Используй данные о районе, инфраструктуре, цене за м² и сравнении со средним. "
        f"\n\nКонтекст о районе {district}: {district_info}"
    )

    user_content = f"Данные об объекте:\n{context}\n\nВопрос пользователя: {question}"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 800,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"]


# ============================================================
# Правиловый ассистент (без API)
# ============================================================

def _answer_rule_based(
    selected_property: dict,
    question: str,
    district_stats: dict,
    microdistrict_stats: dict | None,
    nearby_places: dict,
) -> str:
    """Генерирует ответ на основе шаблонных правил."""
    prop = selected_property
    question_lower = question.lower()

    district = prop.get("district", "неизвестный район")
    ppm2 = prop.get("price_per_m2_raw")
    d_avg = district_stats.get(district, {}).get("avg")
    price_str = prop.get("price", "—")
    ppm2_str = prop.get("price_per_m2", "—")
    rooms = prop.get("rooms", "—")
    square = prop.get("square", "—")
    floor = prop.get("floor", "—")
    year = prop.get("year", "—")
    renovation = prop.get("renovation", "—")
    furniture = prop.get("furniture", "—")
    mortgage = prop.get("mortgage", "—")
    address = prop.get("address", "адрес не определён")
    microdistrict = prop.get("microdistrict", "не определён")

    # Сравнение с районом
    comparison_text = ""
    if ppm2 and d_avg:
        diff_pct = (ppm2 - d_avg) / d_avg * 100
        if abs(diff_pct) < 2:
            comparison_text = f"Цена за м² практически совпадает со средней по {district} ({_fmt(d_avg)} ₸/м²)."
        elif diff_pct > 0:
            comparison_text = (
                f"Цена за м² ({_fmt(ppm2)} ₸/м²) на {abs(diff_pct):.1f}% выше средней "
                f"по {district} ({_fmt(d_avg)} ₸/м²)."
            )
        else:
            comparison_text = (
                f"Цена за м² ({_fmt(ppm2)} ₸/м²) на {abs(diff_pct):.1f}% ниже средней "
                f"по {district} ({_fmt(d_avg)} ₸/м²)."
            )

    # Анализ инфраструктуры
    infra_parts = []
    total_nearby = 0
    if nearby_places and "_error" not in nearby_places:
        for cat, items in nearby_places.items():
            if cat.startswith("_"):
                continue
            total_nearby += len(items)
            if cat in INFRASTRUCTURE_POSITIVE and items:
                nearest = items[0]
                infra_parts.append(
                    f"{cat.lower()} (ближайший — {nearest['name']}, {nearest['distance']} м)"
                )

    # Контекст района
    district_ctx = DISTRICT_CONTEXT.get(district, "")

    # --- Формируем ответ в зависимости от вопроса ---

    if any(w in question_lower for w in ["цена", "почему", "стоит", "дорого", "дёшево", "дешево"]):
        answer = _answer_price(
            prop, district, district_ctx, ppm2, d_avg, comparison_text, infra_parts, total_nearby, year, renovation
        )

    elif any(w in question_lower for w in ["рядом", "инфраструктур", "что рядом", "вблизи"]):
        answer = _answer_nearby(prop, nearby_places, infra_parts, total_nearby)

    elif any(w in question_lower for w in ["подходит", "жить", "для жизни", "хорош", "рекоменд"]):
        answer = _answer_suitability(
            prop, district, district_ctx, ppm2, d_avg, comparison_text,
            infra_parts, total_nearby, year, renovation, furniture, floor, mortgage
        )

    elif any(w in question_lower for w in ["сравн", "средн", "район"]):
        answer = _answer_comparison(
            prop, district, ppm2, d_avg, comparison_text, district_stats
        )

    elif any(w in question_lower for w in ["история", "исторически", "почему в этом"]):
        answer = _answer_history(district, district_ctx, ppm2, d_avg, comparison_text)

    else:
        # Универсальный ответ
        answer = _answer_general(
            prop, district, district_ctx, ppm2, d_avg, comparison_text, infra_parts, total_nearby
        )

    return answer


def _answer_price(prop, district, district_ctx, ppm2, d_avg, comparison_text, infra_parts, total_nearby, year, renovation) -> str:
    parts = [f"💡 **Анализ цены**\n"]
    parts.append(f"Цена объекта составляет {prop.get('price', '—')}, что соответствует {prop.get('price_per_m2', '—')}.\n")

    if comparison_text:
        parts.append(comparison_text + "\n")

    if district_ctx:
        parts.append(f"\n🏙️ **О районе {district}:**\n{district_ctx}\n")

    if infra_parts:
        parts.append(f"\n🏗️ **Инфраструктура рядом** (в радиусе 800м):")
        parts.append("Обнаружены: " + ", ".join(infra_parts[:5]) + ".")
        parts.append("Развитая инфраструктура обычно положительно влияет на цену.\n")
    elif total_nearby == 0:
        parts.append("\nПо данным OSM, объектов инфраструктуры рядом найдено немного — это может отражать как реальную картину, так и неполноту данных карты.\n")

    if year and year < 1990:
        parts.append(f"\nЗдание построено в {year} году — старый фонд может влиять на цену в меньшую сторону.")
    elif year and year >= 2010:
        parts.append(f"\nЗдание относительно новое ({year} г.) — это поддерживает цену.")

    if renovation in ("Дизайнерский ремонт", "Хорошее состояние"):
        parts.append(f"Ремонт «{renovation}» — качественная отделка увеличивает привлекательность квартиры.")

    return "\n".join(parts)


def _answer_nearby(prop, nearby_places, infra_parts, total_nearby) -> str:
    parts = [f"📍 **Объекты рядом**\n"]

    if "_error" in (nearby_places or {}):
        return (
            "⚠️ Данные об объектах рядом недоступны. Проверьте подключение к интернету.\n\n"
            "После получения данных я смогу рассказать, какие школы, магазины, парки и "
            "другие объекты находятся поблизости от этой квартиры."
        )

    if not nearby_places or total_nearby == 0:
        return (
            "По данным OpenStreetMap в радиусе 800 м от объекта найдено мало инфраструктурных объектов. "
            "Это может означать, что данные OSM для этого района неполны, либо квартира расположена "
            "в жилом массиве с минимальной коммерческой застройкой.\n\n"
            "Рекомендуем проверить через 2ГИС или Google Maps для более полной картины."
        )

    parts.append(f"В радиусе 800 м от объекта обнаружено {total_nearby} объектов:\n")
    for cat, items in nearby_places.items():
        if cat.startswith("_") or not items:
            continue
        nearest = items[0]
        parts.append(
            f"• **{cat}** ({len(items)} шт.) — ближайший: {nearest['name']} ({nearest['distance']} м)"
        )

    if infra_parts:
        parts.append(
            f"\nНаличие {', '.join(infra_parts[:3])} вблизи объекта "
            "является позитивным фактором для жизни и стоимости недвижимости."
        )

    return "\n".join(parts)


def _answer_suitability(prop, district, district_ctx, ppm2, d_avg, comparison_text,
                        infra_parts, total_nearby, year, renovation, furniture, floor, mortgage) -> str:
    parts = [f"🏠 **Оценка квартиры для жизни**\n"]
    score_plus = []
    score_minus = []

    if infra_parts:
        score_plus.append(f"рядом есть инфраструктура ({', '.join(infra_parts[:3])})")

    if year and year >= 2005:
        score_plus.append(f"относительно новое здание ({year} г.)")
    elif year and year < 1980:
        score_minus.append(f"старый жилой фонд ({year} г.), возможен износ")

    if renovation in ("Дизайнерский ремонт", "Хорошее состояние"):
        score_plus.append(f"хорошее состояние ремонта ({renovation})")
    elif renovation == "Требует ремонта":
        score_minus.append("квартира требует ремонта")

    if furniture == "С мебелью":
        score_plus.append("квартира меблирована")

    if mortgage == "Доступна":
        score_plus.append("доступна ипотека")

    if ppm2 and d_avg and ppm2 < d_avg * 0.95:
        score_plus.append("цена ниже средней по району")
    elif ppm2 and d_avg and ppm2 > d_avg * 1.1:
        score_minus.append("цена выше средней по району")

    parts.append(f"**Район:** {district}")
    if district_ctx:
        parts.append(district_ctx[:200] + "..." if len(district_ctx) > 200 else district_ctx)

    if score_plus:
        parts.append("\n✅ **Плюсы:**")
        for p in score_plus:
            parts.append(f"  • {p.capitalize()}")

    if score_minus:
        parts.append("\n⚠️ **Моменты, на которые стоит обратить внимание:**")
        for m in score_minus:
            parts.append(f"  • {m.capitalize()}")

    if comparison_text:
        parts.append(f"\n💰 {comparison_text}")

    parts.append("\n\n_Оценка основана на доступных данных. Рекомендуем лично осмотреть квартиру._")
    return "\n".join(parts)


def _answer_comparison(prop, district, ppm2, d_avg, comparison_text, district_stats) -> str:
    parts = [f"📊 **Сравнение со средними показателями**\n"]

    parts.append(f"Объект: {prop.get('price_per_m2', '—')}\n")

    if comparison_text:
        parts.append(comparison_text)

    if district_stats:
        parts.append("\n**Средние цены за м² по районам Алматы:**")
        sorted_d = sorted(district_stats.items(), key=lambda x: x[1].get("avg", 0), reverse=True)
        for d_name, info in sorted_d:
            marker = " ◀ выбранный" if d_name == district else ""
            parts.append(f"  • {d_name}: {_fmt(info.get('avg'))} ₸/м²{marker}")

    return "\n".join(parts)


def _answer_history(district, district_ctx, ppm2, d_avg, comparison_text) -> str:
    parts = [f"📜 **Исторический контекст цен в районе {district}**\n"]

    if district_ctx:
        parts.append(district_ctx)

    if comparison_text:
        parts.append(f"\n💰 {comparison_text}")

    parts.append(
        "\n\nЦены на недвижимость в Алматы исторически формировались под влиянием "
        "близости к центру, развитости инфраструктуры, экологической обстановки, "
        "близости к горам, наличия деловых и торговых центров, а также "
        "престижности района."
    )
    return "\n".join(parts)


def _answer_general(prop, district, district_ctx, ppm2, d_avg, comparison_text, infra_parts, total_nearby) -> str:
    parts = [f"🔍 **Анализ объекта**\n"]
    parts.append(
        f"Квартира расположена в {district}, "
        f"площадь {prop.get('square', '—')} м², "
        f"{prop.get('rooms', '—')} комнат(ы), "
        f"этаж {prop.get('floor', '—')}.\n"
    )
    parts.append(f"Цена: {prop.get('price', '—')} ({prop.get('price_per_m2', '—')}).\n")

    if comparison_text:
        parts.append(comparison_text + "\n")

    if district_ctx:
        parts.append(f"\n{district_ctx}\n")

    if infra_parts:
        parts.append(
            f"\nРядом обнаружены: {', '.join(infra_parts[:4])}. "
            "Это положительно влияет на привлекательность локации."
        )
    elif total_nearby == 0 and prop.get("lat"):
        parts.append("\nДанные об инфраструктуре рядом не получены или объектов мало по данным OSM.")

    parts.append(
        "\n\nЕсли вас интересует конкретный аспект — "
        "спросите о цене, инфраструктуре, подходит ли квартира для жизни, "
        "или сравните её со средними ценами района."
    )
    return "\n".join(parts)
