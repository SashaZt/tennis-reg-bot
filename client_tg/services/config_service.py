# services/config_service.py
"""
Сервис для динамических настроек бота.
Хранит в таблице config_settings (key TEXT PK, value TEXT).
При первом запуске сидирует значениями из config.json.
"""
import json
from typing import Dict

from database.connection import get_db
from config.logger import logger


class ConfigService:

    # ─── Базовые операции ────────────────────────────────────────────

    @staticmethod
    async def get_setting(key: str) -> str | None:
        async with get_db() as db:
            async with db.execute(
                "SELECT value FROM config_settings WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    @staticmethod
    async def set_setting(key: str, value: str) -> None:
        async with get_db() as db:
            await db.execute(
                "INSERT INTO config_settings (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            await db.commit()

    # ─── Цена по умолчанию ───────────────────────────────────────────

    @staticmethod
    async def get_default_price() -> int:
        raw = await ConfigService.get_setting("default_price")
        if raw is not None:
            try:
                return int(raw)
            except ValueError:
                pass
        from config import config
        return config.price  # fallback из config.json

    @staticmethod
    async def set_default_price(price: int) -> None:
        await ConfigService.set_setting("default_price", str(price))
        logger.info(f"💰 Цена по умолчанию → {price}")

    # ─── Локации ─────────────────────────────────────────────────────

    @staticmethod
    async def get_locations() -> Dict[str, str]:
        raw = await ConfigService.get_setting("locations")
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
                logger.warning(f"⚙️ locations в БД не является dict: {type(data)}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга locations из БД: {e} | raw={raw!r}")
        from config import config
        logger.warning("⚙️ Используется fallback locations из config (env)")
        return dict(config.locations)

    @staticmethod
    async def add_location(name: str) -> str:
        """Добавить локацию, возвращает новый ключ."""
        locations = await ConfigService.get_locations()
        max_key = max((int(k) for k in locations if k.isdigit()), default=0)
        new_key = str(max_key + 1)
        locations[new_key] = name.strip()
        await ConfigService.set_setting("locations", json.dumps(locations, ensure_ascii=False))
        logger.info(f"📍 Локация [{new_key}] добавлена: {name}")
        return new_key

    @staticmethod
    async def delete_location(key: str) -> bool:
        """Удалить локацию по ключу."""
        locations = await ConfigService.get_locations()
        if key not in locations:
            return False
        name = locations.pop(key)
        await ConfigService.set_setting("locations", json.dumps(locations, ensure_ascii=False))
        logger.info(f"🗑 Локация [{key}] '{name}' удалена")
        return True

    # ─── Повторяющиеся тренировки ────────────────────────────────────

    @staticmethod
    async def get_recurring_enabled() -> bool:
        raw = await ConfigService.get_setting("recurring_enabled")
        return raw == "true"

    @staticmethod
    async def set_recurring_enabled(enabled: bool) -> None:
        await ConfigService.set_setting("recurring_enabled", "true" if enabled else "false")
        logger.info(f"🔄 Повторяющиеся тренировки → {'ВКЛ' if enabled else 'ВЫКЛ'}")

    # ─── Инициализация ───────────────────────────────────────────────

    @staticmethod
    async def seed_if_empty() -> None:
        """Заполнить начальные значения из config.json если таблица пуста."""
        from config import config
        async with get_db() as db:
            async with db.execute("SELECT COUNT(*) FROM config_settings") as cursor:
                count = (await cursor.fetchone())[0]

        if count == 0:
            logger.info("⚙️ config_settings пуст — сидируем из config.json")
            await ConfigService.set_setting("default_price", str(config.price))
            await ConfigService.set_setting(
                "locations",
                json.dumps(dict(config.locations), ensure_ascii=False),
            )
