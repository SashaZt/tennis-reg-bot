# main.py - с инициализацией loguru
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from database.connection import init_database

# Импортируем только нужные обработчики
from handlers import admin, callback, group, user
from schedulers.recurring_scheduler import RecurringScheduler

# Для обновления событий
from services.event_updater import SimpleEventUpdater

from config import config, logger


async def main():
    """Основная функция запуска бота"""

    # Настройка логирования ПЕРВЫМ ДЕЛОМ
    logger.info("=== Запуск бота ===")

    # Создаем директорию для базы данных
    os.makedirs("data", exist_ok=True)

    # Инициализируем базу данных
    await init_database()

    # Инициализируем бота и диспетчер
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # Для автообновления
    updater = SimpleEventUpdater(bot)
    recurring_scheduler = RecurringScheduler(bot)

    dp = Dispatcher()

    # Порядок роутеров:
    dp.include_router(admin.router)  # Сначала админ
    dp.include_router(user.router)  # Потом пользователь
    dp.include_router(callback.router)  # Потом callback
    dp.include_router(group.router)  # В конце группа (универсальный)

    logger.info("Роутеры подключены, бот запускается...")

    # Запускаем автообновление и планировщик повторяющихся событий
    updater_task = updater.start()
    recurring_task = recurring_scheduler.start()

    try:
        logger.info(
            "🚀 Бот запущен с автообновлением событий и планировщиком повторяющихся тренировок!"
        )
        await dp.start_polling(bot)
    finally:
        updater.stop()
        recurring_scheduler.stop()
        if updater_task:
            updater_task.cancel()
        if recurring_task:
            recurring_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
