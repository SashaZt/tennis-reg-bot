# schedulers/recurring_scheduler.py
"""
Ежедневный планировщик, который создаёт события в группе
на основе активных шаблонов повторяющихся тренировок.

Логика:
  - Запускается каждые 24 часа (при старте бота тоже).
  - Для каждого активного шаблона вычисляет следующую дату
    (ближайший день недели, начиная через 7 дней от сегодня).
  - Если событие из этого шаблона на эту дату ещё не существует —
    создаёт его и публикует в нужный топик Telegram-группы.
"""
import asyncio
from datetime import timedelta

from aiogram import Bot
from config import config, logger
from database.connection import get_db
from services.event_service import EventService
from services.recurring_service import RecurringService
from utils.get_data import get_topic_id_for_date, get_weekday_name
from utils.group_formatters import GroupMessageFormatter


class RecurringScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._task: asyncio.Task = None
        self._running = False

    def start(self) -> asyncio.Task:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("🔄 RecurringScheduler запущен")
        return self._task

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("🔄 RecurringScheduler остановлен")

    async def _loop(self):
        """Основной цикл: проверяем шаблоны раз в 24 часа."""
        while self._running:
            try:
                await self._create_upcoming_events()
            except Exception as e:
                logger.error(f"❌ RecurringScheduler ошибка: {e}")
            # Спим 24 часа
            await asyncio.sleep(86400)

    async def _create_upcoming_events(self):
        """Создать события для шаблонов, которым нужны новые записи."""
        templates = await RecurringService.get_templates_needing_events()

        if not templates:
            logger.info(
                "🔄 RecurringScheduler: все шаблоны уже имеют события на следующую неделю"
            )
            return

        # Берём ID любого активного админа для поля created_by
        creator_id = await self._get_admin_db_id()

        for tmpl in templates:
            next_date = RecurringService.get_next_occurrence(tmpl.weekday)
            date_str = next_date.strftime("%d.%m.%Y")

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

                # Определяем топик
                is_kids = "дет" in tmpl.title.lower() or "ребенок" in tmpl.title.lower()
                topic_id = get_topic_id_for_date(date_str, is_kids=is_kids)

                # Формируем и отправляем сообщение в группу
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
                    f"✅ Авто-событие создано: {tmpl.title} "
                    f"на {date_str} ({weekday_name}), event_id={event.id}"
                )

            except Exception as e:
                logger.error(
                    f"❌ Не удалось создать авто-событие для шаблона {tmpl.id} "
                    f"({tmpl.title}) на {date_str}: {e}"
                )

    async def _get_admin_db_id(self) -> int:
        """Вернуть internal DB id первого доступного администратора."""

        async with get_db() as db:
            for admin_tg_id in config.admin_ids:
                async with db.execute(
                    "SELECT id FROM users WHERE telegram_id = ?", (admin_tg_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return row[0]
        # Если пользователь ещё не в БД — вернём 0, поле nullable
        return 0
