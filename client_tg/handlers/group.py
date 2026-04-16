# handlers/group.py
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery
from config.logger import logger
from services.booking_service import BookingService
from services.event_service import EventService
from services.user_service import UserService
from utils.group_formatters import GroupMessageFormatter

from config import config, logger

router = Router()
_last_updates = {}
_user_cooldowns = {}


async def send_admin_notification(
    bot, event, count: int, notification_type: str
) -> None:
    """Отправить уведомление всем администраторам о состоянии группы."""
    weekday_name = config.weekday_names.get(str(event.weekday), "")
    if notification_type == "assembled":
        text = (
            f"🔔 Группа собралась!\n\n"
            f"🎾 {event.title}\n"
            f"📅 {event.event_date} ({weekday_name})\n"
            f"🕐 {event.event_time}\n"
            f"📍 {event.location}\n"
            f"👥 {count}/4 участников"
        )
    else:  # dissolved
        text = (
            f"⚠️ Группа распалась!\n\n"
            f"🎾 {event.title}\n"
            f"📅 {event.event_date} ({weekday_name})\n"
            f"🕐 {event.event_time}\n"
            f"📍 {event.location}\n"
            f"👥 {count}/4 участников"
        )
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить уведомление админу {admin_id}: {e}")


# Добавьте функцию проверки кулдауна:
def check_user_cooldown(user_id: int, cooldown_seconds: int = 3) -> bool:
    """Проверяет не слишком ли часто пользователь нажимает кнопки"""
    global _user_cooldowns

    now = datetime.now()

    if user_id in _user_cooldowns:
        last_action = _user_cooldowns[user_id]
        time_diff = (now - last_action).total_seconds()

        if time_diff < cooldown_seconds:
            return False  # Слишком рано

    # Обновляем время последнего действия
    _user_cooldowns[user_id] = now
    return True  # Можно выполнять действие


@router.callback_query(F.data.regexp(r"^join_event_\d+$"))
async def join_any_event(callback: CallbackQuery):
    """Запись на ЛЮБОЕ событие (новое или старое)"""
    user_id = callback.from_user.id

    # ПРОВЕРКА КУЛДАУНА - добавьте в самое начало
    if not check_user_cooldown(user_id, cooldown_seconds=3):
        logger.warning(f"🕒 Пользователь {user_id} слишком часто нажимает кнопки")
        await callback.answer(
            "⏰ Подождите немного перед следующим действием", show_alert=True
        )
        return

    logger.info(f"🔍 UNIVERSAL JOIN: {callback.data} от {user_id}")

    await callback.answer()

    if callback.message.chat.id != config.group_id:
        await callback.answer(
            "❌ Этот бот работает только в основной группе", show_alert=True
        )
        return

    event_id = int(callback.data.split("_")[2])

    user = await UserService.get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    event = await EventService.get_event_by_id(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено в системе", show_alert=True)
        return

    # Запоминаем счёт ДО записи для проверки порога 3/4
    count_before = await BookingService.get_booking_count(event_id)

    success, message = await BookingService.register_user(event_id, user.id)
    await callback.answer(f"{'✅' if success else '❌'} {message}", show_alert=True)

    # Обновляем ТОЛЬКО если была реальная операция записи
    if success:
        await update_group_message(callback, event_id)

        # Уведомление: группа собралась (3/4 или 4/4 — один раз за цикл)
        count_after = count_before + 1
        if count_after >= 3:
            notif_state = await EventService.get_notification_state(event_id)
            if notif_state != "assembled":
                await send_admin_notification(
                    callback.bot, event, count_after, "assembled"
                )
                await EventService.set_notification_state(event_id, "assembled")


@router.callback_query(F.data.regexp(r"^leave_event_\d+$"))
async def leave_any_event(callback: CallbackQuery):
    """Отмена записи на ЛЮБОЕ событие (новое или старое)"""
    user_id = callback.from_user.id

    # ПРОВЕРКА КУЛДАУНА - добавьте в самое начало
    if not check_user_cooldown(user_id, cooldown_seconds=3):
        logger.warning(f"🕒 Пользователь {user_id} слишком часто нажимает кнопки")
        await callback.answer(
            "⏰ Подождите немного перед следующим действием", show_alert=True
        )
        return

    logger.info(f"🔍 UNIVERSAL LEAVE: {callback.data} от {user_id}")

    await callback.answer()

    if callback.message.chat.id != config.group_id:
        await callback.answer(
            "❌ Этот бот работает только в основной группе", show_alert=True
        )
        return

    event_id = int(callback.data.split("_")[2])

    user = await UserService.get_or_create_user(callback.from_user.id)

    event = await EventService.get_event_by_id(event_id)
    if not event:
        await callback.answer("⚠️ Событие не найдено в системе", show_alert=True)
        return

    # Запоминаем счёт ДО отмены
    count_before = await BookingService.get_booking_count(event_id)

    success, message = await BookingService.cancel_booking(event_id, user.id)
    await callback.answer(f"{'✅' if success else '❌'} {message}", show_alert=True)

    # Обновляем ТОЛЬКО если была реальная операция отмены
    if success:
        await update_group_message(callback, event_id)

        # Уведомление: группа распалась (было ≥3, стало 2)
        count_after = count_before - 1
        if count_before >= 3 and count_after == 2:
            notif_state = await EventService.get_notification_state(event_id)
            if notif_state == "assembled":
                await send_admin_notification(
                    callback.bot, event, count_after, "dissolved"
                )
                await EventService.set_notification_state(event_id, "dissolved")


# Дополнительно: Функция очистки старых записей (опционально)
async def cleanup_old_cooldowns():
    """Очищает старые записи кулдаунов (вызывайте периодически)"""
    global _user_cooldowns, _last_updates

    now = datetime.now()
    cutoff_time = now - timedelta(minutes=10)  # Удаляем записи старше 10 минут

    # Очищаем кулдауны пользователей
    _user_cooldowns = {
        user_id: last_time
        for user_id, last_time in _user_cooldowns.items()
        if last_time > cutoff_time
    }

    # Очищаем кеш обновлений сообщений
    _last_updates = {
        msg_key: last_time
        for msg_key, last_time in _last_updates.items()
        if last_time > cutoff_time
    }


async def update_group_message(callback: CallbackQuery, event_id: int):
    """Обновляет сообщение в группе с защитой от flood control"""
    global _last_updates

    try:
        # Проверяем не обновляли ли мы это сообщение недавно
        message_key = f"{callback.message.chat.id}_{callback.message.message_id}"
        now = datetime.now()

        if message_key in _last_updates:
            last_update = _last_updates[message_key]
            time_diff = (now - last_update).total_seconds()

            if time_diff < 3:  # Минимум 3 секунды между обновлениями
                logger.warning(
                    f"⏳ Пропускаем обновление события {event_id} - слишком частые запросы ({time_diff:.1f}с)"
                )
                return

        logger.info(f"🔄 Начинаем обновление сообщения для события {event_id}")

        event = await EventService.get_event_by_id(event_id)
        if not event:
            logger.error(f"❌ Событие {event_id} не найдено при обновлении")
            return

        # Форматируем обновленное сообщение
        updated_text = await GroupMessageFormatter.format_group_event_message(event)
        updated_keyboard = GroupMessageFormatter.create_group_keyboard(event_id)

        # Сравниваем с текущим текстом чтобы избежать "message is not modified"
        current_text = callback.message.text or callback.message.caption or ""
        if updated_text == current_text:
            logger.info(f"📋 Сообщение события {event_id} уже актуально")
            return

        logger.debug(f"📝 Обновляем сообщение {updated_text}")

        # Пробуем обновить с markdown
        try:
            await callback.message.edit_text(
                updated_text, reply_markup=updated_keyboard, parse_mode="MarkdownV2"
            )

            # Запоминаем время последнего обновления
            _last_updates[message_key] = now
            logger.success(
                f"✅ Сообщение события {event_id} успешно обновлено в группе"
            )

        except Exception as markdown_error:
            error_msg = str(markdown_error).lower()

            if "message is not modified" in error_msg:
                logger.info(
                    f"📋 Сообщение события {event_id} уже актуально (не изменилось)"
                )
                return

            elif "flood control" in error_msg or "too many requests" in error_msg:
                logger.warning(
                    f"🚫 Flood control для события {event_id} - пропускаем обновление"
                )
                return

            elif "can't parse entities" in error_msg:
                logger.warning(f"⚠️ Markdown ошибка для события {event_id}")
                logger.debug(f"🧪 Ошибка: {markdown_error}")
                logger.debug(f"📤 Сообщение, вызвавшее ошибку:\n{updated_text}")
                logger.warning(
                    f"⚠️ Markdown ошибка для события {event_id}, пробуем без форматирования"
                )

                # Fallback: убираем весь markdown
                try:
                    # Убираем ВСЕ проблемные символы
                    clean_text = (
                        updated_text.replace("**", "")
                        .replace("*", "")
                        .replace("\\", "")
                        .replace("_", "")
                    )
                    await callback.message.edit_text(
                        clean_text, reply_markup=updated_keyboard
                    )
                    _last_updates[message_key] = now
                    logger.success(
                        f"✅ Сообщение события {event_id} обновлено без markdown"
                    )

                except Exception as clean_error:
                    logger.error(
                        f"❌ Не удалось обновить даже без markdown: {clean_error}"
                    )
            else:
                logger.error(f"❌ Неизвестная ошибка обновления: {markdown_error}")

    except Exception as e:
        logger.error(f"❌ Общая ошибка при обновлении сообщения: {e}")


@router.callback_query()
async def debug_all_group_callbacks(callback: CallbackQuery):
    """Отладка ВСЕХ callback'ов которые не попали в фильтры выше"""
    logger.debug(f"🐛 UNHANDLED: callback '{callback.data}' от {callback.from_user.id}")
    logger.debug(f"🐛 Chat ID: {callback.message.chat.id}")

    # Проверяем не пропустили ли мы какой-то формат
    if callback.data:
        if "event" in callback.data:
            logger.warning(f"🚨 ВНИМАНИЕ: Пропущен callback с 'event': {callback.data}")
