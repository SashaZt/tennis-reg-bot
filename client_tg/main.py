# main.py - с инициализацией loguru
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from database.connection import init_database
from services.config_service import ConfigService

# Импортируем только нужные обработчики
from handlers import admin, callback, group, user, schedule_admin, schedule_callbacks
from schedulers.cleanup_scheduler import CleanupScheduler
from schedulers.recurring_scheduler import RecurringScheduler
from schedulers.schedule_scheduler import ScheduleScheduler

# Для обновления событий
from services.event_updater import SimpleEventUpdater

from config import config, logger


async def main():
    """Основная функция запуска бота"""

    # Настройка логирования ПЕРВЫМ ДЕЛОМ
    logger.info("=== Запуск бота ===")


    # Инициализируем базу данных
    await init_database()
    await ConfigService.seed_if_empty()

    # Инициализируем бота и диспетчер
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # Для автообновления
    updater = SimpleEventUpdater(bot)
    recurring_scheduler = RecurringScheduler(bot)
    cleanup_scheduler = CleanupScheduler(bot)
    schedule_scheduler = ScheduleScheduler(bot)

    dp = Dispatcher()

    # Порядок роутеров:
    dp.include_router(admin.router)             # Сначала админ
    dp.include_router(schedule_admin.router)    # Расписание (админ)
    dp.include_router(user.router)              # Пользователь
    dp.include_router(callback.router)          # Callback обычных событий
    dp.include_router(schedule_callbacks.router)# Callback расписания
    dp.include_router(group.router)             # В конце группа (универсальный)

    logger.info("Роутеры подключены, бот запускается...")

    # Запускаем автообновление, планировщики повторяющихся событий и архивации
    updater_task = updater.start()
    recurring_task = recurring_scheduler.start()
    cleanup_task = cleanup_scheduler.start()
    schedule_task = schedule_scheduler.start()

    try:
        logger.info("🚀 Бот запущен!")
        await dp.start_polling(bot)
    finally:
        updater.stop()
        recurring_scheduler.stop()
        cleanup_scheduler.stop()
        schedule_scheduler.stop()
        for task in (updater_task, recurring_task, cleanup_task, schedule_task):
            if task:
                task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
