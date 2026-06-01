# utils/schedule_formatters.py
from typing import List, Dict

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from utils.group_formatters import escape_markdown_v2


class ScheduleFormatter:

    @staticmethod
    def format_message(instance: Dict, slots: List[Dict]) -> str:
        """Format the schedule post for the Telegram group (MarkdownV2).

        Header: 📅 [Weekday] [Date]  (+ optional custom title on second line)
        Slots:  🟢/🔴 HH:MM — N/M занято
        Footer: price, location, conditions
        """
        weekday_name = config.weekday_names.get(str(instance["weekday"]), "")
        safe_weekday = escape_markdown_v2(weekday_name)
        safe_date = escape_markdown_v2(instance["instance_date"])
        safe_location = escape_markdown_v2(instance["location"])
        safe_currency = escape_markdown_v2(str(config.currency))
        safe_conditions = escape_markdown_v2(config.conditions_text)

        header = f"📅 *{safe_weekday} {safe_date}*"

        custom_title = (instance.get("title") or "").strip()
        if custom_title:
            safe_title = escape_markdown_v2(custom_title)
            header += f"\n__{safe_title}__"

        lines = [header, ""]

        for slot in slots:
            free = slot["max_participants"] - slot["booked"]
            time_esc = escape_markdown_v2(slot["slot_time"])
            count = f"{slot['booked']}/{slot['max_participants']}"
            if free <= 0:
                lines.append(f"🔴 *{time_esc}* — заполнено \\({count}\\)")
            else:
                lines.append(f"🟢 *{time_esc}* — {count} занято")

        lines.append(f"\n💰 Стоимость: {instance['price']} {safe_currency}")
        lines.append(f"📍 Место: {safe_location}")
        lines.append(f"\n{safe_conditions}")
        return "\n".join(lines)

    @staticmethod
    def build_keyboard(slots: List[Dict]):
        """
        One row per slot:
          available: [✅ HH:MM]  [❌ HH:MM]
          full:                  [❌ HH:MM]
        """
        builder = InlineKeyboardBuilder()
        for slot in slots:
            free = slot["max_participants"] - slot["booked"]
            row = []
            if free > 0:
                row.append(InlineKeyboardButton(
                    text=f"✅ {slot['slot_time']}",
                    callback_data=f"sched_join_{slot['id']}",
                ))
            row.append(InlineKeyboardButton(
                text=f"❌ {slot['slot_time']}",
                callback_data=f"sched_leave_{slot['id']}",
            ))
            builder.row(*row)
        return builder.as_markup()
