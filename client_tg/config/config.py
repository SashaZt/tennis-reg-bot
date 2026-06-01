# client_tg/config/config.py
# Автоматически сгенерировано для сервиса: client_tg
# Для регенерации: python generate_config.py --service client_tg
#
# Зависимости: pip install pydantic pydantic-settings

from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Вложенные модели ──────────────────────────────────────────────────

class LogConfig(BaseModel):
    """Конфигурация: log"""
    level: str
    rotation: str
    retention: str
    format_file: str
    format_console: str

class SpecialTopicsConfig(BaseModel):
    """Конфигурация: special_topics"""
    kids: int

class DbConfigConfig(BaseModel):
    """Конфигурация: db_config"""
    default_price: int
    default_currency: str
    locations: Dict[str, str]

class ConfigConfig(BaseModel):
    """Конфигурация: config"""
    log: LogConfig
    file_name: str
    bot_token: str
    admin_ids: List[int]
    admin_username: str
    admin_phone: str
    group_id: int
    max_participants: int
    price: int
    currency: str
    cancel_hours_limit: int
    min_group_size: int
    max_group_size: int
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session_string: str
    weekday_topics: Dict[str, int]
    special_topics: SpecialTopicsConfig
    weekday_names: Dict[str, str]
    locations: Dict[str, str]
    conditions_text: str
    db_config: DbConfigConfig


# ── Главный класс настроек ────────────────────────────────────────────

class Config(BaseSettings):
    """Конфигурация client_tg.

    Все значения берутся из переменных окружения с префиксом 'CLIENT_TG__'.
    Вложенные поля разделяются через '__':
        CLIENT_TG__LOG__LEVEL=debug
        CLIENT_TG__MAX_WORKERS=4
    """

    model_config = SettingsConfigDict(
        env_prefix="CLIENT_TG__",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    log: LogConfig
    file_name: str
    bot_token: str
    admin_ids: List[int]
    admin_username: str
    admin_phone: str
    group_id: int
    max_participants: int
    price: int
    currency: str
    cancel_hours_limit: int
    min_group_size: int
    max_group_size: int
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session_string: str
    weekday_topics: Dict[str, int]
    special_topics: SpecialTopicsConfig
    weekday_names: Dict[str, str]
    locations: Dict[str, str]
    conditions_text: str
    db_config: DbConfigConfig


# Глобальный инстанс — бросит ValidationError при старте, если env не заполнен
config = Config()


if __name__ == "__main__":
    try:
        print("✅ Конфигурация client_tg успешно загружена")
        print(f"  file_name = {config.file_name}")
        print(f"  bot_token = {config.bot_token}")
        print(f"  admin_ids = {config.admin_ids}")
        print(f"  admin_username = {config.admin_username}")
        print(f"  admin_phone = {config.admin_phone}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
