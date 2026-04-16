# keyboards/user.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class UserKeyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню пользователя"""
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text="📋 Активные события", callback_data="user_events"
            ),
            InlineKeyboardButton(text="📝 Мои записи", callback_data="user_bookings"),
        )
        builder.adjust(1)
        return builder.as_markup()
