# -*- coding: utf-8 -*-
"""
Вычисление статистики по датасету недвижимости.
"""

import pandas as pd
import numpy as np
from src.config import PRICE_COLORS


def compute_global_stats(df: pd.DataFrame) -> dict:
    """Вычисляет глобальную статистику по всему датасету."""
    valid = df[~df['coords_suspicious']].copy()
    ppm2 = valid['price_per_m2'].dropna()

    stats = {
        "total": len(df),
        "total_valid": len(valid),
        "avg_price": df['price'].mean(),
        "avg_price_m2": ppm2.mean(),
        "median_price_m2": ppm2.median(),
        "min_price_m2": ppm2.min(),
        "max_price_m2": ppm2.max(),
        "by_category": {},
    }

    # Количество по цветовым категориям
    for low, high, color, label in PRICE_COLORS:
        if low is not None and high is None:
            count = (valid['price_per_m2'] >= low).sum()
        elif low is not None and high is not None:
            count = ((valid['price_per_m2'] >= low) & (valid['price_per_m2'] < high)).sum()
        else:
            count = (valid['price_per_m2'] < high).sum()
        stats["by_category"][label] = {"count": int(count), "color": color}

    return stats


def compute_district_stats(df: pd.DataFrame) -> dict:
    """
    Вычисляет среднюю цену за м² по районам.
    Предполагает, что в df есть колонка 'district'.
    """
    if 'district' not in df.columns:
        return {}

    result = {}
    grouped = df.groupby('district')['price_per_m2']
    for district, group in grouped:
        vals = group.dropna()
        if len(vals) == 0:
            continue
        result[district] = {
            "avg": float(vals.mean()),
            "median": float(vals.median()),
            "count": int(len(vals)),
        }
    return result


def get_property_percentile(df: pd.DataFrame, price_per_m2: float) -> float:
    """Возвращает перцентиль объекта по price_per_m2 в датасете."""
    vals = df['price_per_m2'].dropna().values
    if len(vals) == 0 or np.isnan(price_per_m2):
        return 0.0
    return float(np.mean(vals < price_per_m2) * 100)


def get_district_avg(df: pd.DataFrame, district: str) -> float | None:
    """Возвращает среднюю цену за м² для указанного района."""
    if 'district' not in df.columns:
        return None
    sub = df[df['district'] == district]['price_per_m2'].dropna()
    if len(sub) == 0:
        return None
    return float(sub.mean())


def get_microdistrict_avg(df: pd.DataFrame, microdistrict: str) -> float | None:
    """Возвращает среднюю цену за м² для указанного микрорайона."""
    if 'microdistrict' not in df.columns or not microdistrict or microdistrict == "Не определён":
        return None
    sub = df[df['microdistrict'] == microdistrict]['price_per_m2'].dropna()
    if len(sub) == 0:
        return None
    return float(sub.mean())


def compare_to_average(price_per_m2: float, avg: float | None) -> str:
    """Сравнивает объект со средним значением района."""
    if avg is None or np.isnan(price_per_m2):
        return "Нет данных для сравнения"
    diff = price_per_m2 - avg
    pct = abs(diff / avg * 100) if avg != 0 else 0
    if abs(diff) < avg * 0.02:
        return "Примерно соответствует среднему по району"
    if diff > 0:
        return f"Дороже среднего по району на {pct:.1f}%"
    else:
        return f"Дешевле среднего по району на {pct:.1f}%"


def build_stats_html(global_stats: dict, district_stats: dict, selected_prop: dict | None = None,
                     df: pd.DataFrame | None = None) -> str:
    """Формирует HTML-блок статистики."""

    def fmt(val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "Нет данных"
        return f"{int(val):,}".replace(",", " ")

    lines = []
    lines.append('<div class="stats-block">')

    lines.append('<h3>📊 Общая статистика</h3>')
    lines.append(f'<p>Всего объектов: <b>{global_stats["total"]:,}</b></p>'.replace(",", " "))
    lines.append(f'<p>В границах Алматы: <b>{global_stats["total_valid"]:,}</b></p>'.replace(",", " "))
    lines.append(f'<p>Средняя цена: <b>{fmt(global_stats["avg_price"])} ₸</b></p>')
    lines.append(f'<p>Средняя цена/м²: <b>{fmt(global_stats["avg_price_m2"])} ₸</b></p>')
    lines.append(f'<p>Медианная цена/м²: <b>{fmt(global_stats["median_price_m2"])} ₸</b></p>')

    lines.append('<hr/><h3>🎨 По категориям цены</h3>')
    for label, info in global_stats["by_category"].items():
        color = info["color"]
        count = info["count"]
        lines.append(
            f'<p><span style="display:inline-block;width:12px;height:12px;'
            f'background:{color};border-radius:50%;margin-right:6px;"></span>'
            f'{label}: <b>{count}</b></p>'
        )

    if district_stats:
        lines.append('<hr/><h3>🏙️ Средняя цена/м² по районам</h3>')
        sorted_districts = sorted(district_stats.items(), key=lambda x: x[1]["avg"], reverse=True)
        for district, info in sorted_districts:
            lines.append(
                f'<p>{district}: <b>{fmt(info["avg"])} ₸/м²</b> '
                f'<span style="color:#888">({info["count"]} объектов)</span></p>'
            )

    if selected_prop and df is not None:
        ppm2 = selected_prop.get("price_per_m2_raw")
        district = selected_prop.get("district", "")
        microdistrict = selected_prop.get("microdistrict", "")

        lines.append('<hr/><h3>🏠 Выбранный объект</h3>')
        lines.append(f'<p>Цена за м²: <b>{selected_prop.get("price_per_m2", "—")}</b></p>')

        if ppm2:
            pct = get_property_percentile(df, ppm2)
            lines.append(f'<p>Перцентиль в датасете: <b>{pct:.1f}%</b></p>')

        d_avg = get_district_avg(df, district)
        if d_avg:
            cmp = compare_to_average(ppm2, d_avg)
            lines.append(f'<p>Сравнение с районом: <b>{cmp}</b></p>')
            lines.append(f'<p>Среднее по {district}: <b>{fmt(d_avg)} ₸/м²</b></p>')

        m_avg = get_microdistrict_avg(df, microdistrict)
        if m_avg:
            cmp_m = compare_to_average(ppm2, m_avg)
            lines.append(f'<p>Сравнение с микрорайоном: <b>{cmp_m}</b></p>')

    lines.append('</div>')
    return "\n".join(lines)
