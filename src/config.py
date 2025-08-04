import logging

logger = logging.getLogger(__name__)

import random
import json
from pathlib import Path
from typing import Optional
from abc import ABC

from pydantic import BaseModel, Field, model_validator

from enums import BattleType, AppMode


class BaseDelayConfig(BaseModel, ABC):
    min_ms: int = 0
    max_ms: int = 1000

    @property
    def random_delay_seconds(self) -> float:
        """Generate a random delay between min_ms and max_ms in seconds."""
        return random.randint(self.min_ms, self.max_ms) / 1000.0


class ForegroundDelayConfig(BaseDelayConfig):
    min_ms: int = Field(
        default=1000,
        description="Minimum delay in milliseconds for foreground operations.",
    )
    max_ms: int = Field(
        default=2000,
        description="Maximum delay in milliseconds for foreground operations.",
    )


class KeyPressDelayConfig(BaseDelayConfig):
    min_ms: int = Field(default=50, description="Minimum delay in milliseconds for key presses.")
    max_ms: int = Field(default=150, description="Maximum delay in milliseconds for key presses.")


class BattleSelectDelayConfig(BaseDelayConfig):
    min_ms: int = Field(
        default=100,
        description="Minimum delay in milliseconds for battle selection operations.",
    )
    max_ms: int = Field(
        default=500,
        description="Maximum delay in milliseconds for battle selection operations.",
    )


class TabSwitchDelayConfig(BaseDelayConfig):
    min_ms: int = Field(
        default=250,
        description="Minimum delay in milliseconds for tab switching operations.",
    )
    max_ms: int = Field(
        default=500,
        description="Maximum delay in milliseconds for tab switching operations.",
    )


class ClipboardDelayConfig(BaseDelayConfig):
    min_ms: int = Field(
        default=150,
        description="Minimum delay in milliseconds for clipboard operations.",
    )
    max_ms: int = Field(
        default=300,
        description="Maximum delay in milliseconds for clipboard operations.",
    )


class DelayConfig(BaseModel):
    """Delay settings for various operations."""

    foreground_delay: ForegroundDelayConfig = ForegroundDelayConfig()
    key_press_delay: KeyPressDelayConfig = KeyPressDelayConfig()
    battle_select_delay: BattleSelectDelayConfig = BattleSelectDelayConfig()
    tab_switch_delay: TabSwitchDelayConfig = TabSwitchDelayConfig()
    clipboard_delay: ClipboardDelayConfig = ClipboardDelayConfig()


class WarThunderConfig(BaseModel):
    """Game-specific settings."""

    window_title: str = Field(
        default="War Thunder",
        description="Title of the War Thunder game window. Supports regex strings for window titles.",
    )
    battle_type: BattleType = Field(
        default=BattleType.REALISTIC,
        description="What kind of battles are being collected?",
        examples=[BattleType.ARCADE, BattleType.REALISTIC, BattleType.SIMULATION],
    )
    max_battle_count: int = Field(default=30, description="Number of battles to collect data from.")
    max_battle_parse_tries: int = Field(
        default=4,
        description="Maximum number of attempts to parse a battle before giving up.",
    )


class WarThunderUiNavigationConfig(BaseModel):
    """Settings for navigating the game UI."""

    max_up_arrow_count: int = Field(
        default=30,
        description="Number of times to press the up arrow key when resetting the 'Battles' tab.",
    )
    left_arrow_count: int = Field(
        default=11,
        description="Number of times to press the left arrow key when resetting the 'Battles' tab.",
    )


class OCRConfig(BaseModel):
    """Configuration for OCR functionality."""

    confidence_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="OCR confidence threshold (between 0 and 1.0). Confidence values below this will be ignored.",
    )


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


class BattleConfig(BaseModel):
    """Configuration for battle data collection and processing."""

    delay_config: DelayConfig = DelayConfig()
    warthunder_config: WarThunderConfig = WarThunderConfig()
    warthunder_ui_navigation_config: WarThunderUiNavigationConfig = WarThunderUiNavigationConfig()
    ocr_config: OCRConfig = OCRConfig()


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

    mode: AppMode = Field(
        default=AppMode.REPLAY,
        description="Application mode: battle data collection or replay parsing.",
        examples=[AppMode.BATTLE, AppMode.REPLAY],
    )

    battle_config: Optional[BattleConfig] = None
    replay_config: Optional[ReplayConfig] = None

    @model_validator(mode="after")
    def validate_mode_specific_configs(self):
        """Ensure appropriate configs are set based on mode."""
        if self.mode == AppMode.BATTLE and self.battle_config is None:
            self.battle_config = BattleConfig()
        elif self.mode == AppMode.REPLAY and self.replay_config is None:
            self.replay_config = ReplayConfig()

        return self


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
