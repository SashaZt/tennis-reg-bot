# schedulers/schedule_scheduler.py
"""
Daily scheduler for the weekly schedule system.

Runs two tasks:
  00:05 — rotate: archive past instances, publish next week's ones
  09:00 — remind: send DMs to users registered for tomorrow's slots
"""
import asyncio
from datetime import date, datetime, timedelta

from aiogram import Bot
from config import config, logger
from services.schedule_service import ScheduleService
from utils.get_data import get_topic_id_for_date
from utils.schedule_formatters import ScheduleFormatter


class ScheduleScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._task: asyncio.Task = None
        self._running = False

    def start(self) -> asyncio.Task:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("📅 ScheduleScheduler запущен")
        return self._task

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("📅 ScheduleScheduler остановлен")

    async def _loop(self):
        # Run both at startup
        try:
            await self._rotate()
        except Exception as e:
            logger.error(f"❌ ScheduleScheduler (rotate) ошибка при старте: {e}")
        try:
            await self._send_reminders()
        except Exception as e:
            logger.error(f"❌ ScheduleScheduler (remind) ошибка при старте: {e}")

        while self._running:
            seconds, task_type = self._seconds_until_next_run()
            next_time = datetime.now() + timedelta(seconds=seconds)
            logger.info(
                f"📅 ScheduleScheduler: следующий запуск [{task_type}] "
                f"в {next_time.strftime('%d.%m %H:%M')} "
                f"(через {int(seconds // 3600)}ч {int((seconds % 3600) // 60)}м)"
            )
            await asyncio.sleep(seconds)
            if not self._running:
                break
            try:
                if task_type == "rotate":
                    await self._rotate()
                else:
                    await self._send_reminders()
            except Exception as e:
                logger.error(f"❌ ScheduleScheduler [{task_type}] ошибка: {e}")

    @staticmethod
    def _seconds_until_next_run() -> tuple[float, str]:
        """Return (seconds_to_sleep, task_type) for whichever scheduled time is sooner."""
        now = datetime.now()
        candidates = []
        for hour, minute, task in [(0, 5, "rotate"), (9, 0, "remind")]:
            t = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if t <= now:
                t += timedelta(days=1)
            candidates.append((t, task))
        candidates.sort(key=lambda x: x[0])
        next_time, task = candidates[0]
        return (next_time - now).total_seconds(), task

    # ── Rotate ─────────────────────────────────────────────────────────

    async def _rotate(self):
        """Archive past instances, ensure each template has an upcoming one."""
        past = await ScheduleService.get_past_active_instances()
        if not past:
            logger.info("📅 ScheduleScheduler: нет прошедших расписаний для архивации")
        else:
            logger.info(
                f"📅 ScheduleScheduler: архивируем {len(past)} расписаний: "
                + ", ".join(f"#{i['id']} {i['instance_date']} msg={i['group_message_id']}" for i in past)
            )
            for inst in past:
                try:
                    await self._archive_instance(inst)
                except Exception as e:
                    logger.error(f"❌ Ошибка архивации инстанса #{inst['id']} {inst['instance_date']}: {e}")

        templates = await ScheduleService.get_templates()
        for tmpl in templates:
            has = await ScheduleService.has_upcoming_instance(tmpl["id"])
            if not has:
                try:
                    await self._create_and_publish(tmpl)
                except Exception as e:
                    logger.error(f"❌ Ошибка публикации шаблона #{tmpl['id']}: {e}")

    async def _archive_instance(self, inst: dict):
        """Delete TG post and deactivate DB record.

        Only deactivates DB if TG deletion succeeded or message was already gone.
        On transient errors, keeps DB active so the next rotation retries.
        """
        if inst["group_message_id"]:
            try:
                await self.bot.delete_message(
                    chat_id=config.group_id,
                    message_id=inst["group_message_id"],
                )
                logger.info(
                    f"🗑 #{inst['id']} {inst['instance_date']} удалено из TG "
                    f"(msg_id={inst['group_message_id']})"
                )
            except Exception as e:
                err_str = str(e).lower()
                if "message to delete not found" in err_str or "message_id_invalid" in err_str:
                    # Already gone — safe to deactivate
                    logger.info(
                        f"ℹ️ #{inst['id']} {inst['instance_date']} сообщение уже отсутствует в TG"
                    )
                elif "not enough rights" in err_str or "rights" in err_str:
                    # Permissions issue — retrying won't help, deactivate but warn loudly
                    logger.error(
                        f"❌ НЕТ ПРАВ на удаление сообщений! Проверь права бота в группе. "
                        f"Инстанс #{inst['id']} {inst['instance_date']} msg_id={inst['group_message_id']}"
                    )
                else:
                    # Transient error — keep DB active, retry on next rotation
                    logger.warning(
                        f"⚠️ #{inst['id']} {inst['instance_date']} msg_id={inst['group_message_id']} "
                        f"не удалось удалить из TG (попробую завтра): {e}"
                    )
                    return
        else:
            logger.warning(
                f"⚠️ #{inst['id']} {inst['instance_date']} — нет group_message_id, "
                f"TG-пост не отслеживался"
            )

        await ScheduleService.deactivate_instance(inst["id"])
        logger.success(
            f"✅ #{inst['id']} архивирован: {inst['title'] or inst['weekday']} {inst['instance_date']}"
        )

    async def _create_and_publish(self, tmpl: dict):
        next_date = self._next_occurrence(tmpl["weekday"])
        date_str = next_date.strftime("%d.%m.%Y")

        slot_times = await ScheduleService.get_template_slots(tmpl["id"])
        if not slot_times:
            logger.warning(f"⚠️ Шаблон {tmpl['id']} без слотов — пропущен")
            return

        slots = [(t, tmpl["max_participants"]) for t in slot_times]
        instance_id = await ScheduleService.create_instance(tmpl["id"], date_str, slots)
        instance = await ScheduleService.get_instance_by_id(instance_id)
        slot_instances = await ScheduleService.get_slot_instances(instance_id)

        try:
            topic_id = get_topic_id_for_date(date_str, is_kids=tmpl["is_kids"])
            text = ScheduleFormatter.format_message(instance, slot_instances)
            keyboard = ScheduleFormatter.build_keyboard(slot_instances)

            msg = await self.bot.send_message(
                chat_id=config.group_id,
                text=text,
                message_thread_id=topic_id,
                reply_markup=keyboard,
                parse_mode="MarkdownV2",
            )
            await ScheduleService.update_instance_message_id(instance_id, msg.message_id)
            logger.success(
                f"📅 Расписание опубликовано: {tmpl['title'] or 'без названия'} "
                f"на {date_str}, instance_id={instance_id}"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка публикации расписания шаблона {tmpl['id']}: {e}")

    # ── Reminders ──────────────────────────────────────────────────────

    async def _send_reminders(self):
        """Send 'tomorrow training' DMs to all registered users."""
        bookings = await ScheduleService.get_remindable_bookings_for_tomorrow()
        if not bookings:
            logger.info("📅 ScheduleScheduler: нет напоминаний для отправки")
            return

        all_ids = [b["booking_id"] for b in bookings]
        sent_count = 0
        for b in bookings:
            try:
                title_line = f"📋 {b['title']}\n" if b["title"] else ""
                await self.bot.send_message(
                    b["telegram_id"],
                    f"⏰ Напоминание о тренировке!\n\n"
                    f"{title_line}"
                    f"📅 Завтра, {b['instance_date']}\n"
                    f"🕐 {b['slot_time']}\n"
                    f"📍 {b['location']}\n\n"
                    f"Удачной тренировки! 💪",
                )
                sent_count += 1
            except Exception as e:
                err = str(e).lower()
                if "forbidden" in err or "bot was blocked" in err or "can't initiate" in err:
                    logger.info(
                        f"📅 Напоминание не доставлено {b['telegram_id']}: "
                        f"пользователь не начал диалог с ботом"
                    )
                else:
                    logger.warning(
                        f"⚠️ Ошибка отправки напоминания {b['telegram_id']}: {e}"
                    )

        # Mark all as processed regardless of delivery — no point retrying
        await ScheduleService.mark_reminders_sent(all_ids)

        logger.success(
            f"📅 Напоминания обработаны: ✉️ доставлено {sent_count}, "
            f"⛔ недоставлено {len(bookings) - sent_count} (пользователи не начали диалог)"
            if len(bookings) - sent_count > 0
            else f"📅 Напоминания отправлены: {sent_count}/{len(bookings)}"
        )

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _next_occurrence(weekday: int) -> date:
        """Next date (today or later) that falls on the given weekday."""
        today = date.today()
        days_until = (weekday - today.weekday()) % 7
        return today + timedelta(days=days_until)
