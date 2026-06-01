#!/usr/bin/env python3
"""
Одноразовый скрипт: удаляет осиротевшие TG-сообщения деактивированных дублей.
Запускать ОДИН РАЗ при живом боте:
    python3 delete_orphaned_messages.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot
from config import config

# ID сообщений деактивированных дублей (группа: config.group_id)
ORPHANED_MSG_IDS = [1377, 1385, 1389, 1392, 1396, 1397, 1401, 1405, 1406, 1407, 1412]


async def main():
    bot = Bot(token=config.bot_token)
    ok, fail = 0, 0
    for msg_id in ORPHANED_MSG_IDS:
        try:
            await bot.delete_message(chat_id=config.group_id, message_id=msg_id)
            print(f"✅ Удалено сообщение {msg_id}")
            ok += 1
        except Exception as e:
            print(f"⚠️  {msg_id}: {e}")
            fail += 1
    print(f"\nГотово: удалено {ok}, ошибок {fail}")
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
