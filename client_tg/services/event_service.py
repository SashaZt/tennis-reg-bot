# services/event_service.py
from datetime import datetime
from typing import List, Optional

from config.logger import logger
from database.connection import get_db
from database.models import Event
from utils.get_data import get_weekday_from_date


class EventService:
    @staticmethod
    async def create_event(
        title: str, event_date: str, event_time: str, location: str, created_by: int
    ) -> Event:
        """Создать новое событие"""

        weekday = get_weekday_from_date(event_date)

        async with get_db() as db:
            cursor = await db.execute(
                """INSERT INTO events (title, event_date, event_time, location, created_by, weekday) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (title, event_date, event_time, location, created_by, weekday),
            )
            await db.commit()
            event_id = cursor.lastrowid

            logger.info(f"✅ Событие создано: ID {event_id}, день недели: {weekday}")

            return Event(
                id=event_id,
                title=title,
                event_date=event_date,
                event_time=event_time,
                location=location,
                created_by=created_by,
                weekday=weekday,
            )

    @staticmethod
    async def get_active_events() -> List[Event]:
        """Получить все активные события"""
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM events WHERE is_active = TRUE ORDER BY event_date, event_time"
            ) as cursor:
                rows = await cursor.fetchall()
                return [Event(*row[:12]) for row in rows]

    @staticmethod
    async def get_event_by_id(event_id: int) -> Optional[Event]:
        """Получить событие по ID"""
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM events WHERE id = ?", (event_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Event(
                        id=row[0],
                        title=row[1],
                        event_date=row[2],
                        event_time=row[3],
                        location=row[4],
                        max_participants=row[5],
                        price=row[6],
                        created_by=row[7],
                        is_active=row[8],
                        created_at=row[9],
                        group_message_id=row[10] if len(row) > 10 else None,
                        weekday=row[11] if len(row) > 11 else 0,
                    )
                return None

    @staticmethod
    async def deactivate_event(event_id: int) -> bool:
        """Деактивировать событие"""
        async with get_db() as db:
            await db.execute(
                "UPDATE events SET is_active = FALSE WHERE id = ?", (event_id,)
            )
            await db.commit()
            return True

    @staticmethod
    async def get_events_by_creator(
        creator_id: int, current_month_only: bool = False
    ) -> List[Event]:
        """Получить события созданные конкретным пользователем"""
        async with get_db() as db:
            if current_month_only:
                from datetime import date
                month_pattern = date.today().strftime("%m.%Y")
                async with db.execute(
                    "SELECT * FROM events WHERE created_by = ? AND event_date LIKE ? ORDER BY event_date, event_time",
                    (creator_id, f"%.{month_pattern}"),
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM events WHERE created_by = ? ORDER BY event_date, event_time",
                    (creator_id,),
                ) as cursor:
                    rows = await cursor.fetchall()
            return [Event(*row[:12]) for row in rows]

    @staticmethod
    async def update_group_message_id(event_id: int, group_message_id: int):
        """Обновить ID сообщения в группе"""
        async with get_db() as db:
            await db.execute(
                "UPDATE events SET group_message_id = ? WHERE id = ?",
                (group_message_id, event_id),
            )
            await db.commit()
            logger.info(
                f"✅ Обновлен group_message_id для события {event_id}: {group_message_id}"
            )

    @staticmethod
    async def update_event_field(event_id: int, field: str, value) -> bool:
        """Обновить произвольное поле события (title, price, event_date, event_time, location)"""
        allowed_fields = {"title", "price", "event_date", "event_time", "location"}
        if field not in allowed_fields:
            logger.warning(f"⚠️ Попытка обновить запрещённое поле: {field}")
            return False
        async with get_db() as db:
            await db.execute(
                f"UPDATE events SET {field} = ? WHERE id = ?", (value, event_id)
            )
            await db.commit()
            logger.info(f"✅ Обновлено поле '{field}' события {event_id}: {value}")
            return True

    @staticmethod
    async def get_notification_state(event_id: int) -> Optional[str]:
        """Получить состояние уведомления (assembled / dissolved / None)"""
        async with get_db() as db:
            async with db.execute(
                "SELECT notification_state FROM events WHERE id = ?", (event_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    @staticmethod
    async def set_notification_state(event_id: int, state: Optional[str]) -> None:
        """Установить состояние уведомления события"""
        async with get_db() as db:
            await db.execute(
                "UPDATE events SET notification_state = ? WHERE id = ?",
                (state, event_id),
            )
            await db.commit()
            logger.info(f"🔔 notification_state события {event_id} → {state}")

    @staticmethod
    async def create_event_with_price(
        title: str,
        event_date: str,
        event_time: str,
        location: str,
        created_by: int,
        price: int = 90,
        recurring_template_id: int = None,
    ) -> Event:
        """Создать событие с явно указанной ценой (используется планировщиком)"""
        weekday = get_weekday_from_date(event_date)
        async with get_db() as db:
            cursor = await db.execute(
                """INSERT INTO events
                   (title, event_date, event_time, location, created_by, weekday, price, recurring_template_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    title,
                    event_date,
                    event_time,
                    location,
                    created_by,
                    weekday,
                    price,
                    recurring_template_id,
                ),
            )
            await db.commit()
            event_id = cursor.lastrowid
            logger.info(
                f"✅ Событие создано (с ценой): ID {event_id}, weekday {weekday}, price {price}"
            )
            return Event(
                id=event_id,
                title=title,
                event_date=event_date,
                event_time=event_time,
                location=location,
                created_by=created_by,
                weekday=weekday,
                price=price,
            )

    @staticmethod
    async def event_exists_for_template(template_id: int, event_date: str) -> bool:
        """Проверить существует ли уже событие из этого шаблона на данную дату"""
        async with get_db() as db:
            async with db.execute(
                """SELECT COUNT(*) FROM events
                   WHERE recurring_template_id = ? AND event_date = ? AND is_active = TRUE""",
                (template_id, event_date),
            ) as cursor:
                row = await cursor.fetchone()
                return (row[0] if row else 0) > 0
