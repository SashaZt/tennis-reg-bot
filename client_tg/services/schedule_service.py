# services/schedule_service.py
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from database.connection import get_db
from config import logger


class ScheduleService:

    # ── Templates ──────────────────────────────────────────────────────

    @staticmethod
    async def create_template(
        weekday: int,
        title: str,
        location: str,
        price: int,
        max_participants: int,
        created_by: int,
        is_kids: bool = False,
    ) -> int:
        async with get_db() as db:
            cursor = await db.execute(
                """INSERT INTO schedule_templates
                   (weekday, title, location, price, max_participants, created_by, is_kids)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (weekday, title, location, price, max_participants, created_by, is_kids),
            )
            await db.commit()
            return cursor.lastrowid

    @staticmethod
    async def add_slot(template_id: int, slot_time: str) -> int:
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT INTO schedule_template_slots (template_id, slot_time) VALUES (?, ?)",
                (template_id, slot_time),
            )
            await db.commit()
            return cursor.lastrowid

    @staticmethod
    async def get_templates(created_by: int = None) -> List[Dict]:
        async with get_db() as db:
            if created_by is not None:
                async with db.execute(
                    """SELECT id, weekday, title, location, price, max_participants,
                              created_by, is_active, is_kids
                       FROM schedule_templates
                       WHERE is_active = TRUE AND created_by = ?
                       ORDER BY weekday, title""",
                    (created_by,),
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    """SELECT id, weekday, title, location, price, max_participants,
                              created_by, is_active, is_kids
                       FROM schedule_templates
                       WHERE is_active = TRUE
                       ORDER BY weekday, title""",
                ) as cursor:
                    rows = await cursor.fetchall()
        return [_tmpl_row(r) for r in rows]

    @staticmethod
    async def get_template_by_id(template_id: int) -> Optional[Dict]:
        async with get_db() as db:
            async with db.execute(
                """SELECT id, weekday, title, location, price, max_participants,
                          created_by, is_active, is_kids
                   FROM schedule_templates WHERE id = ?""",
                (template_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return _tmpl_row(row) if row else None

    @staticmethod
    async def get_template_slots(template_id: int) -> List[str]:
        async with get_db() as db:
            async with db.execute(
                """SELECT slot_time FROM schedule_template_slots
                   WHERE template_id = ? AND is_active = TRUE
                   ORDER BY slot_time""",
                (template_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [r[0] for r in rows]

    @staticmethod
    async def deactivate_template(template_id: int):
        async with get_db() as db:
            await db.execute(
                "UPDATE schedule_templates SET is_active = FALSE WHERE id = ?",
                (template_id,),
            )
            await db.commit()

    # ── Instances ──────────────────────────────────────────────────────

    @staticmethod
    async def create_instance(
        template_id: int,
        instance_date: str,
        slots: List[Tuple[str, int]],
    ) -> int:
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT INTO schedule_instances (template_id, instance_date) VALUES (?, ?)",
                (template_id, instance_date),
            )
            instance_id = cursor.lastrowid
            for slot_time, max_p in slots:
                await db.execute(
                    """INSERT INTO schedule_slot_instances
                       (schedule_instance_id, slot_time, max_participants)
                       VALUES (?, ?, ?)""",
                    (instance_id, slot_time, max_p),
                )
            await db.commit()
        return instance_id

    @staticmethod
    async def get_instance_by_id(instance_id: int) -> Optional[Dict]:
        async with get_db() as db:
            async with db.execute(
                """SELECT si.id, si.template_id, si.instance_date, si.group_message_id,
                          st.weekday, st.title, st.location, st.price, st.is_kids
                   FROM schedule_instances si
                   JOIN schedule_templates st ON si.template_id = st.id
                   WHERE si.id = ?""",
                (instance_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return _inst_row(row) if row else None

    @staticmethod
    async def get_active_instances() -> List[Dict]:
        """Return all active instances for today and future (admin view)."""
        today_key = date.today().strftime("%Y%m%d")
        async with get_db() as db:
            async with db.execute(
                """SELECT si.id, si.template_id, si.instance_date, si.group_message_id,
                          st.weekday, st.title, st.location, st.price, st.is_kids
                   FROM schedule_instances si
                   JOIN schedule_templates st ON si.template_id = st.id
                   WHERE si.is_active = TRUE
                   AND substr(si.instance_date,7,4)||substr(si.instance_date,4,2)||substr(si.instance_date,1,2) >= ?
                   ORDER BY substr(si.instance_date,7,4)||substr(si.instance_date,4,2)||substr(si.instance_date,1,2)""",
                (today_key,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [_inst_row(r) for r in rows]

    @staticmethod
    async def get_past_active_instances() -> List[Dict]:
        today_key = date.today().strftime("%Y%m%d")
        async with get_db() as db:
            async with db.execute(
                """SELECT si.id, si.template_id, si.instance_date, si.group_message_id,
                          st.weekday, st.title, st.location, st.price, st.is_kids
                   FROM schedule_instances si
                   JOIN schedule_templates st ON si.template_id = st.id
                   WHERE si.is_active = TRUE
                   AND substr(si.instance_date,7,4)||substr(si.instance_date,4,2)||substr(si.instance_date,1,2) < ?""",
                (today_key,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [_inst_row(r) for r in rows]

    @staticmethod
    async def has_upcoming_instance(template_id: int) -> bool:
        today_key = date.today().strftime("%Y%m%d")
        async with get_db() as db:
            async with db.execute(
                """SELECT COUNT(*) FROM schedule_instances
                   WHERE template_id = ? AND is_active = TRUE
                   AND substr(instance_date,7,4)||substr(instance_date,4,2)||substr(instance_date,1,2) >= ?""",
                (template_id, today_key),
            ) as cursor:
                row = await cursor.fetchone()
        return (row[0] if row else 0) > 0

    @staticmethod
    async def deactivate_instance(instance_id: int):
        async with get_db() as db:
            await db.execute(
                "UPDATE schedule_instances SET is_active = FALSE WHERE id = ?",
                (instance_id,),
            )
            await db.commit()

    @staticmethod
    async def update_instance_message_id(instance_id: int, message_id: int):
        async with get_db() as db:
            await db.execute(
                "UPDATE schedule_instances SET group_message_id = ? WHERE id = ?",
                (message_id, instance_id),
            )
            await db.commit()

    # ── Slot instances ─────────────────────────────────────────────────

    @staticmethod
    async def get_slot_instances(instance_id: int) -> List[Dict]:
        async with get_db() as db:
            async with db.execute(
                """SELECT ssi.id, ssi.slot_time, ssi.max_participants,
                          COUNT(CASE WHEN sb.status = 'registered' THEN 1 END) AS booked
                   FROM schedule_slot_instances ssi
                   LEFT JOIN schedule_bookings sb ON sb.slot_instance_id = ssi.id
                   WHERE ssi.schedule_instance_id = ?
                   GROUP BY ssi.id
                   ORDER BY ssi.slot_time""",
                (instance_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            {"id": r[0], "slot_time": r[1], "max_participants": r[2], "booked": r[3]}
            for r in rows
        ]

    @staticmethod
    async def get_slot_instance_by_id(slot_id: int) -> Optional[Dict]:
        async with get_db() as db:
            async with db.execute(
                """SELECT ssi.id, ssi.slot_time, ssi.max_participants,
                          ssi.schedule_instance_id,
                          COUNT(CASE WHEN sb.status = 'registered' THEN 1 END) AS booked
                   FROM schedule_slot_instances ssi
                   LEFT JOIN schedule_bookings sb ON sb.slot_instance_id = ssi.id
                   WHERE ssi.id = ?
                   GROUP BY ssi.id""",
                (slot_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "slot_time": row[1], "max_participants": row[2],
            "schedule_instance_id": row[3], "booked": row[4],
        }

    # ── Bookings ───────────────────────────────────────────────────────

    @staticmethod
    async def get_user_booking_status(slot_id: int, user_id: int) -> Optional[str]:
        async with get_db() as db:
            async with db.execute(
                "SELECT status FROM schedule_bookings WHERE slot_instance_id = ? AND user_id = ?",
                (slot_id, user_id),
            ) as cursor:
                row = await cursor.fetchone()
        return row[0] if row else None

    @staticmethod
    async def register(slot_id: int, user_id: int) -> str:
        slot = await ScheduleService.get_slot_instance_by_id(slot_id)
        if not slot:
            return "not_found"
        status = await ScheduleService.get_user_booking_status(slot_id, user_id)
        if status == "registered":
            return "already"
        if slot["booked"] >= slot["max_participants"]:
            return "full"
        async with get_db() as db:
            if status == "cancelled":
                await db.execute(
                    """UPDATE schedule_bookings SET status = 'registered', cancelled_at = NULL
                       WHERE slot_instance_id = ? AND user_id = ?""",
                    (slot_id, user_id),
                )
            else:
                await db.execute(
                    "INSERT INTO schedule_bookings (slot_instance_id, user_id) VALUES (?, ?)",
                    (slot_id, user_id),
                )
            await db.commit()
        return "ok"

    @staticmethod
    async def cancel(slot_id: int, user_id: int) -> str:
        status = await ScheduleService.get_user_booking_status(slot_id, user_id)
        if status != "registered":
            return "not_registered"
        async with get_db() as db:
            await db.execute(
                """UPDATE schedule_bookings SET status = 'cancelled',
                   cancelled_at = CURRENT_TIMESTAMP
                   WHERE slot_instance_id = ? AND user_id = ?""",
                (slot_id, user_id),
            )
            await db.commit()
        return "ok"

    @staticmethod
    async def cancel_by_internal_ids(slot_id: int, user_id: int) -> bool:
        """Cancel booking by internal user DB id (for admin kick)."""
        async with get_db() as db:
            cursor = await db.execute(
                """UPDATE schedule_bookings SET status = 'cancelled',
                   cancelled_at = CURRENT_TIMESTAMP
                   WHERE slot_instance_id = ? AND user_id = ? AND status = 'registered'""",
                (slot_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    async def get_slot_participants(slot_id: int) -> List[Dict]:
        async with get_db() as db:
            async with db.execute(
                """SELECT u.id, u.first_name, u.last_name, u.username, u.telegram_id
                   FROM schedule_bookings sb
                   JOIN users u ON sb.user_id = u.id
                   WHERE sb.slot_instance_id = ? AND sb.status = 'registered'""",
                (slot_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            {
                "user_id": r[0],
                "name": " ".join(filter(None, [r[1], r[2]])) or "Без имени",
                "username": f"@{r[3]}" if r[3] else None,
                "telegram_id": r[4],
            }
            for r in rows
        ]

    # ── Reminders ──────────────────────────────────────────────────────

    @staticmethod
    async def get_remindable_bookings_for_tomorrow() -> List[Dict]:
        """Bookings for tomorrow's slots that haven't received a reminder yet."""
        tomorrow = (date.today() + timedelta(days=1)).strftime("%d.%m.%Y")
        async with get_db() as db:
            async with db.execute(
                """SELECT sb.id, u.telegram_id, ssi.slot_time,
                          si.instance_date, st.title, st.location
                   FROM schedule_bookings sb
                   JOIN users u ON sb.user_id = u.id
                   JOIN schedule_slot_instances ssi ON sb.slot_instance_id = ssi.id
                   JOIN schedule_instances si ON ssi.schedule_instance_id = si.id
                   JOIN schedule_templates st ON si.template_id = st.id
                   WHERE sb.status = 'registered'
                   AND sb.reminder_sent = FALSE
                   AND si.instance_date = ?
                   AND si.is_active = TRUE""",
                (tomorrow,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            {
                "booking_id": r[0],
                "telegram_id": r[1],
                "slot_time": r[2],
                "instance_date": r[3],
                "title": r[4],
                "location": r[5],
            }
            for r in rows
        ]

    @staticmethod
    async def mark_reminders_sent(booking_ids: List[int]):
        async with get_db() as db:
            for bid in booking_ids:
                await db.execute(
                    "UPDATE schedule_bookings SET reminder_sent = TRUE WHERE id = ?",
                    (bid,),
                )
            await db.commit()


# ── Private helpers ────────────────────────────────────────────────────

def _tmpl_row(r) -> Dict:
    return {
        "id": r[0], "weekday": r[1], "title": r[2], "location": r[3],
        "price": r[4], "max_participants": r[5], "created_by": r[6],
        "is_active": r[7], "is_kids": bool(r[8]) if len(r) > 8 else False,
    }


def _inst_row(r) -> Dict:
    return {
        "id": r[0], "template_id": r[1], "instance_date": r[2],
        "group_message_id": r[3], "weekday": r[4], "title": r[5],
        "location": r[6], "price": r[7],
        "is_kids": bool(r[8]) if len(r) > 8 else False,
    }
