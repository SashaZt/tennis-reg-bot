# client_tg/config/logger.py
# Автоматически сгенерировано для сервиса: client_tg

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .config import Config
    from .paths import ProjectPaths


class LoggerManager:
    def __init__(self):
        self._logger = logger
        self._configured = False

    def setup_logging(
        self, paths: "ProjectPaths" = None, config: "Config" = None
    ) -> logger:
        if self._configured:
            return self._logger

        project_root = Path(__file__).parent.parent
        log_dir = project_root / "log"
        log_dir.mkdir(parents=True, exist_ok=True)

        level = "DEBUG"
        rotation = "10 MB"
        retention = "7 days"
        fmt_file = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}"
        fmt_console = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{file}:{line}</cyan> | <cyan>{message}</cyan>"

        if config and hasattr(config, "log"):
            log_cfg = config.log
            level = log_cfg.level.upper()
            rotation = log_cfg.rotation
            retention = log_cfg.retention
            fmt_file = log_cfg.format_file
            fmt_console = log_cfg.format_console

        self._logger.remove()
        self._logger.add(
            log_dir / "log_message.log",
            format=fmt_file, level=level,
            encoding="utf-8", rotation=rotation, retention=retention,
        )
        self._logger.add(
            sys.stderr,
            format=fmt_console, level=level, enqueue=True,
        )
        self._configured = True
        return self._logger

    def get_logger(self):
        if not self._configured:
            self.setup_logging()
        return self._logger

    def reconfigure(self, paths=None, config=None):
        self._configured = False
        return self.setup_logging(paths, config)


_logger_manager = LoggerManager()

setup_logging = _logger_manager.setup_logging
get_logger = _logger_manager.get_logger
reconfigure_logging = _logger_manager.reconfigure

logger = get_logger()
