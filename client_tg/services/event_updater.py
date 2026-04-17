# services/event_updater.py (упрощенная версия)
import asyncio
from datetime import datetime
from typing import List

from database.models import Event
from utils.group_formatters import GroupMessageFormatter

from config import config, logger


class SimpleEventUpdater:
    """Простой обновлятор событий - только синхронизация БД → ТГ"""

    def __init__(self, bot):
        self.bot = bot
        self.is_running = False

    async def get_future_events(self) -> List[Event]:
        """Получить активные события текущего месяца"""
        from database.connection import get_db

        today = datetime.now().date()
        month_pattern = today.strftime("%m.%Y")

        async with get_db() as db:
            async with db.execute(
                """SELECT * FROM events
                   WHERE is_active = TRUE AND event_date LIKE ?
                   AND group_message_id IS NOT NULL
                   ORDER BY event_date, event_time""",
                (f"%.{month_pattern}",),
            ) as cursor:
                rows = await cursor.fetchall()

                events = []
                for row in rows:
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
                        group_message_id=row[10] if len(row) > 10 else None,
                        weekday=row[11] if len(row) > 11 else 0,
                    )
                    events.append(event)

                return events

    async def update_event_message(self, event: Event):
        """Обновить сообщение события в группе (только если существует)"""
        try:
            # Форматируем обновленное сообщение
            updated_text = await GroupMessageFormatter.format_group_event_message(event)
            updated_keyboard = GroupMessageFormatter.create_group_keyboard(event.id)

            # Пробуем обновить сообщение в группе
            await self.bot.edit_message_text(
                chat_id=config.group_id,
                message_id=event.group_message_id,
                text=updated_text,
                reply_markup=updated_keyboard,
                parse_mode="MarkdownV2",
            )

            logger.info(f"✅ Событие {event.id} ({event.title}) обновлено в ТГ")
            return True

        except Exception as e:
            error_msg = str(e).lower()

            if "message is not modified" in error_msg:
                logger.debug(
                    f"📋 Событие {event.id} не изменилось - обновление не требуется"
                )
                return True

            elif (
                "message to edit not found" in error_msg
                or "message not found" in error_msg
            ):
                logger.warning(
                    f"⚠️ Сообщение события {event.id} не найдено в ТГ - пропускаем"
                )
                # НЕ очищаем БД, НЕ создаем новое - просто пропускаем
                return False

            elif "flood control" in error_msg or "too many requests" in error_msg:
                logger.warning(f"🚫 Flood control для события {event.id} - пропускаем")
                return False

            else:
                logger.error(f"❌ Ошибка обновления события {event.id}: {e}")
                return False

    async def update_all_events(self):
        """Обновить все события (только существующие в ТГ)"""
        logger.info("🔄 Начинаю синхронизацию БД → ТГ...")

        events = await self.get_future_events()

        if not events:
            logger.info("ℹ️ Нет событий с group_message_id для обновления")
            return

        updated = 0
        skipped = 0
        errors = 0

        for event in events:
            logger.debug(
                f"🔍 Обрабатываю событие {event.id} (message_id: {event.group_message_id})"
            )

            success = await self.update_event_message(event)

            if success:
                updated += 1
            else:
                # Считаем как пропущенное (сообщение не найдено или другая ошибка)
                skipped += 1

            # Небольшая пауза между обновлениями
            await asyncio.sleep(1)

        logger.info(
            f"📊 Синхронизация завершена: ✅{updated} обновлено, ⏭️{skipped} пропущено из {len(events)} событий"
        )

    async def hourly_update_loop(self):
        """Цикл обновления каждый час"""
        self.is_running = True
        logger.info("🚀 Запущена синхронизация БД → ТГ каждый час")

        while self.is_running:
            try:
                await self.update_all_events()

                # Ждем час до следующего обновления
                await asyncio.sleep(3600)  # 3600 секунд = 1 час

            except Exception as e:
                logger.error(f"❌ Ошибка в цикле синхронизации: {e}")
                await asyncio.sleep(3600)  # Все равно ждем час

    def start(self):
        """Запустить автообновление"""
        if not self.is_running:
            return asyncio.create_task(self.hourly_update_loop())
        return None

    def stop(self):
        """Остановить автообновление"""
        self.is_running = False
        logger.info("🛑 Синхронизация БД → ТГ остановлена")

    async def manual_update(self):
        """Ручная синхронизация для отладки"""
        logger.info("🔧 Запуск ручной синхронизации БД → ТГ")
        await self.update_all_events()
