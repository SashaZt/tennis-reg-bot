# middleware/auth.py
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import config


class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки админских прав"""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        # Проверяем админские callback'и
        if (
            isinstance(event, CallbackQuery)
            and event.data
            and event.data.startswith("admin_")
        ):
            # Если пользователь НЕ админ - блокируем
            if event.from_user.id not in config.admin_ids:
                await event.answer("❌ У вас нет прав администратора", show_alert=True)
                return
            # Если пользователь админ - пропускаем дальше

        # Проверяем админские команды
        if (
            isinstance(event, Message)
            and event.text
            and event.text.startswith("/admin")
        ):
            # Команда /admin сама проверит права, просто пропускаем
            pass

        # Выполняем обработчик
        return await handler(event, data)
