# services/recurring_service.py
from datetime import date, timedelta
from typing import List, Optional

from database.connection import get_db
from database.models import RecurringTemplate

from config import config, logger


class RecurringService:

    @staticmethod
    async def create_template(
        title: str,
        weekday: int,
        event_time: str,
        location: str,
        created_by: int,
        price: int = 90,
        max_participants: int = 4,
    ) -> RecurringTemplate:
        """Создать шаблон повторяющегося события"""
        async with get_db() as db:
            cursor = await db.execute(
                """INSERT INTO recurring_templates
                   (title, weekday, event_time, location, created_by, price, max_participants)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    title,
                    weekday,
                    event_time,
                    location,
                    created_by,
                    price,
                    max_participants,
                ),
            )
            await db.commit()
            template_id = cursor.lastrowid
            logger.info(
                f"✅ Создан шаблон повторяющегося события ID={template_id}: {title} "
                f"({config.weekday_names.get(str(weekday))} {event_time})"
            )
            return RecurringTemplate(
                id=template_id,
                title=title,
                weekday=weekday,
                event_time=event_time,
                location=location,
                price=price,
                max_participants=max_participants,
                created_by=created_by,
            )

    @staticmethod
    async def get_templates(created_by: int = None) -> List[RecurringTemplate]:
        """Получить все активные шаблоны (опционально — только созданные указанным пользователем)"""
        async with get_db() as db:
            if created_by is not None:
                query = (
                    "SELECT * FROM recurring_templates "
                    "WHERE is_active = TRUE AND created_by = ? ORDER BY weekday, event_time"
                )
                params = (created_by,)
            else:
                query = (
                    "SELECT * FROM recurring_templates "
                    "WHERE is_active = TRUE ORDER BY weekday, event_time"
                )
                params = ()
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [RecurringTemplate(*row) for row in rows]

    @staticmethod
    async def get_template_by_id(template_id: int) -> Optional[RecurringTemplate]:
        """Получить шаблон по ID"""
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM recurring_templates WHERE id = ?", (template_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return RecurringTemplate(*row) if row else None

    @staticmethod
    async def deactivate_template(template_id: int) -> bool:
        """Деактивировать шаблон (мягкое удаление)"""
        async with get_db() as db:
            await db.execute(
                "UPDATE recurring_templates SET is_active = FALSE WHERE id = ?",
                (template_id,),
            )
            await db.commit()
            logger.info(f"🗑 Шаблон {template_id} деактивирован")
            return True

    @staticmethod
    def get_next_occurrence(weekday: int, days_ahead: int = 7) -> date:
        """
        Вернуть ближайшую дату с нужным днём недели,
        начиная не раньше чем через days_ahead дней от сегодня.
        Это гарантирует, что событие создаётся за 7-13 дней вперёд.
        """
        start = date.today() + timedelta(days=days_ahead)
        days_until = (weekday - start.weekday()) % 7
        return start + timedelta(days=days_until)

    @staticmethod
    async def get_templates_needing_events() -> List[RecurringTemplate]:
        """
        Вернуть активные шаблоны, для которых ещё не создано событие
        на следующую плановую дату (7-13 дней вперёд).
        """
        from services.event_service import EventService

        templates = await RecurringService.get_templates()
        needing = []
        for tmpl in templates:
            has_upcoming = await EventService.has_upcoming_event_for_template(tmpl.id)
            if not has_upcoming:
                needing.append(tmpl)
                next_date = RecurringService.get_next_occurrence(tmpl.weekday)
                logger.debug(
                    f"📅 Шаблон {tmpl.id} ({tmpl.title}) нуждается в событии на {next_date.strftime('%d.%m.%Y')}"
                )
        return needing
