# generate_session.py
"""Генерация новой Telethon StringSession для юзербота.

Запуск:  python generate_session.py
Берёт api_id/api_hash из client_tg/.env, спрашивает телефон и код из Telegram,
печатает строку сессии — её нужно вставить в CLIENT_TG__TELEGRAM_SESSION_STRING.
"""
import asyncio
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

ENV_PATH = Path(__file__).parent / "client_tg" / ".env"


def load_env_value(key: str) -> str | None:
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


async def main():
    api_id = load_env_value("CLIENT_TG__TELEGRAM_API_ID")
    api_hash = load_env_value("CLIENT_TG__TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print(f"⚠️ Не нашёл api_id/api_hash в {ENV_PATH}, введите вручную (my.telegram.org):")
        api_id = input("api_id: ").strip()
        api_hash = input("api_hash: ").strip()

    client = TelegramClient(StringSession(), int(api_id), api_hash)
    # interactive: спросит телефон, код из Telegram и пароль 2FA, если включён
    await client.start()

    me = await client.get_me()
    session_string = client.session.save()
    print(f"\n✅ Авторизован как: {me.first_name} (@{me.username}, id={me.id})")
    print("\nНовая строка сессии (вставьте в client_tg/.env):\n")
    print(f"CLIENT_TG__TELEGRAM_SESSION_STRING={session_string}")
    print(
        "\n⚠️ Не завершайте эту сессию в Telegram → Настройки → Устройства, "
        "иначе строка снова станет недействительной."
    )
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
