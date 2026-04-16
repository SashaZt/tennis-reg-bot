# client_tg/config/__init__.py
# Автоматически сгенерировано для сервиса: client_tg

from .config import Config, config
from .logger import get_logger, setup_logging, logger
from .paths import ProjectPaths

paths = ProjectPaths.from_base()

__all__ = ["config", "Config", "ProjectPaths", "paths", "setup_logging", "get_logger", "logger"]
