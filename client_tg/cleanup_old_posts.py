#!/usr/bin/env python3
"""
Одноразовый скрипт: архивирует и убирает все старые посты из TG-группы.

Для каждого деактивированного события с group_message_id:
  - 1+ участников и нет в истории → сохраняет в training_history
  - Пробует удалить TG-сообщение; если старше 48ч → редактирует на "завершена"
  - Очищает group_message_id в БД

Запуск (бот может быть выключен):
    python3 cleanup_old_posts.py
"""
import asyncio
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from config import config

DB_PATH = Path(__file__).parent / "data" / "database.db"
TODAY_KEY = date.today().strftime("%Y%m%d")
CANCELLED_TEXT = "❌ Тренировка завершена"


def get_past_events(db: sqlite3.Connection):
    return db.execute("""
        SELECT e.id, e.title, e.event_date, e.event_time, e.location,
               e.price, e.group_message_id, e.recurring_template_id,
               COUNT(b.id) as participant_count,
               GROUP_CONCAT(
                   json_object(
                       'name', COALESCE(u.first_name,'') ||
                               CASE WHEN u.last_name IS NOT NULL THEN ' '||u.last_name ELSE '' END,
                       'username', CASE WHEN u.username IS NOT NULL THEN '@'||u.username ELSE NULL END,
                       'telegram_id', u.telegram_id
                   )
               ) as participants_json
        FROM events e
        LEFT JOIN bookings b ON b.event_id = e.id AND b.status = 'registered'
        LEFT JOIN users u ON b.user_id = u.id
        WHERE e.is_active = FALSE
          AND e.group_message_id IS NOT NULL
          AND substr(e.event_date,7,4)||substr(e.event_date,4,2)||substr(e.event_date,1,2) < ?
        GROUP BY e.id
        ORDER BY substr(e.event_date,7,4)||substr(e.event_date,4,2)||substr(e.event_date,1,2)
    """, (TODAY_KEY,)).fetchall()


def already_in_history(db: sqlite3.Connection, event_id: int) -> bool:
    row = db.execute(
        "SELECT 1 FROM training_history WHERE event_id = ?", (event_id,)
    ).fetchone()
    return row is not None


def save_to_history(db: sqlite3.Connection, row):
    event_id, title, event_date, event_time, location, price, \
        group_message_id, recurring_template_id, participant_count, participants_json = row

    if participant_count < 1:
        return False

    # Build participants list
    participants = []
    if participants_json:
        for item in participants_json.split("},{"):
            item = item.strip("{}")
            try:
                obj = json.loads("{" + item + "}")
                participants.append(obj)
            except Exception:
                pass

    is_recurring = 1 if recurring_template_id else 0
    db.execute(
        """INSERT INTO training_history
           (event_id, title, event_date, event_time, location, price,
            participant_count, participants, is_recurring)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event_id, title, event_date, event_time, location, price,
            participant_count,
            json.dumps(participants, ensure_ascii=False),
            is_recurring,
        ),
    )
    db.commit()
    return True


async def handle_tg_message(bot: Bot, msg_id: int) -> str:
    """Try delete; if too old/restricted — edit to cancelled text."""
    for attempt in range(3):
        try:
            await bot.delete_message(chat_id=config.group_id, message_id=msg_id)
            return "deleted"
        except TelegramRetryAfter as e:
            print(f"    ⏳ Флуд-контроль, жду {e.retry_after}с...")
            await asyncio.sleep(e.retry_after + 1)
        except TelegramBadRequest as e:
            err = str(e).lower()
            if "not found" in err or "can't be deleted" in err:
                # Message too old or already deleted — try edit instead
                return await _try_edit(bot, msg_id)
            return f"not_found"
        except Exception as e:
            return f"error: {e}"
    return "error: превышено число попыток"


async def _try_edit(bot: Bot, msg_id: int) -> str:
    """Edit message text to mark as finished, removing keyboard."""
    for attempt in range(3):
        try:
            await bot.edit_message_text(
                chat_id=config.group_id,
                message_id=msg_id,
                text=CANCELLED_TEXT,
                reply_markup=None,
            )
            return "edited"
        except TelegramRetryAfter as e:
            print(f"    ⏳ Флуд-контроль (edit), жду {e.retry_after}с...")
            await asyncio.sleep(e.retry_after + 1)
        except TelegramBadRequest as e:
            err = str(e).lower()
            if "not modified" in err:
                return "edited"
            if "not found" in err:
                return "not_found"
            return f"error: {e}"
        except Exception as e:
            return f"error: {e}"
    return "error: превышено число попыток"


async def main():
    db = sqlite3.connect(DB_PATH)
    rows = get_past_events(db)

    print(f"Найдено {len(rows)} деактивированных событий с TG-сообщением\n")

    bot = Bot(token=config.bot_token)

    archived = 0
    deleted = 0
    edited = 0
    not_found = 0
    errors = 0
    skipped_history = 0

    for i, row in enumerate(rows, 1):
        event_id = row[0]
        title = row[1]
        event_date = row[2]
        msg_id = row[6]
        participant_count = row[8]

        # Save to history if needed
        hist_status = ""
        if participant_count >= 1:
            if already_in_history(db, event_id):
                hist_status = "(уже в истории)"
                skipped_history += 1
            else:
                save_to_history(db, row)
                hist_status = "→ сохранено в историю"
                archived += 1

        # Handle TG message
        result = await handle_tg_message(bot, msg_id)
        if result == "deleted":
            deleted += 1
        elif result == "edited":
            edited += 1
        elif result == "not_found":
            not_found += 1
        else:
            errors += 1

        # Clear group_message_id in DB
        db.execute(
            "UPDATE events SET group_message_id = NULL WHERE id = ?", (event_id,)
        )
        db.commit()

        pct = f"{participant_count}/4"
        print(f"[{i}/{len(rows)}] {event_date} {title} 👥{pct}  TG:{result}  {hist_status}")

        # Pause every 5 messages to avoid flood control
        if i % 5 == 0:
            await asyncio.sleep(1.5)

    await bot.session.close()
    db.close()

    print(f"""
{'='*50}
Готово!
  Сохранено в историю:     {archived}
  Уже было в истории:      {skipped_history}
  Удалено из TG:           {deleted}
  Заменено на "завершена": {edited}
  Уже не было в TG:        {not_found}
  Ошибок:                  {errors}
""")


if __name__ == "__main__":
    asyncio.run(main())
