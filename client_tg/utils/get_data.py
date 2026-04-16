from datetime import datetime

from config import config, logger


def get_weekday_from_date(date_str: str) -> int:
    """Получить день недели из даты в формате ДД.ММ.ГГГГ"""
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        weekday = date_obj.weekday()  # 0 = понедельник, 6 = воскресенье

        logger.info(f"📅 Дата: {date_str}")
        logger.info(f"📊 День недели (число): {weekday}")
        logger.info(
            f"📋 День недели (название): {config.weekday_names.get(str(weekday), 'Неизвестно')}"
        )

        return weekday
    except ValueError as e:
        logger.info(f"❌ Ошибка парсинга даты {date_str}: {e}")
        return 0  # По умолчанию понедельник


def get_topic_id_for_date(date_str: str, is_kids: bool = False) -> int:
    """Получить ID топика для определенной даты"""
    if is_kids:
        logger.info(f"👶 Детская тренировка → топик {config.special_topics.kids}")
        return config.special_topics.kids

    weekday = get_weekday_from_date(date_str)
    topic_id = config.weekday_topics.get(
        str(weekday), config.weekday_topics["1"]
    )  # По умолчанию вторник

    logger.info(f"🎯 Топик для дня {weekday}: {topic_id}")
    logger.info(
        f"📍 Соответствие: {config.weekday_names.get(str(weekday))} → топик {topic_id}"
    )

    return topic_id


def get_weekday_name(date_str: str) -> str:
    """Получить название дня недели для даты"""
    weekday = get_weekday_from_date(date_str)
    return config.weekday_names.get(str(weekday), "Неизвестный день")
