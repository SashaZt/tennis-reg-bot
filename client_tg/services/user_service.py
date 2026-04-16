# services/user_service.py
from typing import Optional

from database.connection import get_db
from database.models import User


class UserService:
    @staticmethod
    async def get_or_create_user(
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        is_admin: bool = False,
    ) -> User:
        """Получить или создать пользователя"""
        async with get_db() as db:
            # Проверяем есть ли пользователь
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                return User(*row)

            # Создаем нового пользователя
            await db.execute(
                """INSERT INTO users (telegram_id, username, first_name, last_name, is_admin) 
                   VALUES (?, ?, ?, ?, ?)""",
                (telegram_id, username, first_name, last_name, is_admin),
            )
            await db.commit()

            # Возвращаем созданного пользователя
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return User(*row)

    @staticmethod
    async def is_admin(telegram_id: int) -> bool:
        """Проверить является ли пользователь администратором"""
        async with get_db() as db:
            async with db.execute(
                "SELECT is_admin FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row and row[0]

    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return User(*row) if row else None
