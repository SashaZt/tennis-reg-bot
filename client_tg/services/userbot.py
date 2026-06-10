# services/userbot.py
"""Telethon userbot client for operations unavailable to bots (e.g. delete in forum topics)."""
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, UnauthorizedError
from telethon.sessions import StringSession

from config import config, logger

_client: TelegramClient | None = None
_group_entity = None  # cached after first get_dialogs() call


async def _get_client() -> TelegramClient:
    global _client
    if _client is None:
        _client = TelegramClient(
            StringSession(config.telegram_session_string),
            config.telegram_api_id,
            config.telegram_api_hash,
        )
    if not _client.is_connected():
        await _client.connect()
        logger.info("👤 Userbot подключён")
    return _client


async def _get_group_entity():
    """Return cached group entity, fetching dialogs on first call to populate access hash cache."""
    global _group_entity
    if _group_entity is None:
        client = await _get_client()
        # StringSession doesn't persist entity access hashes — get_dialogs() fills the in-memory cache
        logger.info("👤 Userbot: загружаю диалоги для получения access hash группы...")
        await client.get_dialogs(limit=500)
        _group_entity = await client.get_entity(config.group_id)
        logger.info(f"👤 Userbot: группа найдена — {_group_entity.id}")
    return _group_entity


async def delete_message(chat_id: int, message_id: int) -> bool:
    """Delete a message via userbot session. Returns True on success."""
    try:
        client = await _get_client()
        entity = await _get_group_entity()
        await client.delete_messages(entity, [message_id])
        return True
    except (AuthKeyUnregisteredError, UnauthorizedError) as e:
        logger.error(
            f"❌ Userbot: сессия недействительна (отозвана или завершена): {e}. "
            f"Нужно сгенерировать новую: python generate_session.py "
            f"и обновить CLIENT_TG__TELEGRAM_SESSION_STRING в .env"
        )
        return False
    except Exception as e:
        logger.error(f"❌ Userbot: не удалось удалить msg_id={message_id}: {e}")
        return False
