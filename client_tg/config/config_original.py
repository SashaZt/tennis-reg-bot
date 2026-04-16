#config/config.py
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")

# Отладочная информация
print(f"ADMIN_IDS из .env: '{ADMIN_IDS_STR}'")

# Обработка ADMIN_IDS
if ADMIN_IDS_STR:
    try:
        ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]
    except ValueError as e:
        print(f"Ошибка парсинга ADMIN_IDS: {e}")
        ADMIN_IDS = []
else:
    ADMIN_IDS = []

print(f"Обработанные ADMIN_IDS: {ADMIN_IDS}")
print(f"Тип ADMIN_IDS: {type(ADMIN_IDS)}")

# Настройки событий
MAX_PARTICIPANTS = 4
PRICE = 90
CURRENCY = "злотых"
CANCEL_HOURS_LIMIT = 24

# ID группы
GROUP_ID = -1002635671990

# Топики по дням недели (найденные через анализ)
WEEKDAY_TOPICS = {
    0: 37,  # Понедельник - https://t.me/c/MTA_tennis_academy/37
    1: 39,  # Вторник - https://t.me/c/MTA_tennis_academy/39
    2: 41,  # Среда - https://t.me/c/MTA_tennis_academy/41
    3: 43,  # Четверг - https://t.me/c/MTA_tennis_academy/43
    4: 46,  # Пятница - https://t.me/c/MTA_tennis_academy/46 
    5: 48,  # Суббота - https://t.me/c/MTA_tennis_academy/48
    6: 50,  # Воскресенье - https://t.me/c/MTA_tennis_academy/50
}

# Специальные топики
SPECIAL_TOPICS = {
    'kids': 71,  # Тренировка для детей - https://t.me/c/MTA_tennis_academy/71
}

WEEKDAY_NAMES = {
    0: "Понедельник",
    1: "Вторник", 
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье"
}

# Доступные места проведения
LOCATIONS = {
    "1": "Piaseczyńska 71, 00-765 Warszawa",
    "2": "Solec 71, 00-765 Warszawa"
}

# Текст условий
CONDITIONS_TEXT = """📋 Условия:
Отмена возможна не позднее чем за 24 часа до тренировки. При более позднем отказе занятие подлежит оплате — разве что удастся найти замену."""

def get_weekday_from_date(date_str: str) -> int:
    """Получить день недели из даты в формате ДД.ММ.ГГГГ"""
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        weekday = date_obj.weekday()  # 0 = понедельник, 6 = воскресенье
        
        print(f"📅 Дата: {date_str}")
        print(f"📊 День недели (число): {weekday}")
        print(f"📋 День недели (название): {WEEKDAY_NAMES.get(weekday, 'Неизвестно')}")
        
        return weekday
    except ValueError as e:
        print(f"❌ Ошибка парсинга даты {date_str}: {e}")
        return 0  # По умолчанию понедельник

def get_topic_id_for_date(date_str: str, is_kids: bool = False) -> int:
    """Получить ID топика для определенной даты"""
    if is_kids:
        print(f"👶 Детская тренировка → топик {SPECIAL_TOPICS['kids']}")
        return SPECIAL_TOPICS['kids']
    
    weekday = get_weekday_from_date(date_str)
    topic_id = WEEKDAY_TOPICS.get(weekday, WEEKDAY_TOPICS[1])  # По умолчанию вторник
    
    print(f"🎯 Топик для дня {weekday}: {topic_id}")
    print(f"📍 Соответствие: {WEEKDAY_NAMES.get(weekday)} → топик {topic_id}")
    
    return topic_id

def get_weekday_name(date_str: str) -> str:
    """Получить название дня недели для даты"""
    weekday = get_weekday_from_date(date_str)
    return WEEKDAY_NAMES.get(weekday, "Неизвестный день")
