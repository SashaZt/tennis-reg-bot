# keyboards/admin.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config


class AdminKeyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню администратора"""
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text="➕ Создать событие", callback_data="admin_create_event"
            ),
            InlineKeyboardButton(
                text="📋 Мои события", callback_data="admin_my_events"
            ),
            InlineKeyboardButton(
                text="🔄 Повторяющиеся", callback_data="admin_recurring"
            ),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def location_menu(locations: dict = None) -> InlineKeyboardMarkup:
        """Меню выбора локации. Принимает locations из БД; fallback — config.json."""
        if locations is None:
            locations = config.locations
        builder = InlineKeyboardBuilder()
        for location_id, location_name in locations.items():
            builder.add(
                InlineKeyboardButton(
                    text=f"📍 {location_name}", callback_data=f"location_{location_id}"
                )
            )
        builder.add(
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def event_management(event_id: int) -> InlineKeyboardMarkup:
        """Управление событием с редактированием"""
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text="✏️ Редактировать", callback_data=f"admin_edit_{event_id}"
            ),
            InlineKeyboardButton(
                text="🗑 Удалить", callback_data=f"admin_delete_{event_id}"
            ),
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_my_events"),
        )
        builder.adjust(2, 1)
        return builder.as_markup()

    @staticmethod
    def confirm_delete(event_id: int) -> InlineKeyboardMarkup:
        """Подтверждение удаления события"""
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text="✅ Да, удалить", callback_data=f"admin_confirm_delete_{event_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена", callback_data=f"admin_event_{event_id}"
            ),
        )
        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    def edit_menu(event_id: int) -> InlineKeyboardMarkup:
        """Расширенное меню редактирования события"""
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text="📝 Название", callback_data=f"edit_title_{event_id}"
            ),
            InlineKeyboardButton(
                text="💰 Цена", callback_data=f"edit_price_{event_id}"
            ),
            InlineKeyboardButton(text="📅 Дата", callback_data=f"edit_date_{event_id}"),
            InlineKeyboardButton(
                text="🕐 Время", callback_data=f"edit_time_{event_id}"
            ),
            InlineKeyboardButton(
                text="📍 Место", callback_data=f"edit_location_{event_id}"
            ),
            InlineKeyboardButton(
                text="👤 Удалить участника",
                callback_data=f"remove_participant_{event_id}",
            ),
            InlineKeyboardButton(
                text="📱 Собрать в чате", callback_data=f"gather_chat_{event_id}"
            ),
            InlineKeyboardButton(
                text="◀️ Назад", callback_data=f"admin_event_{event_id}"
            ),
        )
        builder.adjust(2, 2, 2, 1, 1)
        return builder.as_markup()

    @staticmethod
    def recurring_menu() -> InlineKeyboardMarkup:
        """Меню повторяющихся тренировок"""
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text="➕ Создать шаблон", callback_data="recurring_create"
            ),
            InlineKeyboardButton(text="📋 Мои шаблоны", callback_data="recurring_list"),
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="admin_main"),
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def weekday_menu() -> InlineKeyboardMarkup:
        """Выбор дня недели для шаблона"""
        builder = InlineKeyboardBuilder()
        for wd, name in config.weekday_names.items():
            builder.add(
                InlineKeyboardButton(text=name, callback_data=f"recurring_weekday_{wd}")
            )
        builder.add(
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_recurring")
        )
        builder.adjust(3, 3, 1, 1)
        return builder.as_markup()

    @staticmethod
    def recurring_templates_list(templates) -> InlineKeyboardMarkup:
        """Список шаблонов с кнопкой удаления каждого"""
        builder = InlineKeyboardBuilder()
        for tmpl in templates:
            day = config.weekday_names.get(str(tmpl.weekday), "?")
            builder.add(
                InlineKeyboardButton(
                    text=f"🗑 {tmpl.title} ({day} {tmpl.event_time})",
                    callback_data=f"recurring_delete_{tmpl.id}",
                )
            )
        builder.add(
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_recurring")
        )
        builder.adjust(1)
        return builder.as_markup()

    # ─── Настройки ───────────────────────────────────────────────────

    @staticmethod
    def settings_menu(default_price: int, locations: dict) -> InlineKeyboardMarkup:
        """Главное меню настроек."""
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text=f"💰 Цена по умолч.: {default_price} зл.",
                callback_data="settings_edit_price",
            ),
            InlineKeyboardButton(
                text=f"📍 Локации ({len(locations)})",
                callback_data="settings_locations",
            ),
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="admin_main"),
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def locations_manage_menu(locations: dict) -> InlineKeyboardMarkup:
        """Список локаций с кнопками удаления + кнопка добавить."""
        builder = InlineKeyboardBuilder()
        for key, name in locations.items():
            builder.add(
                InlineKeyboardButton(
                    text=f"🗑 {name}",
                    callback_data=f"settings_del_loc_{key}",
                )
            )
        builder.add(
            InlineKeyboardButton(text="➕ Добавить локацию", callback_data="settings_add_loc"),
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_settings"),
        )
        builder.adjust(1)
        return builder.as_markup()
