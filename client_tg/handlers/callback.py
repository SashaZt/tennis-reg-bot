# handlers/callback.py
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.inline import InlineKeyboards
from services.booking_service import BookingService
from services.event_service import EventService
from services.user_service import UserService
from utils.formatters import MessageFormatter

from config import logger

router = Router()


async def safe_edit_message(
    callback: CallbackQuery, text: str, reply_markup=None, parse_mode="MarkdownV2"
):
    """Безопасное редактирование сообщения с проверкой на дублирование"""
    try:
        await callback.message.edit_text(
            text, reply_markup=reply_markup, parse_mode=parse_mode
        )
    except Exception as e:
        # Если сообщение не изменилось, просто игнорируем ошибку
        if "message is not modified" in str(e).lower():
            await callback.answer("🔄 Информация актуальна")
        else:
            # Если другая ошибка, логируем её
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)
    except Exception as e:
        logger.error(f"[Telegram Markdown Error] {e}")


@router.callback_query(F.data.startswith("register_"))
async def register_for_event(callback: CallbackQuery):
    """Регистрация на событие"""
    logger.info(f"DEBUG CALLBACK: register_ от пользователя {callback.from_user.id}")
    await callback.answer()

    event_id = int(callback.data.split("_")[1])

    # Получаем или создаем пользователя
    user = await UserService.get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    # Пытаемся зарегистрировать
    success, message = await BookingService.register_user(event_id, user.id)

    if success:
        await callback.answer("✅ " + message, show_alert=True)

        # Обновляем сообщение с актуальной информацией
        event = await EventService.get_event_by_id(event_id)
        if event:
            message_text = await MessageFormatter.format_event_message(event)

            # Создаем обновленную клавиатуру
            builder = InlineKeyboardBuilder()

            # Проверяем записан ли пользователь
            bookings = await BookingService.get_event_bookings(event_id)
            user_registered = any(booking.user_id == user.id for booking in bookings)

            # Проверяем количество мест
            booking_count = len(bookings)
            has_free_places = booking_count < 4

            if user_registered:
                builder.add(
                    InlineKeyboardButton(
                        text="❌ Отменить запись", callback_data=f"cancel_{event_id}"
                    )
                )
            elif has_free_places:
                builder.add(
                    InlineKeyboardButton(
                        text="✅ Записаться", callback_data=f"register_{event_id}"
                    )
                )
            else:
                builder.add(
                    InlineKeyboardButton(text="🔒 Нет мест", callback_data="no_places")
                )

            # Добавляем дополнительные кнопки
            builder.add(
                InlineKeyboardButton(
                    text="🔄 Обновить", callback_data=f"refresh_{event_id}"
                ),
                InlineKeyboardButton(text="◀️ К событиям", callback_data="user_events"),
            )
            builder.adjust(1, 2)

            await safe_edit_message(
                callback, message_text, reply_markup=builder.as_markup()
            )
    else:
        await callback.answer("❌ " + message, show_alert=True)


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_registration(callback: CallbackQuery):
    """Отмена регистрации на событие"""
    logger.info(f"DEBUG CALLBACK: cancel_ от пользователя {callback.from_user.id}")
    await callback.answer()

    event_id = int(callback.data.split("_")[1])

    # Получаем пользователя
    user = await UserService.get_or_create_user(callback.from_user.id)

    # Пытаемся отменить регистрацию
    success, message = await BookingService.cancel_booking(event_id, user.id)

    if success:
        await callback.answer("✅ " + message, show_alert=True)

        # Обновляем сообщение с актуальной информацией
        event = await EventService.get_event_by_id(event_id)
        if event:
            message_text = await MessageFormatter.format_event_message(event)

            # Создаем обновленную клавиатуру
            builder = InlineKeyboardBuilder()

            # Проверяем записан ли пользователь
            bookings = await BookingService.get_event_bookings(event_id)
            user_registered = any(booking.user_id == user.id for booking in bookings)

            # Проверяем количество мест
            booking_count = len(bookings)
            has_free_places = booking_count < 4

            if user_registered:
                builder.add(
                    InlineKeyboardButton(
                        text="❌ Отменить запись", callback_data=f"cancel_{event_id}"
                    )
                )
            elif has_free_places:
                builder.add(
                    InlineKeyboardButton(
                        text="✅ Записаться", callback_data=f"register_{event_id}"
                    )
                )
            else:
                builder.add(
                    InlineKeyboardButton(text="🔒 Нет мест", callback_data="no_places")
                )

            # Добавляем дополнительные кнопки
            builder.add(
                InlineKeyboardButton(
                    text="🔄 Обновить", callback_data=f"refresh_{event_id}"
                ),
                InlineKeyboardButton(text="◀️ К событиям", callback_data="user_events"),
            )
            builder.adjust(1, 2)

            await safe_edit_message(
                callback, message_text, reply_markup=builder.as_markup()
            )
    else:
        await callback.answer("❌ " + message, show_alert=True)


@router.callback_query(F.data.startswith("refresh_"))
async def refresh_event(callback: CallbackQuery):
    """Обновление информации о событии"""
    logger.info(f"DEBUG CALLBACK: refresh_ от пользователя {callback.from_user.id}")
    await callback.answer("🔄 Обновляем...")

    event_id = int(callback.data.split("_")[1])
    event = await EventService.get_event_by_id(event_id)

    if not event:
        await callback.answer("❌ Событие не найдено", show_alert=True)
        return

    message_text = await MessageFormatter.format_event_message(event)

    # Создаем клавиатуру с действиями
    builder = InlineKeyboardBuilder()

    # Проверяем записан ли пользователь
    user = await UserService.get_or_create_user(callback.from_user.id)
    bookings = await BookingService.get_event_bookings(event_id)
    user_registered = any(booking.user_id == user.id for booking in bookings)

    # Проверяем количество мест
    booking_count = len(bookings)
    has_free_places = booking_count < 4

    if user_registered:
        builder.add(
            InlineKeyboardButton(
                text="❌ Отменить запись", callback_data=f"cancel_{event_id}"
            )
        )
    elif has_free_places:
        builder.add(
            InlineKeyboardButton(
                text="✅ Записаться", callback_data=f"register_{event_id}"
            )
        )
    else:
        builder.add(InlineKeyboardButton(text="🔒 Нет мест", callback_data="no_places"))

    # Добавляем дополнительные кнопки
    builder.add(
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_{event_id}"),
        InlineKeyboardButton(text="◀️ К событиям", callback_data="user_events"),
    )
    builder.adjust(1, 2)

    await safe_edit_message(callback, message_text, reply_markup=builder.as_markup())
