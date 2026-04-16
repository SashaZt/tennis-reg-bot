# utils/validators.py
import re
from datetime import datetime


class Validators:
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Проверка формата даты DD.MM.YYYY"""
        try:
            datetime.strptime(date_str, "%d.%m.%Y")
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_time(time_str: str) -> bool:
        """Проверка формата времени HH:MM"""
        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_future_datetime(date_str: str, time_str: str) -> bool:
        """Проверка что дата и время в будущем"""
        try:
            event_datetime = datetime.strptime(
                f"{date_str} {time_str}", "%d.%m.%Y %H:%M"
            )
            return event_datetime > datetime.now()
        except ValueError:
            return False
