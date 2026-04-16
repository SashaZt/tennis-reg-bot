# handlers/admin.py
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.admin import AdminKeyboards
from services.booking_service import BookingService
from services.event_service import EventService
from services.recurring_service import RecurringService
from services.user_service import UserService
from utils.formatters import MessageFormatter
from utils.get_data import get_topic_id_for_date, get_weekday_name
from utils.group_formatters import GroupMessageFormatter, escape_markdown_v2
from utils.validators import Validators

from config import config, logger

router = Router()


class CreateEventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_location = State()


class EditEventStates(StatesGroup):
    waiting_for_new_title = State()
    waiting_for_new_price = State()


class GatherChatStates(StatesGroup):
    waiting_for_invite_link = State()


class RecurringStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_weekday = State()
    waiting_for_time = State()
    waiting_for_location = State()


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ панель"""
    user_id = message.from_user.id

    if user_id not in config.admin_ids:
        await message.answer(
            f"❌ У вас нет прав администратора\n\nВаш ID: {user_id}\nРазрешенные ID: {config.admin_ids}"
        )
        return

    # Создаем или обновляем админа в БД
    await UserService.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        is_admin=True,
    )

    # Экранируем текст для MarkdownV2
    welcome_text = f"🔧 *Панель администратора*\n\n"
    welcome_text += (
        f"Добро пожаловать, {escape_markdown_v2(message.from_user.first_name)}\\!\n\n"
    )
    welcome_text += f"Доступные действия:"

    keyboard = AdminKeyboards.main_menu()
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="MarkdownV2")


@router.callback_query(F.data == "admin_create_event")
async def start_create_event(callback: CallbackQuery, state: FSMContext):
    """Начать создание события"""
    logger.info(
        f"DEBUG: admin_create_event вызван пользователем {callback.from_user.id}"
    )

    await callback.answer()

    if callback.from_user.id not in config.admin_ids:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return

    await state.set_state(CreateEventStates.waiting_for_title)

    # Создаем кнопку отмены
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))

    try:
        await callback.message.edit_text(
            f"➕ *Создание нового события*\n\n"
            f"Введите название тренировки:\n"
            f"Например: `Групповая тренировка`",
            reply_markup=builder.as_markup(),
            parse_mode="MarkdownV2",
        )
        logger.info("DEBUG: Сообщение успешно отредактировано")
    except Exception as e:
        logger.info(f"DEBUG: Ошибка при редактировании сообщения: {e}")


@router.callback_query(F.data == "admin_my_events")
async def show_admin_events(callback: CallbackQuery):
    """Показать события администратора"""
    logger.info(f"DEBUG: admin_my_events вызван пользователем {callback.from_user.id}")

    await callback.answer()

    user = await UserService.get_or_create_user(callback.from_user.id)
    events = await EventService.get_events_by_creator(user.id, current_month_only=True)

    if not events:
        try:
            await callback.message.edit_text(
                "📋 У вас нет событий в текущем месяце\n\n"
                "Используйте кнопку ➕ Создать событие",
                reply_markup=AdminKeyboards.main_menu(),
            )
        except Exception as e:
            logger.info(f"DEBUG: Ошибка при редактировании: {e}")
            await callback.message.answer(
                "📋 У вас нет созданных событий\n\n"
                "Используйте кнопку ➕ Создать событие"
            )
        return

    events_page = events[:10]
    message_text = MessageFormatter.format_admin_event_list(events_page)

    # Создаем кнопки для управления событиями
    builder = InlineKeyboardBuilder()
    for event in events_page:
        booking_count = await BookingService.get_booking_count(event.id)
        builder.add(
            InlineKeyboardButton(
                text=f"🏋️‍♂️ {event.title} ({booking_count}/4)",
                callback_data=f"admin_event_{event.id}",
            )
        )
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main"))
    builder.adjust(1)

    try:
        await callback.message.edit_text(
            message_text, reply_markup=builder.as_markup(), parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.info(f"DEBUG: Ошибка при показе событий: {e}")


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика для админа"""
    logger.info(f"DEBUG: admin_stats вызван пользователем {callback.from_user.id}")

    await callback.answer()

    user = await UserService.get_or_create_user(callback.from_user.id)
    events = await EventService.get_events_by_creator(user.id)

    total_events = len(events)
    active_events = len([e for e in events if e.is_active])

    total_bookings = 0
    for event in events:
        bookings = await BookingService.get_booking_count(event.id)
        total_bookings += bookings

    stats_text = f"""📊 **Статистика**

📋 Всего событий: {total_events}
✅ Активных событий: {active_events}
👥 Всего записей: {total_bookings}

📈 **Детали по событиям:**"""

    for event in events[:5]:  # Показываем только первые 5
        booking_count = await BookingService.get_booking_count(event.id)
        status = "🟢" if event.is_active else "🔴"
        stats_text += f"\n{status} {escape_markdown_v2(event.title)}: {booking_count}/4"

    keyboard = AdminKeyboards.main_menu()

    try:
        await callback.message.edit_text(
            stats_text, reply_markup=keyboard, parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.info(f"DEBUG: Ошибка при показе статистики: {e}")


@router.callback_query(F.data == "admin_main")
async def admin_main_menu(callback: CallbackQuery):
    """Возврат в главное меню админа"""
    await callback.answer()

    keyboard = AdminKeyboards.main_menu()

    try:
        await callback.message.edit_text(
            f"🔧 *Панель администратора*\n\nВыберите действие:",
            reply_markup=keyboard,
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.info(f"DEBUG: Ошибка в admin_main: {e}")


@router.callback_query(F.data.startswith("admin_event_"))
async def admin_event_detail(callback: CallbackQuery):
    """Детали события для админа с участниками"""
    logger.info(f"DEBUG: admin_event_ вызван пользователем {callback.from_user.id}")
    await callback.answer()

    event_id = int(callback.data.split("_")[2])
    event = await EventService.get_event_by_id(event_id)

    if not event:
        await callback.answer("❌ Событие не найдено", show_alert=True)
        return

    # Форматируем основное сообщение о событии
    message_text = await MessageFormatter.format_event_message(event)

    # Получаем участников
    bookings = await BookingService.get_event_bookings(event_id)

    if bookings:
        message_text += "\n\n👥 **Участники:**\n"

        for i, booking in enumerate(bookings, 1):
            user = await UserService.get_user_by_id(booking.user_id)
            if user:
                # Формируем имя участника
                name_parts = []

                if user.first_name:
                    # Экранируем специальные символы markdown
                    first_name = (
                        user.first_name.replace("*", "\\*")
                        .replace("_", "\\_")
                        .replace("`", "\\`")
                    )
                    name_parts.append(first_name)
                if user.last_name:
                    # Экранируем специальные символы markdown
                    last_name = (
                        user.last_name.replace("*", "\\*")
                        .replace("_", "\\_")
                        .replace("`", "\\`")
                    )
                    name_parts.append(last_name)

                display_name = " ".join(name_parts) if name_parts else "Без имени"

                # Добавляем username если есть (экранируем @)
                if user.username:
                    # username = user.username.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                    username = user.username.replace("*", "\\*").replace("`", "\\`")
                    display_name += f" (@{username})"

                message_text += f"{i}. {display_name}\n"
            else:
                message_text += f"{i}\\. Пользователь ID: {booking.user_id}\n"

        # Добавляем общий доход
        total_income = len(bookings) * 90
        message_text += f"\n💰 **Общий доход: {total_income} злотых**"
    else:
        message_text += "\n\n👥 **Участники:** Пока никто не записался"

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="✏️ Редактировать", callback_data=f"admin_edit_{event_id}"
        ),
        InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"admin_delete_{event_id}"
        ),
        InlineKeyboardButton(
            text="📱 Собрать в чате", callback_data=f"gather_chat_{event_id}"
        ),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_my_events"),
    )
    builder.adjust(2, 1, 1)

    try:
        await callback.message.edit_text(
            f"🔧 **Управление событием**\n\n{message_text}",
            reply_markup=builder.as_markup(),
            parse_mode="MarkdownV2",
        )
        logger.info("DEBUG: Сообщение успешно отправлено")
    except Exception as e:
        logger.info(f"DEBUG: Ошибка при показе деталей события: {e}")
        # Если проблема с markdown, отправляем без разметки
        try:
            # Убираем всю markdown разметку
            clean_text = (
                message_text.replace("**", "").replace("*", "").replace("`", "")
            )
            # clean_text = message_text.replace('**', '').replace('*', '').replace('_', '').replace('`', '')
            await callback.message.edit_text(
                f"🔧 Управление событием\n\n{clean_text}",
                reply_markup=builder.as_markup(),
            )
            logger.info("DEBUG: Сообщение отправлено без markdown")
        except Exception as e2:
            logger.info(f"DEBUG: Критическая ошибка: {e2}")
            await callback.answer(
                "❌ Произошла ошибка при отображении", show_alert=True
            )


@router.callback_query(F.data.startswith("admin_participants_"))
async def show_participants(callback: CallbackQuery):
    """Показать участников события"""
    logger.info(
        f"DEBUG: admin_participants_ вызван пользователем {callback.from_user.id}"
    )
    await callback.answer()

    event_id = int(callback.data.split("_")[2])
    bookings = await BookingService.get_event_bookings(event_id)

    if not bookings:
        await callback.answer("👥 Пока никто не записался", show_alert=True)
        return

    # Получаем информацию о событии
    event = await EventService.get_event_by_id(event_id)
    event_title = event.title if event else f"Событие ID {event_id}"

    participants_text = f"👥 **Участники события: {event_title}**\n\n"

    for i, booking in enumerate(bookings, 1):
        user = await UserService.get_user_by_id(booking.user_id)
        if user:
            # Формируем имя участника
            name_parts = []

            if user.first_name:
                name_parts.append(user.first_name)
            if user.last_name:
                name_parts.append(user.last_name)

            display_name = " ".join(name_parts) if name_parts else "Без имени"

            # Добавляем username если есть
            if user.username:
                display_name += f" (@{user.username})"

            participants_text += f"{i}. {display_name}\n"
            participants_text += f"   📱 ID: {user.telegram_id}\n\n"
        else:
            participants_text += f"{i}. Пользователь ID: {booking.user_id}\n\n"

    participants_text += f"💰 **Общий доход: {len(bookings) * 90} злотых**"

    await callback.message.answer(participants_text, parse_mode="MarkdownV2")


@router.callback_query(F.data.startswith("admin_delete_"))
async def confirm_delete_event(callback: CallbackQuery):
    """Подтверждение удаления события"""
    logger.info(f"DEBUG: admin_delete_ вызван пользователем {callback.from_user.id}")
    await callback.answer()

    event_id = int(callback.data.split("_")[2])
    event = await EventService.get_event_by_id(event_id)

    if not event:
        await callback.answer("❌ Событие не найдено", show_alert=True)
        return

    keyboard = AdminKeyboards.confirm_delete(event_id)
    try:
        await callback.message.edit_text(
            f"⚠️ **Подтверждение удаления**\n\n"
            f"Вы уверены, что хотите удалить событие:\n"
            f"**{event.title}**\n"
            f"📅 {event.event_date} в {event.event_time}?\n\n"
            f"❗️ Это действие нельзя отменить!",
            reply_markup=keyboard,
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.info(f"DEBUG: Ошибка при подтверждении удаления: {e}")


@router.callback_query(F.data.startswith("admin_confirm_delete_"))
async def delete_event(callback: CallbackQuery):
    """Удаление события"""
    logger.info(
        f"DEBUG: admin_confirm_delete_ вызван пользователем {callback.from_user.id}"
    )
    await callback.answer()

    event_id = int(callback.data.split("_")[3])

    # Деактивируем событие
    await EventService.deactivate_event(event_id)

    try:
        await callback.message.edit_text(
            "✅ Событие успешно удалено", reply_markup=AdminKeyboards.main_menu()
        )
    except Exception as e:
        logger.info(f"DEBUG: Ошибка при удалении: {e}")
        await callback.message.answer("✅ Событие успешно удалено")


@router.callback_query(F.data.startswith("admin_edit_"))
async def edit_event(callback: CallbackQuery):
    """Редактирование события — расширенное меню"""
    logger.info(f"DEBUG: admin_edit_ вызван пользователем {callback.from_user.id}")
    await callback.answer()

    event_id = int(callback.data.split("_")[2])
    event = await EventService.get_event_by_id(event_id)

    if not event:
        await callback.answer("❌ Событие не найдено", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            f"✏️ Редактирование события\n\n"
            f"{event.title}\n"
            f"📅 {event.event_date}  🕐 {event.event_time}\n"
            f"📍 {event.location}\n"
            f"💰 {event.price} злотых\n\n"
            f"Что хотите изменить?",
            reply_markup=AdminKeyboards.edit_menu(event_id),
        )
    except Exception as e:
        logger.info(f"DEBUG: Ошибка при показе меню редактирования: {e}")


@router.message(CreateEventStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Обработка названия события"""
    title = message.text.strip()

    if len(title) < 3:
        await message.answer("❌ Название должно содержать минимум 3 символа")
        return

    await state.update_data(title=title)
    await state.set_state(CreateEventStates.waiting_for_date)

    # Создаем кнопку отмены
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))

    # НОВОЕ сообщение, не редактируем предыдущее
    await message.answer(
        f"✅ Название: *{escape_markdown_v2(title)}*\n\n"
        f"📅 *Дата тренировки*\n\n"
        f"Введите дату в формате ДД\\.ММ\\.ГГГГ\n"
        f"Например: `15\\.07\\.2025`",
        reply_markup=builder.as_markup(),
        parse_mode="MarkdownV2",
    )


@router.message(CreateEventStates.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    """Обработка даты события"""
    date_str = message.text.strip()

    if not Validators.validate_date(date_str):
        await message.answer(
            f"❌ Неверный формат даты\\!\n"
            f"Используйте формат ДД\\.ММ\\.ГГГГ\n"
            f"Например: `15\\.07\\.2025`",
            parse_mode="MarkdownV2",
        )
        return

    await state.update_data(event_date=date_str)
    await state.set_state(CreateEventStates.waiting_for_time)

    # Создаем кнопку отмены
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))

    data = await state.get_data()
    await message.answer(
        f"✅ Название: *{escape_markdown_v2(data['title'])}*\n"
        f"✅ Дата: *{escape_markdown_v2(date_str)}*\n\n"
        f"🕐 *Время тренировки*\n\n"
        f"Введите время в формате ЧЧ:ММ\n"
        f"Например: `19:00`",
        reply_markup=builder.as_markup(),
        parse_mode="MarkdownV2",
    )


@router.message(CreateEventStates.waiting_for_time)
async def process_time(message: Message, state: FSMContext):
    """Обработка времени события"""
    time_str = message.text.strip()

    if not Validators.validate_time(time_str):
        await message.answer(
            f"❌ Неверный формат времени\\!\n"
            f"Используйте формат ЧЧ:ММ\n"
            f"Например: `19:00`",
            parse_mode="MarkdownV2",
        )
        return

    # Проверяем что дата и время в будущем
    data = await state.get_data()
    event_date = data.get("event_date")

    if not Validators.validate_future_datetime(event_date, time_str):
        await message.answer(
            f"❌ Дата и время должны быть в будущем\\!", parse_mode="MarkdownV2"
        )
        return

    await state.update_data(event_time=time_str)
    await state.set_state(CreateEventStates.waiting_for_location)

    keyboard = AdminKeyboards.location_menu()
    await message.answer(
        f"✅ Название: *{escape_markdown_v2(data['title'])}*\n"
        f"✅ Дата: *{escape_markdown_v2(event_date)}*\n"
        f"✅ Время: *{escape_markdown_v2(time_str)}*\n\n"
        f"📍 *Место проведения*\n\n"
        f"Выберите место проведения тренировки:",
        reply_markup=keyboard,
        parse_mode="MarkdownV2",
    )


@router.callback_query(
    F.data.startswith("location_"), CreateEventStates.waiting_for_location
)
async def process_location(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора локации и создание события в топике"""
    await callback.answer()

    location_id = callback.data.split("_")[1]

    if location_id not in config.locations:
        await callback.answer("❌ Неверная локация", show_alert=True)
        return

    location = config.locations[location_id]
    data = await state.get_data()

    # Создаем событие
    user = await UserService.get_or_create_user(callback.from_user.id)
    event = await EventService.create_event(
        title=data["title"],
        event_date=data["event_date"],
        event_time=data["event_time"],
        location=location,
        created_by=user.id,
    )

    await state.clear()

    # Определяем топик по дню недели

    # Проверяем, детская ли это тренировка
    is_kids = "дет" in data["title"].lower() or "ребенок" in data["title"].lower()

    topic_id = get_topic_id_for_date(data["event_date"], is_kids=is_kids)
    weekday_name = get_weekday_name(data["event_date"])

    if is_kids:
        topic_name = "Тренировка для детей"
    else:
        topic_name = f"Тренировка {weekday_name}"

    logger.info(
        f"🎯 Событие {event.id} будет размещено в топике {topic_id} ({topic_name})"
    )

    try:
        # Форматируем сообщение для группы

        group_message_text = await GroupMessageFormatter.format_group_event_message(
            event
        )
        group_keyboard = GroupMessageFormatter.create_group_keyboard(event.id)

        logger.info(
            f"📝 Отправляем сообщение в группу {config.group_id}, топик {topic_id}"
        )
        logger.info(
            f"📄 Текст сообщения (первые 200 символов): {group_message_text[:200]}..."
        )

        # Отправляем сообщение в соответствующий топик
        group_message = await callback.bot.send_message(
            chat_id=config.group_id,
            text=group_message_text,
            message_thread_id=topic_id,  # Это ключевой параметр для топика!
            reply_markup=group_keyboard,
            parse_mode="MarkdownV2",
        )

        logger.info(f"✅ Сообщение отправлено! Message ID: {group_message.message_id}")

        # Сохраняем ID сообщения в БД
        await EventService.update_group_message_id(event.id, group_message.message_id)

        # Простое сообщение об успехе БЕЗ markdown
        success_message = f"""✅ Событие создано и опубликовано!

🎾 {event.title}
📅 {event.event_date} ({topic_name})
🕐 {event.event_time}
📍 {location}

📨 Размещено в топике: {topic_name}
🆔 ID события: {event.id}

Пользователи смогут записываться через кнопки в группе."""

        await callback.message.edit_text(success_message)

        logger.info(f"✅ Событие {event.id} успешно создано в топике {topic_id}")

    except Exception as e:
        logger.info(f"❌ Ошибка при создании события в топике: {e}")
        logger.info(f"❌ Тип ошибки: {type(e)}")

        # Максимально простое сообщение об ошибке
        simple_error = f"Ошибка при публикации события. ID: {event.id}"

        try:
            await callback.message.edit_text(simple_error)
        except Exception as e2:
            logger.info(f"❌ Даже простое сообщение не отправляется: {e2}")
            try:
                # Последняя попытка - новое сообщение без форматирования
                await callback.message.answer(f"Событие создано. ID: {event.id}")
            except Exception as e3:
                logger.info(f"❌ Критическая ошибка: {e3}")
                # Хотя бы ответим на callback
                await callback.answer(
                    f"Событие создано! ID: {event.id}", show_alert=True
                )


@router.callback_query(F.data == "admin_cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await callback.answer()
    await state.clear()

    keyboard = AdminKeyboards.main_menu()
    await callback.message.edit_text(
        "❌ Действие отменено\n\n" "🔧 **Панель администратора**",
        reply_markup=keyboard,
        parse_mode="MarkdownV2",
    )


# ────────────────────────────────────────────────────────────────────
#  РЕДАКТИРОВАНИЕ: НАЗВАНИЕ
# ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.regexp(r"^edit_title_\d+$"))
async def start_edit_title(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    event_id = int(callback.data.split("_")[2])
    await state.set_state(EditEventStates.waiting_for_new_title)
    await state.update_data(event_id=event_id)

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_edit_{event_id}")
    )
    await callback.message.edit_text(
        "📝 Введите новое название тренировки:", reply_markup=builder.as_markup()
    )


@router.message(EditEventStates.waiting_for_new_title)
async def process_new_title(message: Message, state: FSMContext):
    new_title = message.text.strip()
    if len(new_title) < 3:
        await message.answer("❌ Название должно содержать минимум 3 символа")
        return

    data = await state.get_data()
    event_id = data["event_id"]
    await state.clear()

    await EventService.update_event_field(event_id, "title", new_title)
    await message.answer(
        f"✅ Название обновлено: {new_title}", reply_markup=AdminKeyboards.main_menu()
    )


# ────────────────────────────────────────────────────────────────────
#  РЕДАКТИРОВАНИЕ: ЦЕНА
# ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.regexp(r"^edit_price_\d+$"))
async def start_edit_price(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    event_id = int(callback.data.split("_")[2])
    await state.set_state(EditEventStates.waiting_for_new_price)
    await state.update_data(event_id=event_id)

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_edit_{event_id}")
    )
    await callback.message.edit_text(
        "💰 Введите новую цену (только число, в злотых):",
        reply_markup=builder.as_markup(),
    )


@router.message(EditEventStates.waiting_for_new_price)
async def process_new_price(message: Message, state: FSMContext):
    try:
        new_price = int(message.text.strip())
        if new_price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное число (например: 90)")
        return

    data = await state.get_data()
    event_id = data["event_id"]
    await state.clear()

    await EventService.update_event_field(event_id, "price", new_price)
    await message.answer(
        f"✅ Цена обновлена: {new_price} злотых",
        reply_markup=AdminKeyboards.main_menu(),
    )


# ────────────────────────────────────────────────────────────────────
#  УДАЛЕНИЕ УЧАСТНИКА ИЗ ТРЕНИРОВКИ
# ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.regexp(r"^remove_participant_\d+$"))
async def remove_participant_menu(callback: CallbackQuery):
    """Показать список участников для удаления"""
    await callback.answer()
    event_id = int(callback.data.split("_")[2])
    bookings = await BookingService.get_event_bookings(event_id)

    if not bookings:
        await callback.answer("👥 Нет записанных участников", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for booking in bookings:
        user = await UserService.get_user_by_id(booking.user_id)
        if user:
            name = (
                " ".join(filter(None, [user.first_name, user.last_name])) or "Без имени"
            )
            if user.username:
                name += f" (@{user.username})"
            builder.add(
                InlineKeyboardButton(
                    text=f"❌ {name}", callback_data=f"kick_user_{event_id}_{user.id}"
                )
            )
    builder.add(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_edit_{event_id}")
    )
    builder.adjust(1)

    await callback.message.edit_text(
        "👤 Выберите участника для удаления из тренировки:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.regexp(r"^kick_user_\d+_\d+$"))
async def kick_user_from_event(callback: CallbackQuery):
    """Принудительно отменить запись участника (без ограничения 24 ч)"""
    await callback.answer()
    parts = callback.data.split("_")
    event_id = int(parts[2])
    internal_user_id = int(parts[3])

    from database.connection import get_db

    async with get_db() as db:
        await db.execute(
            """UPDATE bookings SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP
               WHERE event_id = ? AND user_id = ? AND status = 'registered'""",
            (event_id, internal_user_id),
        )
        await db.commit()

    # Уведомить удалённого пользователя
    user = await UserService.get_user_by_id(internal_user_id)
    event = await EventService.get_event_by_id(event_id)
    if user and event:
        try:
            await callback.bot.send_message(
                user.telegram_id,
                f"ℹ️ Тренер отменил вашу запись на тренировку:\n"
                f"🎾 {event.title}\n"
                f"📅 {event.event_date} в {event.event_time}",
            )
        except Exception:
            pass  # пользователь мог не начать диалог с ботом

    await callback.message.edit_text(
        "✅ Участник удалён из тренировки",
        reply_markup=AdminKeyboards.edit_menu(event_id),
    )


# ────────────────────────────────────────────────────────────────────
#  СОБРАТЬ В ЧАТЕ
# ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.regexp(r"^gather_chat_\d+$"))
async def gather_chat_start(callback: CallbackQuery, state: FSMContext):
    """Начать сбор группы в отдельный чат — попросить ссылку"""
    await callback.answer()
    event_id = int(callback.data.split("_")[2])
    bookings = await BookingService.get_event_bookings(event_id)

    if not bookings:
        await callback.answer("👥 Нет записанных участников", show_alert=True)
        return

    await state.set_state(GatherChatStates.waiting_for_invite_link)
    await state.update_data(event_id=event_id)

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_edit_{event_id}")
    )

    await callback.message.edit_text(
        f"📱 Участников: {len(bookings)}\n\n"
        f"Введите пригласительную ссылку в чат\n"
        f"(например: https://t.me/+xxxxxx):",
        reply_markup=builder.as_markup(),
    )


@router.message(GatherChatStates.waiting_for_invite_link)
async def process_gather_link(message: Message, state: FSMContext):
    """Отправить ссылку всем участникам в личку"""
    invite_link = message.text.strip()
    data = await state.get_data()
    event_id = data["event_id"]
    await state.clear()

    event = await EventService.get_event_by_id(event_id)
    bookings = await BookingService.get_event_bookings(event_id)

    sent_ok = 0
    sent_fail = 0
    for booking in bookings:
        user = await UserService.get_user_by_id(booking.user_id)
        if not user:
            continue
        try:
            await message.bot.send_message(
                user.telegram_id,
                f"🎾 Тренер приглашает вас в чат тренировки!\n\n"
                f"📅 {event.title} — {event.event_date} в {event.event_time}\n\n"
                f"🔗 {invite_link}",
            )
            sent_ok += 1
        except Exception:
            sent_fail += 1

    await message.answer(
        f"✅ Ссылка отправлена: {sent_ok} участникам\n"
        f"{'⚠️ Не доставлено: ' + str(sent_fail) if sent_fail else ''}",
        reply_markup=AdminKeyboards.main_menu(),
    )


# ────────────────────────────────────────────────────────────────────
#  ПОВТОРЯЮЩИЕСЯ ТРЕНИРОВКИ
# ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "admin_recurring")
async def recurring_menu(callback: CallbackQuery):
    """Меню повторяющихся тренировок"""
    await callback.answer()
    await callback.message.edit_text(
        "🔄 Повторяющиеся тренировки\n\n"
        "Шаблоны публикуются автоматически каждую неделю.",
        reply_markup=AdminKeyboards.recurring_menu(),
    )


@router.callback_query(F.data == "recurring_list")
async def recurring_list(callback: CallbackQuery):
    """Список активных шаблонов"""
    await callback.answer()

    user = await UserService.get_or_create_user(callback.from_user.id)
    templates = await RecurringService.get_templates(created_by=user.id)

    try:
        if not templates:
            await callback.message.edit_text(
                "📋 Нет активных шаблонов.\n\nСоздайте первый через ➕ Создать шаблон.",
                reply_markup=AdminKeyboards.recurring_menu(),
            )
            return

        text = "📋 Активные шаблоны:\n\n"
        for tmpl in templates:
            day = config.weekday_names.get(str(tmpl.weekday), "?")
            text += f"• {tmpl.title} — {day} {tmpl.event_time}, {tmpl.price} зл.\n"

        await callback.message.edit_text(
            text + "\n\nНажмите на шаблон чтобы удалить:",
            reply_markup=AdminKeyboards.recurring_templates_list(templates),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.regexp(r"^recurring_delete_\d+$"))
async def recurring_delete(callback: CallbackQuery):
    """Деактивировать шаблон"""
    await callback.answer()

    template_id = int(callback.data.split("_")[2])
    tmpl = await RecurringService.get_template_by_id(template_id)
    if not tmpl:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"recurring_confirm_delete_{template_id}",
        ),
        InlineKeyboardButton(text="❌ Отмена", callback_data="recurring_list"),
    )
    builder.adjust(2)
    await callback.message.edit_text(
        f"⚠️ Удалить шаблон?\n\n{tmpl.title}\n"
        f"Новые события больше не будут создаваться автоматически.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.regexp(r"^recurring_confirm_delete_\d+$"))
async def recurring_confirm_delete(callback: CallbackQuery):
    await callback.answer()

    template_id = int(callback.data.split("_")[3])
    await RecurringService.deactivate_template(template_id)
    await callback.message.edit_text(
        "✅ Шаблон удалён", reply_markup=AdminKeyboards.recurring_menu()
    )


@router.callback_query(F.data == "recurring_create")
async def recurring_create_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания шаблона повторяющейся тренировки"""
    await callback.answer()
    await state.set_state(RecurringStates.waiting_for_title)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_recurring"))
    await callback.message.edit_text(
        "🔄 Создание повторяющегося шаблона\n\n" "Введите название тренировки:",
        reply_markup=builder.as_markup(),
    )


@router.message(RecurringStates.waiting_for_title)
async def recurring_process_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("❌ Название должно содержать минимум 3 символа")
        return
    await state.update_data(title=title)
    await state.set_state(RecurringStates.waiting_for_weekday)
    await message.answer(
        f"✅ Название: {title}\n\nВыберите день недели:",
        reply_markup=AdminKeyboards.weekday_menu(),
    )


@router.callback_query(
    F.data.regexp(r"^recurring_weekday_\d+$"), RecurringStates.waiting_for_weekday
)
async def recurring_process_weekday(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    weekday = int(callback.data.split("_")[2])
    await state.update_data(weekday=weekday)
    await state.set_state(RecurringStates.waiting_for_time)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_recurring"))

    await callback.message.edit_text(
        f"✅ День: {config.weekday_names.get(str(weekday))}\n\n"
        f"Введите время в формате ЧЧ:ММ (например: 19:00):",
        reply_markup=builder.as_markup(),
    )


@router.message(RecurringStates.waiting_for_time)
async def recurring_process_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    if not Validators.validate_time(time_str):
        await message.answer("❌ Неверный формат. Используйте ЧЧ:ММ, например: 19:00")
        return
    await state.update_data(event_time=time_str)
    await state.set_state(RecurringStates.waiting_for_location)
    await message.answer(
        f"✅ Время: {time_str}\n\nВыберите место проведения:",
        reply_markup=AdminKeyboards.location_menu(),
    )


@router.callback_query(
    F.data.startswith("location_"), RecurringStates.waiting_for_location
)
async def recurring_process_location(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора локации для шаблона (тот же callback location_<id>, но другое FSM-состояние)"""
    await callback.answer()
    location_id = callback.data.split("_")[1]
    if location_id not in config.locations:
        await callback.answer("❌ Неверная локация", show_alert=True)
        return

    location = config.locations[location_id]
    data = await state.get_data()
    await state.clear()

    user = await UserService.get_or_create_user(callback.from_user.id)
    template = await RecurringService.create_template(
        title=data["title"],
        weekday=data["weekday"],
        event_time=data["event_time"],
        location=location,
        created_by=user.id,
    )
    day = config.weekday_names.get(str(template.weekday), "")
    await callback.message.edit_text(
        f"✅ Шаблон создан!\n\n"
        f"🎾 {template.title}\n"
        f"📅 Каждый {day} в {template.event_time}\n"
        f"📍 {template.location}\n\n"
        f"Тренировки будут создаваться автоматически каждую неделю.",
        reply_markup=AdminKeyboards.recurring_menu(),
    )


# # DEBUG функция должна быть В САМОМ КОНЦЕ!
# @router.callback_query()
# async def debug_all_admin_callbacks(callback: CallbackQuery):
#     """Отладка всех callback'ов которые не обработались"""
#     logger.info(f"DEBUG: Необработанный callback от пользователя {callback.from_user.id}")
#     logger.info(f"DEBUG: Данные callback: {callback.data}")
#     logger.info(f"DEBUG: Пользователь админ: {callback.from_user.id in config.admin_ids}")

#     await callback.answer("🐛 DEBUG: Callback получен но не обработан", show_alert=True)


# @router.callback_query()
# async def debug_admin_callbacks(callback: CallbackQuery):
#     """Debug админских callback'ов"""
#     logger.info(f"🔧 ADMIN DEBUG: callback от {callback.from_user.id}")
#     logger.info(f"🔧 ADMIN Chat ID: {callback.message.chat.id}")
#     logger.info(f"🔧 ADMIN callback.data: '{callback.data}'")#     logger.info(f"🔧 ADMIN Chat ID: {callback.message.chat.id}")
#     logger.info(f"🔧 ADMIN callback.data: '{callback.data}'")
