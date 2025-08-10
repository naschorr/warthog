from pathlib import Path
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from utilities import get_root_directory


def _directory_exist_validator(path: Path) -> Path:
    """Ensure the directory exists, creating it if necessary."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    elif not path.is_dir():
        raise ValueError(f"Path {path} exists but is not a directory")
    return path


class LoggingConfig(BaseModel):
    """Logging configuration."""

    console_level: str = Field(default="DEBUG", description="Logging level for console output.")
    file_level: str = Field(default="DEBUG", description="Logging level for file output.")
    log_file: Path = Field(default=get_root_directory() / "logs" / "warthog.log", description="File to write logs to.")
    clear_logs_on_start: bool = Field(default=True, description="Whether to clear the log file on application start.")

    @field_validator("log_file")
    @classmethod
    def ensure_log_file_exists(cls, v: Path) -> Path:
        return _directory_exist_validator(v.parent)


class VehicleServiceConfig(BaseModel):
    """Configuration for the Vehicle Service."""

    processed_vehicle_data_directory_path: Path = Field(
        default=get_root_directory() / "data" / "processed_vehicle_data",
        description="Path to the directory containing processed vehicle data files.",
    )

    @field_validator("processed_vehicle_data_directory_path")
    @classmethod
    def ensure_processed_vehicle_data_dir_exists(cls, v: Path) -> Path:
        return _directory_exist_validator(v)


class WtExtCliServiceConfig(BaseModel):
    """Configuration for replay collection and processing."""

    wt_ext_cli_path: Optional[Path] = Field(
        default=None,
        description="Path to the wt_ext_cli executable for parsing War Thunder replay blk data. If None, the service will attempt to discover the executable within the project directory.",
    )


class ReplayManagerServiceConfig(BaseModel):
    """Configuration for the Replay Manager Service."""

    processed_replay_dir: Path = Field(
        default=get_root_directory() / "output" / "replays",
        description="Directory to store replays after they've been processed.",
    )

    @field_validator("processed_replay_dir")
    @classmethod
    def ensure_processed_replay_dir_exists(cls, v: Path) -> Path:
        return _directory_exist_validator(v)


class WarThunderConfig(BaseModel):
    """War Thunder specific configuration."""

    replay_dir: Path = Field(
        description="Directory where War Thunder replays are stored.",
    )

    @field_validator("replay_dir")
    @classmethod
    def ensure_replay_dir_exists(cls, v: Path) -> Path:
        return _directory_exist_validator(v)


class WarthogConfig(BaseModel):
    """Main application configuration."""

    logging_config: LoggingConfig = LoggingConfig()
    vehicle_service_config: VehicleServiceConfig = VehicleServiceConfig()
    wt_ext_cli_service_config: WtExtCliServiceConfig = WtExtCliServiceConfig()
    replay_manager_service_config: ReplayManagerServiceConfig = ReplayManagerServiceConfig()
    war_thunder_config: WarThunderConfig
    overwrite_existing_replays: bool = Field(
        default=False,
        description="Whether to overwrite existing replays in the processed replay directory.",
    )
