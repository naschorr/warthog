from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from src.common.utilities import get_root_directory
from src.common.configuration.validators import Validators
from src.replay_data_grabber.configuration import WarthogReplayDataGrabberConfig
from src.vehicle_data_grabber.configuration import WarthogVehicleDataGrabberConfig


class LoggingConfig(BaseModel):
    """Logging configuration."""

    console_level: str = Field(default="DEBUG", description="Logging level for console output.")
    file_level: str = Field(default="DEBUG", description="Logging level for file output.")
    log_file: Path = Field(default=get_root_directory() / "logs" / "warthog.log", description="File to write logs to.")
    clear_logs_on_start: bool = Field(default=True, description="Whether to clear the log file on application start.")

    @field_validator("log_file")
    @classmethod
    def ensure_log_file_exists(cls, v: Path) -> Path:
        return Validators.directory_exists_validator(v.parent)


class VehicleServiceConfig(BaseModel):
    """Configuration for the Vehicle Service."""

    processed_vehicle_data_directory_path: Path = Field(
        default=get_root_directory() / "data" / "vehicle_data" / "processed_vehicle_data",
        description="Path to the directory containing processed vehicle data files.",
    )

    @field_validator("processed_vehicle_data_directory_path")
    @classmethod
    def ensure_processed_vehicle_data_dir_exists(cls, v: Path) -> Path:
        return Validators.directory_exists_validator(v)

    game_version_to_release_datetime_file_path: Path = Field(
        default=get_root_directory() / "data" / "vehicle_data" / "game_version_release_datetimes.json",
        description="Path to the JSON file mapping game versions to their release datetimes.",
    )

    @field_validator("game_version_to_release_datetime_file_path")
    @classmethod
    def ensure_game_version_file_exists(cls, v: Path) -> Path:
        if not Validators.file_exists_validator(v):
            raise ValueError(
                f"Game version to release datetime file does not exist at {v}.\nUse `VehicleDataGrabber` launch option in VSCode, or execute the `src/vehicle_data_grabber/warthog_vehicle_data_grabber.py` script. Check configuration if it's still not found."
            )
        return v


class WarthogConfig(BaseModel):
    """Main configuration for Warthog."""

    logging_config: LoggingConfig = Field(default_factory=LoggingConfig)
    vehicle_service_config: VehicleServiceConfig = Field(default_factory=VehicleServiceConfig)
    vehicle_data_grabber_config: WarthogVehicleDataGrabberConfig = Field(
        default_factory=WarthogVehicleDataGrabberConfig
    )
    replay_data_grabber_config: WarthogReplayDataGrabberConfig
