# database/connection.py
import asyncio
from pathlib import Path

import aiosqlite

from config import config, logger, paths

DB_PATH = Path(paths.data) / config.file_name


async def init_database():
    """Инициализация базы данных"""

    db_exists = DB_PATH.exists()
    if db_exists:
        logger.info(f"📂 БД найдена: {DB_PATH}, запускаем только миграции")
    else:
        logger.info(f"🆕 БД не найдена: {DB_PATH}, создаём с нуля")

    async with aiosqlite.connect(DB_PATH) as db:
        if not db_exists:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    location TEXT NOT NULL,
                    max_participants INTEGER DEFAULT 4,
                    price INTEGER DEFAULT 90,
                    created_by INTEGER REFERENCES users(id),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    group_message_id INTEGER,
                    weekday INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER REFERENCES events(id),
                    user_id INTEGER REFERENCES users(id),
                    status TEXT CHECK(status IN ('registered', 'cancelled')) DEFAULT 'registered',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cancelled_at TIMESTAMP,
                    UNIQUE(event_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS recurring_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    weekday INTEGER NOT NULL,
                    event_time TEXT NOT NULL,
                    location TEXT NOT NULL,
                    price INTEGER DEFAULT 90,
                    max_participants INTEGER DEFAULT 4,
                    created_by INTEGER REFERENCES users(id),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        # Миграции — всегда, безопасно для существующей БД
        migrations = [
            ("group_message_id", "ALTER TABLE events ADD COLUMN group_message_id INTEGER"),
            ("weekday", "ALTER TABLE events ADD COLUMN weekday INTEGER DEFAULT 0"),
            ("notification_state", "ALTER TABLE events ADD COLUMN notification_state TEXT DEFAULT NULL"),
            ("recurring_template_id", "ALTER TABLE events ADD COLUMN recurring_template_id INTEGER REFERENCES recurring_templates(id)"),
            ("recurring_templates", "CREATE TABLE IF NOT EXISTS recurring_templates (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, weekday INTEGER NOT NULL, event_time TEXT NOT NULL, location TEXT NOT NULL, price INTEGER DEFAULT 90, max_participants INTEGER DEFAULT 4, created_by INTEGER REFERENCES users(id), is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"),
        ]
        for name, sql in migrations:
            try:
                await db.execute(sql)
            except Exception as e:
                if "duplicate column name" not in str(e).lower() and "already exists" not in str(e).lower():
                    logger.warning(f"⚠️ Миграция {name}: {e}")

        await db.commit()
        logger.info("База данных инициализирована")


def get_db():
    """Получение соединения с БД"""
    return aiosqlite.connect(DB_PATH)
