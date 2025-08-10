import logging

logger = logging.getLogger(__name__)

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Logging configuration."""

    console_level: str = Field(default="DEBUG", description="Logging level for console output.")
    file_level: str = Field(default="DEBUG", description="Logging level for file output.")
    log_file: str = Field(default="logs/warthog.log", description="File to write logs to.")


class StorageConfig(BaseModel):
    """Data storage configuration."""

    output_dir: str = Field(default="output", description="Directory to store collected battle data.")


class VehicleServiceConfig(BaseModel):
    """Configuration for the Vehicle Service."""

    processed_vehicle_data_directory_path: Path = Field(
        default=Path("data") / "processed_vehicle_data",
        description="Path to the directory containing processed vehicle data files.",
    )


class ReplayConfig(BaseModel):
    """Configuration for replay collection and processing."""

    wt_ext_cli_path: Optional[Path] = Field(
        default=None,
        description="Path to the wt_ext_cli executable for parsing War Thunder replay blk data.",
    )


class AppConfig(BaseModel):
    """Main application configuration."""

    logging_config: LoggingConfig = LoggingConfig()
    storage_config: StorageConfig = StorageConfig()
    vehicle_service_config: VehicleServiceConfig = VehicleServiceConfig()
    replay_config: Optional[ReplayConfig] = None


class ConfigManager:
    ## Statics

    _SINGLETON_INSTANCE = None

    ## Lifecycle

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize the configuration manager."""

        # Prevent creating multiple instances directly
        if ConfigManager._SINGLETON_INSTANCE is not None:
            logger.warning("ConfigManager is a singleton! Use ConfigManager.get_instance() instead.")
            return
        else:
            ConfigManager._SINGLETON_INSTANCE = self

        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path("config")

        self.config_file = self.config_dir / "config.json"
        self.default_config_file = self.config_dir / "default_config.json"
        self.config = self._load_config()

    ## Methods

    @classmethod
    def get_instance(cls, config_dir: Optional[str] = None):
        """Get or create the singleton instance of ConfigManager."""
        if cls._SINGLETON_INSTANCE is None:
            cls._SINGLETON_INSTANCE = cls(config_dir)
        return cls._SINGLETON_INSTANCE

    def _load_config(self) -> AppConfig:
        """Load configuration from file or create default."""
        try:
            config_data = {}

            # Try to load from config.json first
            if self.config_file.exists():
                logger.info(f"Loading config from {self.config_file}")
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                return AppConfig(**config_data)

            # Try to load from default_config.json
            if self.default_config_file.exists():
                logger.info(f"Loading config from defaults: {self.default_config_file}")
                with open(self.default_config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                return AppConfig(**config_data)

            # If no config files found, create a default config
            logger.info("No configuration files found, default configuration will be used.")
            return AppConfig()

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Using default configuration")
            return AppConfig()


def get_config(config_dir: Optional[str] = None) -> AppConfig:
    """
    One-stop shop to get the application configuration.
    """
    return ConfigManager.get_instance(config_dir).config
