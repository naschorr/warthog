import logging

logger = logging.getLogger(__name__)

import warnings
from typing import Optional
from pathlib import Path

from src.config import LoggingConfig


class LoggingService:

    # STATICS

    ROOT_DIR = Path(__file__).parent.parent.parent  # I don't love this, but it's fine for now
    DEFAULT_CONSOLE_LOG_LEVEL = logging.INFO
    DEFAULT_FILE_LOG_LEVEL = logging.DEBUG
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_NAME = "warthog.log"

    # Lifecycle

    def __init__(self, logging_config: LoggingConfig):
        self.logging_config = logging_config

        # Suppress warnings from specific dependencies
        self._noisy_loggers = [
            "torch.utils.data.dataloader",
            # Add more noisy loggers as needed
        ]
        self._ignored_warnings = [
            ".*'pin_memory' argument is set as true but no accelerator.*"
            # Add more globbed warnings to ignore as needed
        ]

        # Initialize logging!
        self._init_logging(logging_config)

    # Methods

    def _init_console_logger(self, log_level, log_format) -> logging.Handler:
        """Initialize console logger with the specified log level and format."""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(log_format)
        return console_handler

    def _init_file_logger(self, log_file_path: Path, log_level, log_format) -> logging.Handler:
        """Initialize file logger with the specified log file path, level, and format."""
        # Relative log paths should be relative to the ROOT_DIR, while absolute paths are used as is.
        if not log_file_path.is_absolute():
            log_file_path = Path(self.ROOT_DIR) / log_file_path
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_format)
        return file_handler

    def _init_log_filters(self):
        """Initialize log filtering to suppress noisy loggers and warnings."""
        for logger_name in self._noisy_loggers:
            specific_logger = logging.getLogger(logger_name)
            specific_logger.setLevel(logging.ERROR)  # Only show ERROR or higher

        for warning in self._ignored_warnings:
            warnings.filterwarnings(
                "ignore",
                message=warning,
            )

    def _init_logging(self, logging_config: Optional[LoggingConfig] = None):
        """Initialize logging configuration."""

        # Create root logger and formatter
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Set to lowest level, the individual handlers will filter
        root_logger.handlers.clear()
        formatter = logging.Formatter(self.LOG_FORMAT)

        # Console handler
        console_level = getattr(
            logging, logging_config.console_level.upper() if logging_config else str(self.DEFAULT_CONSOLE_LOG_LEVEL)
        )
        console_log_handler = self._init_console_logger(console_level, formatter)
        root_logger.addHandler(console_log_handler)

        # File handler
        file_level = getattr(
            logging, logging_config.file_level.upper() if logging_config else str(self.DEFAULT_FILE_LOG_LEVEL)
        )
        log_file_path = (
            Path(self.logging_config.log_file) if self.logging_config.log_file else Path("logs") / self.LOG_FILE_NAME
        )
        file_log_handler = self._init_file_logger(log_file_path, file_level, formatter)
        root_logger.addHandler(file_log_handler)

        # Initialize log filters
        self._init_log_filters()

        logger.info(f"Logging initialized - Console: {console_level}, File: {file_level} ({log_file_path})")
