# handlers/updater_admin.py
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config, logger

router = Router()

# Глобальная переменная для доступа к updater
updater = None


def set_updater(event_updater):
    """Установить ссылку на updater"""
    global updater
    updater = event_updater


@router.message(Command("update_events"))
async def manual_update_command(message: Message):
    """Ручное обновление событий"""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ У вас нет прав администратора")
        return

    if not updater:
        await message.answer("❌ Система обновлений не инициализирована")
        return

    await message.answer("🔄 Запускаю ручное обновление событий...")

    try:
        await updater.manual_update()
        await message.answer("✅ Обновление событий завершено успешно")
    except Exception as e:
        logger.error(f"Ошибка ручного обновления: {e}")
        await message.answer(f"❌ Ошибка при обновлении: {str(e)}")


@router.message(Command("updater_status"))
async def updater_status_command(message: Message):
    """Статус системы автообновления"""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ У вас нет прав администратора")
        return

    if not updater:
        await message.answer("❌ Система обновлений не инициализирована")
        return

    status = "🟢 Запущено" if updater.is_running else "🔴 Остановлено"
    interval_hours = updater.update_interval / 3600

    status_text = f"""📊 **Статус автообновления событий**

Состояние: {status}
⏱️ Интервал: {interval_hours:.1f} часов
🔄 Последнее обновление: проверьте логи

**Доступные команды:**
• `/update_events` - ручное обновление
• `/updater_start` - запустить автообновление
• `/updater_stop` - остановить автообновление
• `/updater_interval` - изменить интервал"""

    await message.answer(status_text, parse_mode="Markdown")


@router.message(Command("updater_start"))
async def start_updater_command(message: Message):
    """Запустить автообновление"""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ У вас нет прав администратора")
        return

    if not updater:
        await message.answer("❌ Система обновлений не инициализирована")
        return

    if updater.is_running:
        await message.answer("ℹ️ Автообновление уже запущено")
        return

    try:
        updater.start_updater()
        await message.answer("✅ Автообновление событий запущено")
    except Exception as e:
        logger.error(f"Ошибка запуска updater: {e}")
        await message.answer(f"❌ Ошибка запуска: {str(e)}")


@router.message(Command("updater_stop"))
async def stop_updater_command(message: Message):
    """Остановить автообновление"""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ У вас нет прав администратора")
        return

    if not updater:
        await message.answer("❌ Система обновлений не инициализирована")
        return

    if not updater.is_running:
        await message.answer("ℹ️ Автообновление уже остановлено")
        return

    try:
        updater.stop_updater()
        await message.answer("🛑 Автообновление событий остановлено")
    except Exception as e:
        logger.error(f"Ошибка остановки updater: {e}")
        await message.answer(f"❌ Ошибка остановки: {str(e)}")


@router.message(Command("updater_interval"))
async def set_interval_command(message: Message):
    """Установить интервал обновления"""
    if message.from_user.id not in config.admin_ids:
        await message.answer("❌ У вас нет прав администратора")
        return

    if not updater:
        await message.answer("❌ Система обновлений не инициализирована")
        return

    # Показываем кнопки с предустановленными интервалами
    builder = InlineKeyboardBuilder()
    intervals = [
        ("30 минут", 0.5),
        ("1 час", 1.0),
        ("2 часа", 2.0),
        ("3 часа", 3.0),
        ("6 часов", 6.0),
        ("12 часов", 12.0),
    ]

    for name, hours in intervals:
        builder.add(
            InlineKeyboardButton(text=name, callback_data=f"set_interval_{hours}")
        )

    builder.adjust(2)

    current_hours = updater.update_interval / 3600
    await message.answer(
        f"⏱️ **Настройка интервала обновления**\n\n"
        f"Текущий интервал: {current_hours:.1f} часов\n\n"
        f"Выберите новый интервал:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("set_interval_"))
async def set_interval_callback(callback: CallbackQuery):
    """Обработка установки интервала"""
    await callback.answer()

    if callback.from_user.id not in config.admin_ids:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return

    if not updater:
        await callback.answer(
            "❌ Система обновлений не инициализирована", show_alert=True
        )
        return

    try:
        hours = float(callback.data.split("_")[2])
        old_hours = updater.update_interval / 3600

        updater.set_interval(hours)

        await callback.message.edit_text(
            f"✅ **Интервал обновления изменен**\n\n"
            f"Было: {old_hours:.1f} часов\n"
            f"Стало: {hours:.1f} часов\n\n"
            f"Изменения вступят в силу при следующем цикле обновления.",
            parse_mode="Markdown",
        )

        logger.info(
            f"Интервал обновления изменен пользователем {callback.from_user.id}: {old_hours:.1f}ч → {hours:.1f}ч"
        )

    except Exception as e:
        logger.error(f"Ошибка установки интервала: {e}")
        await callback.answer("❌ Ошибка установки интервала", show_alert=True)


# Добавляем в админскую панель кнопку управления обновлениями
@router.callback_query(F.data == "admin_updater")
async def admin_updater_menu(callback: CallbackQuery):
    """Меню управления автообновлением в админ панели"""
    await callback.answer()

    if callback.from_user.id not in config.admin_ids:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return

    if not updater:
        await callback.message.edit_text("❌ Система обновлений не инициализирована")
        return

    status = "🟢 Запущено" if updater.is_running else "🔴 Остановлено"
    interval_hours = updater.update_interval / 3600

    builder = InlineKeyboardBuilder()

    if updater.is_running:
        builder.add(
            InlineKeyboardButton(text="🛑 Остановить", callback_data="updater_stop")
        )
    else:
        builder.add(
            InlineKeyboardButton(text="▶️ Запустить", callback_data="updater_start")
        )

    builder.add(
        InlineKeyboardButton(text="🔄 Обновить сейчас", callback_data="updater_manual"),
        InlineKeyboardButton(text="⏱️ Интервал", callback_data="updater_set_interval"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main"),
    )
    builder.adjust(1, 2, 1)

    try:
        await callback.message.edit_text(
            f"🔄 **Управление автообновлением**\n\n"
            f"Статус: {status}\n"
            f"Интервал: {interval_hours:.1f} часов\n\n"
            f"Система автоматически обновляет все активные события от текущей даты и вперед\\.",
            reply_markup=builder.as_markup(),
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.error(f"Ошибка отображения меню updater: {e}")


@router.callback_query(F.data == "updater_start")
async def start_updater_callback(callback: CallbackQuery):
    """Запуск через callback"""
    await callback.answer()

    if not updater or updater.is_running:
        await callback.answer("Уже запущено", show_alert=True)
        return

    updater.start_updater()
    await callback.answer("✅ Автообновление запущено", show_alert=True)
    await admin_updater_menu(callback)


@router.callback_query(F.data == "updater_stop")
async def stop_updater_callback(callback: CallbackQuery):
    """Остановка через callback"""
    await callback.answer()

    if not updater or not updater.is_running:
        await callback.answer("Уже остановлено", show_alert=True)
        return

    updater.stop_updater()
    await callback.answer("🛑 Автообновление остановлено", show_alert=True)
    await admin_updater_menu(callback)


@router.callback_query(F.data == "updater_manual")
async def manual_update_callback(callback: CallbackQuery):
    """Ручное обновление через callback"""
    await callback.answer("🔄 Запускаю обновление...", show_alert=True)

    if not updater:
        await callback.answer("Система не инициализирована", show_alert=True)
        return

    try:
        await updater.manual_update()
        await callback.answer("✅ Обновление завершено", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка ручного обновления: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)


@router.callback_query(F.data == "updater_set_interval")
async def set_interval_menu_callback(callback: CallbackQuery):
    """Меню установки интервала через callback"""
    await set_interval_command(callback.message)
