# database/models.py
from datetime import datetime
from typing import Dict, List, Optional

from config import config


class User:
    def __init__(
        self,
        id: int,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        is_admin: bool = False,
        created_at: str = None,
    ):
        self.id = id
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.is_admin = is_admin
        self.created_at = created_at


class Event:
    def __init__(
        self,
        id: int,
        title: str,
        event_date: str,
        event_time: str,
        location: str,
        max_participants: int = 4,
        price: int = 90,
        created_by: int = None,
        is_active: bool = True,
        created_at: str = None,
        group_message_id: int = None,
        weekday: int = 0,
    ):
        self.id = id
        self.title = title
        self.event_date = event_date
        self.event_time = event_time
        self.location = location
        self.max_participants = max_participants
        self.price = price
        self.created_by = created_by
        self.is_active = is_active
        self.created_at = created_at
        self.group_message_id = group_message_id
        self.weekday = weekday

    def __repr__(self):
        return f"Event(id={self.id}, title='{self.title}', date='{self.event_date}', weekday={self.weekday})"


class Booking:
    def __init__(
        self,
        id: int,
        event_id: int,
        user_id: int,
        status: str = "registered",
        created_at: str = None,
        cancelled_at: str = None,
    ):
        self.id = id
        self.event_id = event_id
        self.user_id = user_id
        self.status = status
        self.created_at = created_at
        self.cancelled_at = cancelled_at


class RecurringTemplate:
    def __init__(
        self,
        id: int,
        title: str,
        weekday: int,
        event_time: str,
        location: str,
        price: int = 90,
        max_participants: int = 4,
        created_by: int = None,
        is_active: bool = True,
        created_at: str = None,
    ):
        self.id = id
        self.title = title
        self.weekday = weekday  # 0=Пн, 6=Вс
        self.event_time = event_time
        self.location = location
        self.price = price
        self.max_participants = max_participants
        self.created_by = created_by
        self.is_active = is_active
        self.created_at = created_at

    def __repr__(self):

        day = config.weekday_names.get(str(self.weekday), str(self.weekday))
        return f"RecurringTemplate(id={self.id}, title='{self.title}', {day} {self.event_time})"
