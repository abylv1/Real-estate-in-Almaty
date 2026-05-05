# -*- coding: utf-8 -*-
"""
Загрузка и очистка данных из CSV.
Вычисление цены за м², маркировка подозрительных координат.
"""

import pandas as pd
import numpy as np
import os
from src.config import (
    DATA_PATH, ALMATY_LAT_MIN, ALMATY_LAT_MAX, ALMATY_LON_MIN, ALMATY_LON_MAX,
    get_color, BUILDING_TYPES, RENOVATION_TYPES, FURNITURE_TYPES,
    TOILET_TYPES, PRIV_DORM_TYPES
)


def load_data() -> tuple[pd.DataFrame, list[str]]:
    """
    Загружает и очищает данные из CSV.
    Возвращает (DataFrame, список предупреждений).
    """
    warnings = []

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Файл данных не найден: {DATA_PATH}\n"
            "Пожалуйста, поместите файл cleaned_almaty_only.csv в папку data/"
        )

    df = pd.read_csv(DATA_PATH, low_memory=False)
    original_count = len(df)

    # --- Удаляем строки без координат ---
    df = df.dropna(subset=['map_lat', 'map_lon'])
    after_coords = len(df)
    if after_coords < original_count:
        warnings.append(f"Удалено {original_count - after_coords} строк без координат.")

    # --- Удаляем строки с live_square <= 0 ---
    df = df[pd.to_numeric(df['live_square'], errors='coerce').fillna(0) > 0].copy()
    after_square = len(df)
    if after_square < after_coords:
        warnings.append(f"Удалено {after_coords - after_square} строк с нулевой или отрицательной площадью.")

    # --- Приводим числовые типы ---
    for col in ['price', 'live_rooms', 'live_square', 'year', 'flat_floor', 'house_floor_num',
                'flat_building', 'flat_renovation', 'live_furniture', 'flat_toilet',
                'mortgage', 'flat_priv_dorm', 'house_complex_name', 'map_lat', 'map_lon']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- Вычисляем цену за м² ---
    df['price_per_m2'] = (df['price'] / df['live_square']).round(0)

    # --- Маркируем подозрительные координаты ---
    df['coords_suspicious'] = ~(
        (df['map_lat'] >= ALMATY_LAT_MIN) & (df['map_lat'] <= ALMATY_LAT_MAX) &
        (df['map_lon'] >= ALMATY_LON_MIN) & (df['map_lon'] <= ALMATY_LON_MAX)
    )
    suspicious_count = df['coords_suspicious'].sum()
    if suspicious_count > 0:
        warnings.append(
            f"{suspicious_count} объектов имеют координаты вне диапазона Алматы "
            f"(lat {ALMATY_LAT_MIN}–{ALMATY_LAT_MAX}, lon {ALMATY_LON_MIN}–{ALMATY_LON_MAX}). "
            "Они отмечены как подозрительные и скрыты по умолчанию."
        )

    # --- Цвет маркера ---
    df['color'] = df['price_per_m2'].apply(get_color)

    # --- Индекс строки как уникальный ID ---
    df = df.reset_index(drop=True)
    df['id'] = df.index

    return df, warnings


def format_price(value) -> str:
    """Форматирует цену в тенге."""
    if pd.isna(value):
        return "Нет данных"
    return f"{int(value):,} ₸".replace(",", " ")


def format_price_m2(value) -> str:
    """Форматирует цену за м²."""
    if pd.isna(value):
        return "Нет данных"
    return f"{int(value):,} ₸/м²".replace(",", " ")


def decode_building(code) -> str:
    if pd.isna(code):
        return "Нет данных"
    return BUILDING_TYPES.get(int(code), f"Тип {int(code)}")


def decode_renovation(code) -> str:
    if pd.isna(code):
        return "Нет данных"
    return RENOVATION_TYPES.get(int(code), f"Тип {int(code)}")


def decode_furniture(code) -> str:
    if pd.isna(code):
        return "Нет данных"
    return FURNITURE_TYPES.get(int(code), f"Тип {int(code)}")


def decode_toilet(code) -> str:
    if pd.isna(code):
        return "Нет данных"
    return TOILET_TYPES.get(int(code), f"Тип {int(code)}")


def decode_priv_dorm(code) -> str:
    if pd.isna(code):
        return "Нет данных"
    return PRIV_DORM_TYPES.get(int(code), f"Тип {int(code)}")


def format_complex_name(value) -> str:
    """Форматирует название ЖК. Если числовое — показывает как ID."""
    if pd.isna(value):
        return "Нет данных"
    try:
        # Числовое значение → показываем как ID
        int_val = int(float(value))
        return f"ID ЖК: {int_val}"
    except (ValueError, TypeError):
        return str(value)


def format_floor(flat_floor, house_floor_num) -> str:
    """Форматирует этаж."""
    f = None if pd.isna(flat_floor) else int(flat_floor)
    h = None if pd.isna(house_floor_num) else int(house_floor_num)
    if f is not None and h is not None:
        return f"{f} из {h}"
    elif f is not None:
        return str(f)
    return "Нет данных"


def format_mortgage(value) -> str:
    if pd.isna(value):
        return "Нет данных"
    return "Доступна" if int(value) == 1 else "Недоступна"


def get_property_dict(row: pd.Series) -> dict:
    """Преобразует строку DataFrame в удобный словарь для отображения."""
    return {
        "id": int(row["id"]),
        "price": format_price(row["price"]),
        "price_raw": float(row["price"]) if not pd.isna(row["price"]) else None,
        "price_per_m2": format_price_m2(row["price_per_m2"]),
        "price_per_m2_raw": float(row["price_per_m2"]) if not pd.isna(row["price_per_m2"]) else None,
        "rooms": int(row["live_rooms"]) if not pd.isna(row["live_rooms"]) else None,
        "square": float(row["live_square"]) if not pd.isna(row["live_square"]) else None,
        "floor": format_floor(row.get("flat_floor"), row.get("house_floor_num")),
        "year": int(row["year"]) if not pd.isna(row.get("year")) else None,
        "complex": format_complex_name(row.get("house_complex_name")),
        "building": decode_building(row.get("flat_building")),
        "renovation": decode_renovation(row.get("flat_renovation")),
        "furniture": decode_furniture(row.get("live_furniture")),
        "toilet": decode_toilet(row.get("flat_toilet")),
        "mortgage": format_mortgage(row.get("mortgage")),
        "priv_dorm": decode_priv_dorm(row.get("flat_priv_dorm")),
        "lat": float(row["map_lat"]),
        "lon": float(row["map_lon"]),
        "suspicious": bool(row.get("coords_suspicious", False)),
        "color": str(row.get("color", "#9e9e9e")),
    }
