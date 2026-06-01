# services/history_service.py
import json
from typing import Dict, List

from config import logger
from database.connection import get_db


class HistoryService:

    @staticmethod
    async def save_event_to_history(event, participants: List[Dict]) -> bool:
        """
        Save completed event snapshot. Skipped if fewer than 3 participants.
        participants: [{"name": "...", "username": "@...", "telegram_id": 123}]
        """
        count = len(participants)
        if count < 1:
            logger.info(
                f"📋 Событие {event.id} ({event.title} {event.event_date}) "
                f"не сохранено в историю: участников 0"
            )
            return False

        participants_json = json.dumps(participants, ensure_ascii=False)
        is_recurring = 1 if getattr(event, "recurring_template_id", None) else 0

        async with get_db() as db:
            await db.execute(
                """INSERT INTO training_history
                   (event_id, title, event_date, event_time, location, price,
                    participant_count, participants, is_recurring)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.id,
                    event.title,
                    event.event_date,
                    event.event_time,
                    event.location,
                    event.price,
                    count,
                    participants_json,
                    is_recurring,
                ),
            )
            await db.commit()

        logger.success(
            f"📚 История сохранена: {event.title} {event.event_date}, участников: {count}"
        )
        return True

    @staticmethod
    async def get_recent_history(limit: int = 10, offset: int = 0) -> List[Dict]:
        """Return history records ordered by date desc, newest first."""
        async with get_db() as db:
            async with db.execute(
                """SELECT id, event_id, title, event_date, event_time, location, price,
                          participant_count, participants, is_recurring, archived_at
                   FROM training_history
                   ORDER BY
                       substr(event_date,7,4) || substr(event_date,4,2) || substr(event_date,1,2) DESC,
                       event_time DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()

        result = []
        for row in rows:
            result.append(
                {
                    "id": row[0],
                    "event_id": row[1],
                    "title": row[2],
                    "event_date": row[3],
                    "event_time": row[4],
                    "location": row[5],
                    "price": row[6],
                    "participant_count": row[7],
                    "participants": json.loads(row[8]),
                    "is_recurring": bool(row[9]),
                    "archived_at": row[10],
                }
            )
        return result

    @staticmethod
    async def get_history_count() -> int:
        """Total number of records in history."""
        async with get_db() as db:
            async with db.execute("SELECT COUNT(*) FROM training_history") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
