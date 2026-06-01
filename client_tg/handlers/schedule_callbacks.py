# handlers/schedule_callbacks.py
"""User-facing callbacks for the schedule system (join/leave a time slot)."""
from aiogram import F, Router
from aiogram.types import CallbackQuery

from config import config, logger
from services.schedule_service import ScheduleService
from services.user_service import UserService
from utils.schedule_formatters import ScheduleFormatter

router = Router()


async def _refresh_schedule_message(bot, slot_id: int) -> None:
    """Edit the group post to reflect the current booking state."""
    slot = await ScheduleService.get_slot_instance_by_id(slot_id)
    if not slot:
        return
    instance = await ScheduleService.get_instance_by_id(slot["schedule_instance_id"])
    if not instance or not instance["group_message_id"]:
        return

    slots = await ScheduleService.get_slot_instances(instance["id"])
    text = ScheduleFormatter.format_message(instance, slots)
    keyboard = ScheduleFormatter.build_keyboard(slots)

    try:
        await bot.edit_message_text(
            chat_id=config.group_id,
            message_id=instance["group_message_id"],
            text=text,
            reply_markup=keyboard,
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            logger.warning(f"⚠️ Не удалось обновить расписание: {e}")


@router.callback_query(F.data.regexp(r"^sched_join_\d+$"))
async def sched_join(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[2])

    user = await UserService.get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    result = await ScheduleService.register(slot_id, user.id)

    if result == "already":
        await callback.answer("ℹ️ Вы уже записаны на это время", show_alert=True)
        return
    if result == "full":
        await callback.answer("❌ Нет свободных мест на это время", show_alert=True)
        return
    if result == "not_found":
        await callback.answer("❌ Слот не найден", show_alert=True)
        return

    await callback.answer("✅ Вы записаны!")
    await _refresh_schedule_message(callback.bot, slot_id)


@router.callback_query(F.data.regexp(r"^sched_leave_\d+$"))
async def sched_leave(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[2])

    user = await UserService.get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    result = await ScheduleService.cancel(slot_id, user.id)

    if result == "not_registered":
        await callback.answer("ℹ️ Вы не записаны на это время", show_alert=True)
        return

    await callback.answer("✅ Запись отменена")
    await _refresh_schedule_message(callback.bot, slot_id)
