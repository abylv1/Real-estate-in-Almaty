# -*- coding: utf-8 -*-
"""
Конфигурация приложения: константы, цветовые схемы, границы Алматы.
"""

import os

# === Пути ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "cleaned_almaty_only.csv")
GEOCODE_CACHE_PATH = os.path.join(BASE_DIR, "cache", "geocode_cache.json")
OSM_CACHE_PATH = os.path.join(BASE_DIR, "cache", "osm_cache.json")
DISTRICTS_GEOJSON_PATH = os.path.join(BASE_DIR, "geo", "optional_almaty_districts.geojson")
MAP_TEMPLATE_PATH = os.path.join(BASE_DIR, "assets", "map_template.html")

# === Координаты Алматы ===
ALMATY_CENTER = (43.238949, 76.889709)
ALMATY_LAT_MIN = 43.00
ALMATY_LAT_MAX = 43.45
ALMATY_LON_MIN = 76.65
ALMATY_LON_MAX = 77.20

# === Цветовые категории по цене за м² (тенге) ===
PRICE_COLORS = [
    (1_000_000, None,       "#e53935", "≥ 1 000 000 ₸/м²"),   # красный
    (700_000,  1_000_000,   "#fb8c00", "700 000 – 1 000 000 ₸/м²"),  # оранжевый
    (500_000,  700_000,     "#fdd835", "500 000 – 700 000 ₸/м²"),  # жёлтый
    (300_000,  500_000,     "#43a047", "300 000 – 500 000 ₸/м²"),  # зелёный
    (None,     300_000,     "#1e88e5", "< 300 000 ₸/м²"),    # синий
]

def get_color(price_per_m2: float) -> str:
    """Возвращает цвет маркера по цене за м²."""
    if price_per_m2 is None or price_per_m2 != price_per_m2:  # NaN check
        return "#9e9e9e"
    for low, high, color, _ in PRICE_COLORS:
        if low is not None and high is None:
            if price_per_m2 >= low:
                return color
        elif low is not None and high is not None:
            if low <= price_per_m2 < high:
                return color
        elif low is None and high is not None:
            if price_per_m2 < high:
                return color
    return "#9e9e9e"

# === Расшифровка числовых кодов ===
BUILDING_TYPES = {
    1: "Кирпичный",
    2: "Панельный",
    3: "Монолитный",
}

RENOVATION_TYPES = {
    1: "Требует ремонта",
    2: "Хорошее состояние",
    4: "Черновая отделка",
    5: "Предчистовая",
    6: "Дизайнерский ремонт",
}

FURNITURE_TYPES = {
    1: "Без мебели",
    2: "С мебелью",
    3: "Частично меблирована",
}

TOILET_TYPES = {
    1: "Совмещённый",
    2: "Раздельный",
    3: "2 санузла",
    4: "Несколько санузлов",
}

PRIV_DORM_TYPES = {
    1: "Общежитие",
    2: "Квартира",
}

# === Настройки поиска ===
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT = 8  # секунд
NEARBY_RADIUS = 800  # метров

# === Категории объектов Overpass ===
OVERPASS_CATEGORIES = {
    "Школы": ('amenity', 'school'),
    "Университеты": ('amenity', 'university'),
    "Детские сады": ('amenity', 'kindergarten'),
    "Больницы": ('amenity', 'hospital'),
    "Клиники": ('amenity', 'clinic'),
    "Аптеки": ('amenity', 'pharmacy'),
    "Торговые центры": ('shop', 'mall'),
    "Магазины": ('shop', 'supermarket'),
    "Парки": ('leisure', 'park'),
    "Театры": ('amenity', 'theatre'),
    "Музеи": ('tourism', 'museum'),
    "Остановки": ('highway', 'bus_stop'),
    "Кафе/рестораны": ('amenity', 'cafe'),
    "Рестораны": ('amenity', 'restaurant'),
    "Спортивные объекты": ('leisure', 'sports_centre'),
}

# === Приблизительные границы районов Алматы ===
# Используются если geojson-файл отсутствует
ALMATY_DISTRICTS_APPROX = {
    "Медеуский": {
        "lat_min": 43.20, "lat_max": 43.45,
        "lon_min": 76.88, "lon_max": 77.20,
        "description": "Горный район в юго-восточной части Алматы. Включает Медеу, Шымбулак, Горный парк.",
    },
    "Бостандыкский": {
        "lat_min": 43.20, "lat_max": 43.40,
        "lon_min": 76.78, "lon_max": 76.92,
        "description": "Престижный район, проспект Аль-Фараби, Горный Гигант, КИМЭП.",
    },
    "Алмалинский": {
        "lat_min": 43.23, "lat_max": 43.35,
        "lon_min": 76.87, "lon_max": 77.00,
        "description": "Исторический центр, Золотой квадрат, ЦУМ, Арбат, Панфилова.",
    },
    "Жетысуский": {
        "lat_min": 43.28, "lat_max": 43.38,
        "lon_min": 77.00, "lon_max": 77.20,
        "description": "Восточная часть, микрорайоны.",
    },
    "Ауэзовский": {
        "lat_min": 43.18, "lat_max": 43.30,
        "lon_min": 76.78, "lon_max": 76.92,
        "description": "Западно-центральный район, рынок Алтын Орда.",
    },
    "Алатауский": {
        "lat_min": 43.05, "lat_max": 43.22,
        "lon_min": 76.78, "lon_max": 77.00,
        "description": "Южный район, Алатауский акимат.",
    },
    "Наурызбайский": {
        "lat_min": 43.08, "lat_max": 43.25,
        "lon_min": 76.65, "lon_max": 76.82,
        "description": "Юго-западный район, Наурызбай батыра.",
    },
    "Турксибский": {
        "lat_min": 43.28, "lat_max": 43.45,
        "lon_min": 76.82, "lon_max": 77.05,
        "description": "Северный район, Турксибский вокзал.",
    },
}

APP_TITLE = "Анализ рынка недвижимости Алматы"
APP_VERSION = "1.0.0"
