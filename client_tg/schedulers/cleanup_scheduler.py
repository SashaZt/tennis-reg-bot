# schedulers/cleanup_scheduler.py
"""
Ежедневный планировщик архивации прошедших тренировок.

Логика:
  - Запускается при старте бота, затем каждые 24 часа.
  - Ищет активные события, дата которых строго меньше сегодня.
  - Для каждого такого события:
      1. Если участников ≥ 1 — сохраняет снимок в таблицу training_history.
      2. Удаляет сообщение из Telegram-группы (если оно есть).
      3. Деактивирует событие (is_active = FALSE).
      4. Если событие цикличное — сразу создаёт следующее и публикует в группу.
  - Обычные события (разовые) просто удаляются без создания следующего.
"""
import asyncio
from datetime import date, datetime, timedelta

from aiogram import Bot
from config import config, logger
from database.connection import get_db
from database.models import Event
from services.history_service import HistoryService


class CleanupScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._task: asyncio.Task = None
        self._running = False

    def start(self) -> asyncio.Task:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("🧹 CleanupScheduler запущен")
        return self._task

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("🧹 CleanupScheduler остановлен")

    async def _loop(self):
        # Run once at startup to catch anything missed while bot was offline
        try:
            await self._cleanup_past_events()
        except Exception as e:
            logger.error(f"❌ CleanupScheduler ошибка при старте: {e}")

        # Then run every day at 00:05
        while self._running:
            await self._sleep_until_next_run()
            if not self._running:
                break
            try:
                await self._cleanup_past_events()
            except Exception as e:
                logger.error(f"❌ CleanupScheduler ошибка: {e}")

    @staticmethod
    async def _sleep_until_next_run():
        """Sleep until next 00:05."""
        now = datetime.now()
        next_run = now.replace(hour=0, minute=5, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        seconds = (next_run - now).total_seconds()
        logger.info(f"🧹 CleanupScheduler: следующий запуск в {next_run.strftime('%d.%m %H:%M')} (через {int(seconds//3600)}ч {int((seconds%3600)//60)}м)")
        await asyncio.sleep(seconds)

    async def _cleanup_past_events(self):
        """Find all active past events, archive and deactivate them."""
        today_key = date.today().strftime("%Y%m%d")

        async with get_db() as db:
            async with db.execute(
                """SELECT id, title, event_date, event_time, location,
                          max_participants, price, created_by, is_active,
                          created_at, group_message_id, weekday, recurring_template_id
                   FROM events
                   WHERE is_active = TRUE
                   AND substr(event_date,7,4) || substr(event_date,4,2) || substr(event_date,1,2) < ?""",
                (today_key,),
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            logger.info("🧹 CleanupScheduler: нет прошедших событий для архивации")
        else:
            logger.info(f"🧹 CleanupScheduler: найдено {len(rows)} прошедших событий")
            for row in rows:
                await self._archive_event(row)

        await self._cleanup_old_history()

    async def _archive_event(self, row):
        """Archive one event: save history if 1+ participants, delete TG message,
        deactivate in DB, then create next occurrence for recurring templates."""
        event = Event(
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
            group_message_id=row[10],
            weekday=row[11],
        )
        event.recurring_template_id = row[12]

        try:
            # Collect registered participants
            async with get_db() as db:
                async with db.execute(
                    """SELECT u.first_name, u.last_name, u.username, u.telegram_id
                       FROM bookings b
                       JOIN users u ON b.user_id = u.id
                       WHERE b.event_id = ? AND b.status = 'registered'""",
                    (event.id,),
                ) as cursor:
                    booking_rows = await cursor.fetchall()

            participants = []
            for brow in booking_rows:
                name_parts = list(filter(None, [brow[0], brow[1]]))
                name = " ".join(name_parts) if name_parts else "Без имени"
                participants.append(
                    {
                        "name": name,
                        "username": f"@{brow[2]}" if brow[2] else None,
                        "telegram_id": brow[3],
                    }
                )

            # Save to history if 1+ participants; skip if 0
            await HistoryService.save_event_to_history(event, participants)

            # Delete Telegram group message
            if event.group_message_id:
                try:
                    await self.bot.delete_message(
                        chat_id=config.group_id,
                        message_id=event.group_message_id,
                    )
                    logger.info(f"🗑 Сообщение события {event.id} удалено из группы")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Не удалось удалить сообщение события {event.id}: {e}"
                    )

            # Deactivate event
            async with get_db() as db:
                await db.execute(
                    "UPDATE events SET is_active = FALSE WHERE id = ?", (event.id,)
                )
                await db.commit()

            recurring_label = (
                "🔁 цикличная" if event.recurring_template_id else "📌 обычная"
            )
            logger.success(
                f"✅ Архивировано: {event.title} {event.event_date} "
                f"[{recurring_label}, участников: {len(participants)}]"
            )

            # For recurring events: immediately create and publish the next occurrence
            if event.recurring_template_id:
                await self._create_next_recurring_event(event.recurring_template_id)

        except Exception as e:
            logger.error(f"❌ Ошибка архивации события {event.id}: {e}")

    async def _create_next_recurring_event(self, template_id: int):
        """Create and publish next occurrence of a recurring template right after archival."""
        from services.config_service import ConfigService
        from services.event_service import EventService
        from services.recurring_service import RecurringService
        from utils.get_data import get_topic_id_for_date, get_weekday_name
        from utils.group_formatters import GroupMessageFormatter

        if not await ConfigService.get_recurring_enabled():
            logger.info(f"🔁 Шаблон {template_id} — повторяющиеся выключены, следующее событие не создаётся")
            return

        tmpl = await RecurringService.get_template_by_id(template_id)
        if not tmpl or not tmpl.is_active:
            logger.info(f"🔁 Шаблон {template_id} неактивен — следующее событие не создаётся")
            return

        # Don't create if there's already an upcoming active event for this template
        already_has = await EventService.has_upcoming_event_for_template(template_id)
        if already_has:
            logger.info(
                f"🔁 Шаблон {template_id} ({tmpl.title}) — будущее событие уже существует"
            )
            return

        next_date = RecurringService.get_next_occurrence(tmpl.weekday)
        date_str = next_date.strftime("%d.%m.%Y")
        creator_id = await self._get_admin_db_id()

        try:
            event = await EventService.create_event_with_price(
                title=tmpl.title,
                event_date=date_str,
                event_time=tmpl.event_time,
                location=tmpl.location,
                created_by=creator_id,
                price=tmpl.price,
                recurring_template_id=tmpl.id,
            )

            is_kids = "дет" in tmpl.title.lower() or "ребенок" in tmpl.title.lower()
            topic_id = get_topic_id_for_date(date_str, is_kids=is_kids)

            text = await GroupMessageFormatter.format_group_event_message(event)
            keyboard = GroupMessageFormatter.create_group_keyboard(event.id)

            msg = await self.bot.send_message(
                chat_id=config.group_id,
                text=text,
                message_thread_id=topic_id,
                reply_markup=keyboard,
                parse_mode="MarkdownV2",
            )
            await EventService.update_group_message_id(event.id, msg.message_id)

            weekday_name = get_weekday_name(date_str)
            logger.success(
                f"📅 Следующее событие опубликовано: {tmpl.title} "
                f"на {date_str} ({weekday_name}), event_id={event.id}"
            )

        except Exception as e:
            logger.error(
                f"❌ Не удалось создать следующее событие для шаблона {template_id}: {e}"
            )

    async def _get_admin_db_id(self) -> int:
        """Return internal DB id of the first available admin."""
        async with get_db() as db:
            for admin_tg_id in config.admin_ids:
                async with db.execute(
                    "SELECT id FROM users WHERE telegram_id = ?", (admin_tg_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return row[0]
        return 0

    async def _cleanup_old_history(self):
        """Delete history records older than 2 weeks."""
        async with get_db() as db:
            async with db.execute(
                "SELECT COUNT(*) FROM training_history WHERE archived_at < datetime('now', '-14 days')"
            ) as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0

            if count == 0:
                logger.info("🧹 CleanupScheduler: старых записей истории нет")
                return

            await db.execute(
                "DELETE FROM training_history WHERE archived_at < datetime('now', '-14 days')"
            )
            await db.commit()

        logger.info(f"🧹 CleanupScheduler: удалено {count} старых записей истории (>14 дней)")
