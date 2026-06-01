# handlers/schedule_admin.py
"""Admin panel: schedule template management, instance view, participant removal."""
from datetime import date, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config, logger
from services.config_service import ConfigService
from services.schedule_service import ScheduleService
from services.user_service import UserService
from utils.get_data import get_topic_id_for_date
from utils.schedule_formatters import ScheduleFormatter
from utils.validators import Validators

router = Router()


class ScheduleCreateStates(StatesGroup):
    waiting_for_weekday = State()
    waiting_for_title = State()
    waiting_for_location = State()
    waiting_for_price = State()
    waiting_for_max = State()
    waiting_for_slots = State()


# ── Main menu ──────────────────────────────────────────────────────────

def _menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Обычная тренировка", callback_data="sched_create_regular"),
        InlineKeyboardButton(text="👶 Детская тренировка", callback_data="sched_create_kids"),
        InlineKeyboardButton(text="📋 Мои шаблоны", callback_data="sched_list"),
        InlineKeyboardButton(text="👁 Активные расписания", callback_data="sched_view"),
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="admin_main"),
    )
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "sched_menu")
async def schedule_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📅 Расписание тренировок\n\n"
        "Шаблон определяет день недели и слоты. "
        "Расписание публикуется автоматически и удаляется на следующий день после тренировки.",
        reply_markup=_menu_keyboard(),
    )


# ── List & delete templates ────────────────────────────────────────────

@router.callback_query(F.data == "sched_list")
async def schedule_list(callback: CallbackQuery):
    await callback.answer()
    user = await UserService.get_or_create_user(callback.from_user.id)
    templates = await ScheduleService.get_templates(created_by=user.id)

    if not templates:
        try:
            await callback.message.edit_text(
                "📋 Нет активных шаблонов.\n\nСоздайте через ➕ кнопки выше.",
                reply_markup=_menu_keyboard(),
            )
        except TelegramBadRequest:
            pass
        return

    builder = InlineKeyboardBuilder()
    for tmpl in templates:
        day = config.weekday_names.get(str(tmpl["weekday"]), "?")
        slots = await ScheduleService.get_template_slots(tmpl["id"])
        kids = " 👶" if tmpl["is_kids"] else ""
        title = f" — {tmpl['title']}" if tmpl["title"] else ""
        slots_str = ", ".join(slots) if slots else "без слотов"
        # info button (non-functional, just label)
        builder.row(
            InlineKeyboardButton(
                text=f"📅 {day}{kids}{title}  •  {slots_str}  •  {tmpl['price']} зл.",
                callback_data=f"sched_tmpl_info_{tmpl['id']}",
            ),
        )
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 Удалить шаблон",
                callback_data=f"sched_delete_{tmpl['id']}",
            ),
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="sched_menu"))

    try:
        await callback.message.edit_text(
            f"📋 Активных шаблонов: {len(templates)}\n\nНажмите 🗑 чтобы удалить шаблон:",
            reply_markup=builder.as_markup(),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.regexp(r"^sched_tmpl_info_\d+$"))
async def schedule_tmpl_info(callback: CallbackQuery):
    await callback.answer()  # just dismiss tap, no action


@router.callback_query(F.data.regexp(r"^sched_delete_\d+$"))
async def schedule_delete(callback: CallbackQuery):
    await callback.answer()
    template_id = int(callback.data.split("_")[2])
    tmpl = await ScheduleService.get_template_by_id(template_id)
    if not tmpl:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return

    day = config.weekday_names.get(str(tmpl["weekday"]), "?")
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"sched_confirm_del_{template_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="sched_list"),
    )
    builder.adjust(2)
    await callback.message.edit_text(
        f"⚠️ Удалить шаблон?\n\n"
        f"{'👶 ' if tmpl['is_kids'] else ''}{tmpl['title'] or day} ({day})\n\n"
        "Новые расписания не будут создаваться. "
        "Уже опубликованное расписание останется до следующего дня.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.regexp(r"^sched_confirm_del_\d+$"))
async def schedule_confirm_delete(callback: CallbackQuery):
    await callback.answer()
    template_id = int(callback.data.split("_")[3])
    await ScheduleService.deactivate_template(template_id)
    await callback.message.edit_text(
        "✅ Шаблон удалён.",
        reply_markup=_menu_keyboard(),
    )


# ── View active instances ──────────────────────────────────────────────

@router.callback_query(F.data == "sched_view")
async def schedule_view(callback: CallbackQuery):
    """List currently active schedule instances."""
    await callback.answer()
    instances = await ScheduleService.get_active_instances()

    if not instances:
        try:
            await callback.message.edit_text(
                "👁 Нет активных расписаний.",
                reply_markup=_menu_keyboard(),
            )
        except TelegramBadRequest:
            pass
        return

    builder = InlineKeyboardBuilder()
    counter = 1

    for inst in instances:
        day = config.weekday_names.get(str(inst["weekday"]), "?")
        title = inst.get("title") or ""
        slot_times = await ScheduleService.get_slot_instances(inst["id"])

        title_part = f" {title}," if title else ","
        for slot in slot_times:
            builder.row(InlineKeyboardButton(
                text=f"{counter}. {day}{title_part} 💰 {inst['price']} зл., 🕐 {slot['slot_time']}",
                callback_data=f"sched_inst_{inst['id']}",
            ))
            counter += 1

    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="sched_menu"))

    try:
        await callback.message.edit_text(
            "👁 Активные расписания:",
            reply_markup=builder.as_markup(),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.regexp(r"^sched_inst_\d+$"))
async def schedule_instance_detail(callback: CallbackQuery):
    """Show slots of a schedule instance with participant counts."""
    await callback.answer()
    instance_id = int(callback.data.split("_")[2])
    instance = await ScheduleService.get_instance_by_id(instance_id)
    if not instance:
        await callback.answer("❌ Расписание не найдено", show_alert=True)
        return

    slots = await ScheduleService.get_slot_instances(instance_id)
    day = config.weekday_names.get(str(instance["weekday"]), "?")
    kids = " 👶" if instance.get("is_kids") else ""

    lines = [f"📅 {instance['title'] or day}{kids} — {instance['instance_date']}\n"]
    for slot in slots:
        free = slot["max_participants"] - slot["booked"]
        icon = "🟢" if free > 0 else "🔴"
        lines.append(f"{icon} {slot['slot_time']} — {slot['booked']}/{slot['max_participants']}")

    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.add(InlineKeyboardButton(
            text=f"👥 {slot['slot_time']} ({slot['booked']}/{slot['max_participants']})",
            callback_data=f"sched_slot_{slot['id']}",
        ))
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить расписание", callback_data=f"sched_del_inst_{instance_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="sched_view"),
    )

    try:
        await callback.message.edit_text(
            "\n".join(lines) + "\n\nНажмите на слот для управления участниками:",
            reply_markup=builder.as_markup(),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.regexp(r"^sched_del_inst_\d+$"))
async def schedule_delete_instance(callback: CallbackQuery):
    """Confirm before deleting a schedule instance."""
    await callback.answer()
    instance_id = int(callback.data.split("_")[3])
    instance = await ScheduleService.get_instance_by_id(instance_id)
    if not instance:
        await callback.answer("❌ Расписание не найдено", show_alert=True)
        return

    day = config.weekday_names.get(str(instance["weekday"]), "?")
    kids = " 👶" if instance.get("is_kids") else ""
    label = instance["title"] or day

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"sched_confirm_del_inst_{instance_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"sched_inst_{instance_id}"),
    )
    await callback.message.edit_text(
        f"⚠️ Удалить расписание?\n\n"
        f"{label}{kids} — {instance['instance_date']}\n\n"
        "Пост будет удалён из группы. "
        "Шаблон останется — следующая неделя создастся автоматически.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.regexp(r"^sched_confirm_del_inst_\d+$"))
async def schedule_confirm_delete_instance(callback: CallbackQuery):
    """Delete (deactivate) a schedule instance and remove its TG post."""
    await callback.answer()
    instance_id = int(callback.data.split("_")[4])
    instance = await ScheduleService.get_instance_by_id(instance_id)
    if not instance:
        await callback.answer("❌ Расписание не найдено", show_alert=True)
        return

    if instance["group_message_id"]:
        try:
            await callback.bot.delete_message(
                chat_id=config.group_id,
                message_id=instance["group_message_id"],
            )
        except Exception:
            pass  # already deleted or too old

    await ScheduleService.deactivate_instance(instance_id)
    logger.info(f"🗑 Расписание {instance_id} ({instance['instance_date']}) удалено администратором")

    await callback.message.edit_text(
        "✅ Расписание удалено из группы.",
        reply_markup=_menu_keyboard(),
    )


@router.callback_query(F.data.regexp(r"^sched_slot_\d+$"))
async def schedule_slot_participants(callback: CallbackQuery):
    """Show participants of a slot with kick buttons."""
    await callback.answer()
    slot_id = int(callback.data.split("_")[2])
    slot = await ScheduleService.get_slot_instance_by_id(slot_id)
    if not slot:
        await callback.answer("❌ Слот не найден", show_alert=True)
        return

    participants = await ScheduleService.get_slot_participants(slot_id)
    instance_id = slot["schedule_instance_id"]

    if not participants:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="◀️ Назад", callback_data=f"sched_inst_{instance_id}"
        ))
        await callback.message.edit_text(
            f"🕐 {slot['slot_time']} — никто не записан.",
            reply_markup=builder.as_markup(),
        )
        return

    lines = [f"🕐 {slot['slot_time']} — участники ({slot['booked']}/{slot['max_participants']}):\n"]
    for i, p in enumerate(participants, 1):
        name = p["name"]
        if p["username"]:
            name += f" ({p['username']})"
        lines.append(f"{i}. {name}")

    builder = InlineKeyboardBuilder()
    for p in participants:
        name = p["name"]
        if p["username"]:
            name += f" ({p['username']})"
        builder.add(InlineKeyboardButton(
            text=f"❌ {name}",
            callback_data=f"sched_kick_{slot_id}_{p['user_id']}",
        ))
    builder.add(InlineKeyboardButton(
        text="◀️ Назад", callback_data=f"sched_inst_{instance_id}"
    ))
    builder.adjust(1)

    try:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=builder.as_markup(),
            parse_mode=None,
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.regexp(r"^sched_kick_\d+_\d+$"))
async def schedule_kick_participant(callback: CallbackQuery):
    """Admin removes a user from a schedule slot."""
    await callback.answer()
    parts = callback.data.split("_")
    slot_id = int(parts[2])
    user_id = int(parts[3])

    removed = await ScheduleService.cancel_by_internal_ids(slot_id, user_id)
    if not removed:
        await callback.answer("ℹ️ Пользователь уже не записан", show_alert=True)
        return

    # Notify the removed user
    user = await UserService.get_user_by_id(user_id)
    slot = await ScheduleService.get_slot_instance_by_id(slot_id)
    if user and slot:
        instance = await ScheduleService.get_instance_by_id(slot["schedule_instance_id"])
        if instance:
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    f"ℹ️ Тренер отменил вашу запись:\n"
                    f"📅 {instance['instance_date']}\n"
                    f"🕐 {slot['slot_time']}",
                )
            except Exception:
                pass  # user hasn't started the bot

        # Refresh the group TG message
        await _refresh_group_message(callback.bot, slot["schedule_instance_id"])

    await callback.message.edit_text(
        "✅ Участник удалён из расписания.",
        reply_markup=InlineKeyboardBuilder().add(
            InlineKeyboardButton(text="◀️ К слоту", callback_data=f"sched_slot_{slot_id}")
        ).as_markup(),
    )


# ── Create flow ────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({"sched_create_regular", "sched_create_kids"}))
async def schedule_create_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    is_kids = callback.data == "sched_create_kids"
    await state.update_data(is_kids=is_kids)
    await state.set_state(ScheduleCreateStates.waiting_for_weekday)

    prefix = "👶 Детская тренировка" if is_kids else "Тренировка"
    await callback.message.edit_text(
        f"📅 Создание шаблона: {prefix}\n\nВыберите день недели:",
        reply_markup=_weekday_keyboard(),
    )


def _weekday_keyboard():
    builder = InlineKeyboardBuilder()
    for wd, name in config.weekday_names.items():
        builder.add(InlineKeyboardButton(text=name, callback_data=f"sched_wd_{wd}"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="sched_menu"))
    builder.adjust(3, 3, 1, 1)
    return builder.as_markup()


@router.callback_query(
    F.data.regexp(r"^sched_wd_\d+$"),
    ScheduleCreateStates.waiting_for_weekday,
)
async def schedule_process_weekday(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    weekday = int(callback.data.split("_")[2])
    await state.update_data(weekday=weekday)
    await state.set_state(ScheduleCreateStates.waiting_for_title)

    day_name = config.weekday_names.get(str(weekday), "?")
    # Show preview date
    today = date.today()
    days_until = (weekday - today.weekday()) % 7
    preview_date = (today + timedelta(days=days_until)).strftime("%d.%m.%Y")

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Пропустить", callback_data="sched_skip_title"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="sched_menu"),
    )
    builder.adjust(1)
    await callback.message.edit_text(
        f"✅ День: {day_name}\n"
        f"📅 Первое расписание будет на: {preview_date}\n\n"
        f"Добавьте подпись к названию (необязательно).\n"
        f"Например: «Дети с 6 лет» или «Начинающие»\n\n"
        f"Заголовок поста будет: {day_name} {preview_date} [ваш текст]\n\n"
        "Или нажмите «Пропустить»:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "sched_skip_title", ScheduleCreateStates.waiting_for_title)
async def schedule_skip_title(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(title="")
    await _ask_location(callback.message, state, use_edit=True)


@router.message(ScheduleCreateStates.waiting_for_title)
async def schedule_process_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)
    # message — это сообщение пользователя, его нельзя редактировать → answer()
    await _ask_location(message, state, use_edit=False)


async def _ask_location(msg, state: FSMContext, use_edit: bool = False):
    """Show location picker. use_edit=True when msg is a bot message (callback.message)."""
    locations = await ConfigService.get_locations()
    builder = InlineKeyboardBuilder()
    for loc_id, loc_name in locations.items():
        builder.add(InlineKeyboardButton(
            text=f"📍 {loc_name}", callback_data=f"sched_loc_{loc_id}"
        ))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="sched_menu"))
    builder.adjust(1)
    data = await state.get_data()
    text = f"✅ Подпись: «{data['title']}»\n\n" if data.get("title") else "✅ Без подписи\n\n"
    text += "📍 Выберите место проведения:"

    if use_edit:
        await msg.edit_text(text, reply_markup=builder.as_markup())
    else:
        await msg.answer(text, reply_markup=builder.as_markup())
    # Устанавливаем состояние ПОСЛЕ успешного вызова Telegram
    await state.set_state(ScheduleCreateStates.waiting_for_location)


@router.callback_query(
    F.data.startswith("sched_loc_"),
    ScheduleCreateStates.waiting_for_location,
)
async def schedule_process_location(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    loc_id = callback.data[len("sched_loc_"):]
    locations = await ConfigService.get_locations()
    location = locations.get(loc_id)
    if not location:
        await callback.answer("❌ Локация не найдена", show_alert=True)
        return
    await state.update_data(location=location)
    await state.set_state(ScheduleCreateStates.waiting_for_price)

    default_price = await ConfigService.get_default_price()
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="sched_menu"))
    await callback.message.edit_text(
        f"✅ Место: {location}\n\n"
        f"💰 Введите цену (в злотых), по умолчанию {default_price}:",
        reply_markup=builder.as_markup(),
    )


@router.message(ScheduleCreateStates.waiting_for_price)
async def schedule_process_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное число (например: 90)")
        return
    await state.update_data(price=price)
    await state.set_state(ScheduleCreateStates.waiting_for_max)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="sched_menu"))
    await message.answer(
        f"✅ Цена: {price} зл.\n\n"
        "👥 Максимум участников на каждый слот (по умолчанию 4):",
        reply_markup=builder.as_markup(),
    )


@router.message(ScheduleCreateStates.waiting_for_max)
async def schedule_process_max(message: Message, state: FSMContext):
    try:
        max_p = int(message.text.strip())
        if max_p < 1 or max_p > 20:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 1 до 20")
        return
    await state.update_data(max_participants=max_p)
    await state.set_state(ScheduleCreateStates.waiting_for_slots)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="sched_menu"))
    await message.answer(
        f"✅ Макс. участников: {max_p}\n\n"
        "🕐 Введите временные слоты через запятую:\n"
        "Например: 11:00, 12:00, 18:00",
        reply_markup=builder.as_markup(),
    )


@router.message(ScheduleCreateStates.waiting_for_slots)
async def schedule_process_slots(message: Message, state: FSMContext):
    parts = [p.strip() for p in message.text.strip().split(",") if p.strip()]
    invalid = [p for p in parts if not Validators.validate_time(p)]
    if invalid:
        await message.answer(
            f"❌ Неверный формат: {', '.join(invalid)}\n"
            "Используйте ЧЧ:ММ, например: 11:00, 12:00, 18:00"
        )
        return
    if not parts:
        await message.answer("❌ Введите хотя бы один слот")
        return

    data = await state.get_data()
    await state.clear()

    user = await UserService.get_or_create_user(message.from_user.id)
    template_id = await ScheduleService.create_template(
        weekday=data["weekday"],
        title=data.get("title", ""),
        location=data["location"],
        price=data["price"],
        max_participants=data["max_participants"],
        created_by=user.id,
        is_kids=data.get("is_kids", False),
    )
    for slot_time in parts:
        await ScheduleService.add_slot(template_id, slot_time)

    day_name = config.weekday_names.get(str(data["weekday"]), "?")
    kids_label = " 👶 (детская)" if data.get("is_kids") else ""

    published_date = await _publish_first_instance(message.bot, template_id)
    extra = f"\n📨 Опубликовано на {published_date}" if published_date else ""

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="◀️ К расписаниям", callback_data="sched_menu"))
    title_line = f"\n📝 Подпись: {data['title']}" if data.get("title") else ""
    await message.answer(
        f"✅ Шаблон создан!\n\n"
        f"📅 {day_name}{kids_label}{title_line}\n"
        f"📍 {data['location']}\n"
        f"💰 {data['price']} зл.  👥 макс. {data['max_participants']}\n"
        f"🕐 {', '.join(parts)}"
        f"{extra}\n\n"
        "Расписание будет публиковаться автоматически каждую неделю.",
        reply_markup=builder.as_markup(),
    )


# ── Helpers ────────────────────────────────────────────────────────────

async def _publish_first_instance(bot, template_id: int) -> str | None:
    """Create and post the first instance for a newly created template."""
    try:
        tmpl = await ScheduleService.get_template_by_id(template_id)
        if not tmpl:
            return None

        if await ScheduleService.has_upcoming_instance(template_id):
            return None

        today = date.today()
        days_until = (tmpl["weekday"] - today.weekday()) % 7
        date_str = (today + timedelta(days=days_until)).strftime("%d.%m.%Y")

        slot_times = await ScheduleService.get_template_slots(template_id)
        if not slot_times:
            return None

        slots = [(t, tmpl["max_participants"]) for t in slot_times]
        instance_id = await ScheduleService.create_instance(template_id, date_str, slots)
        instance = await ScheduleService.get_instance_by_id(instance_id)
        slot_instances = await ScheduleService.get_slot_instances(instance_id)

        topic_id = get_topic_id_for_date(date_str, is_kids=tmpl["is_kids"])
        text = ScheduleFormatter.format_message(instance, slot_instances)
        keyboard = ScheduleFormatter.build_keyboard(slot_instances)

        msg = await bot.send_message(
            chat_id=config.group_id,
            text=text,
            message_thread_id=topic_id,
            reply_markup=keyboard,
            parse_mode="MarkdownV2",
        )
        await ScheduleService.update_instance_message_id(instance_id, msg.message_id)
        logger.success(f"📅 Первое расписание опубликовано на {date_str}")
        return date_str
    except Exception as e:
        logger.error(f"❌ Ошибка публикации первого расписания шаблона {template_id}: {e}")
        return None


async def _refresh_group_message(bot, instance_id: int):
    """Edit the group post after a participant change."""
    instance = await ScheduleService.get_instance_by_id(instance_id)
    if not instance or not instance["group_message_id"]:
        return
    slots = await ScheduleService.get_slot_instances(instance_id)
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
            logger.warning(f"⚠️ Не удалось обновить расписание в группе: {e}")
