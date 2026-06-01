#!/usr/bin/env python3
"""
Миграция: добавляет таблицу training_history в существующую БД.

Запуск:
    python migrate_add_history.py
    python migrate_add_history.py --db /path/to/database.db   # кастомный путь

Скрипт идемпотентный — безопасно запускать повторно.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).parent / "data" / "database.db"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS training_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id         INTEGER,
    title            TEXT    NOT NULL,
    event_date       TEXT    NOT NULL,
    event_time       TEXT    NOT NULL,
    location         TEXT    NOT NULL,
    price            INTEGER DEFAULT 90,
    participant_count INTEGER DEFAULT 0,
    participants     TEXT    NOT NULL,
    is_recurring     INTEGER DEFAULT 0,
    archived_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def run(db_path: Path) -> None:
    if not db_path.exists():
        print(f"❌ БД не найдена: {db_path}")
        sys.exit(1)

    print(f"📂 БД: {db_path}")

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()

        # Проверяем, существует ли таблица уже
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='training_history'"
        )
        already_exists = cur.fetchone() is not None

        if already_exists:
            print("ℹ️  Таблица training_history уже существует — миграция не нужна.")
        else:
            cur.execute(CREATE_TABLE)
            con.commit()
            print("✅ Таблица training_history успешно создана.")

        # Показываем итоговую схему таблицы
        cur.execute("PRAGMA table_info(training_history)")
        columns = cur.fetchall()
        print("\nСхема таблицы training_history:")
        for col in columns:
            print(f"  {col[1]:20s} {col[2]}")

    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Миграция: добавить таблицу training_history")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"Путь к файлу БД (по умолчанию: {DEFAULT_DB})",
    )
    args = parser.parse_args()
    run(args.db)
