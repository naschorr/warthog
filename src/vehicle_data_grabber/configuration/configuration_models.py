from pathlib import Path

from pydantic import BaseModel, Field, field_validator, HttpUrl

from src.common.utilities import get_root_directory
from src.common.configuration.validators import Validators


class VehicleDataOrchestratorConfig(BaseModel):
    """Configuration for the vehicle data orchestrator."""

    working_directory_path: Path = Field(
        description="Working directory for cloning and processing the datamine repository.",
        default=get_root_directory() / "temp",
    )

    @field_validator("working_directory_path")
    @classmethod
    def ensure_working_directory_exists(cls, v: Path) -> Path:
        return Validators.directory_exists_validator(v)

    @field_validator("working_directory_path")
    @classmethod
    def ensure_working_dir_absolute(cls, v: Path) -> Path:
        return Validators.directory_absolute_validator(v)

    repository_url: HttpUrl = Field(
        description="URL of the War Thunder datamine repository",
        default=HttpUrl("https://github.com/gszabi99/War-Thunder-Datamine"),
    )

    game_versions: list[str] = Field(
        description="List of game versions to support (major revisions since the start of data collection)",
        default=[],
    )

    datamine_data_directory_path: Path = Field(
        description="Directory to save datamined data files.",
        default=get_root_directory() / "data" / "vehicle_data" / "datamine_vehicle_data",
    )

    @field_validator("datamine_data_directory_path")
    @classmethod
    def ensure_datamine_data_directory_exists(cls, v: Path) -> Path:
        return Validators.directory_exists_validator(v)

    @field_validator("datamine_data_directory_path")
    @classmethod
    def ensure_datamine_data_dir_absolute(cls, v: Path) -> Path:
        return Validators.directory_absolute_validator(v)

    store_datamine_data: bool = Field(
        description="Whether to store datamined data files locally (to avoid checking out the repository repeatedly)",
        default=True,
    )

    skip_stored_datamine_data: bool = Field(
        description="Whether to skip datamine data if it has already been stored locally.", default=True
    )

    game_version_release_datetimes_file_path: Path = Field(
        description="Path to a JSON file mapping game versions to their release datetimes.",
        default=get_root_directory() / "data" / "vehicle_data" / "game_version_release_datetimes.json",
    )

    @field_validator("game_version_release_datetimes_file_path")
    @classmethod
    def ensure_game_version_release_datetimes_file_path_exists(cls, v: Path) -> Path:
        return Validators.file_exists_validator(v)


class VehicleDataProcessorConfig(BaseModel):
    """Configuration for the vehicle data processor."""

    processed_data_directory_path: Path = Field(
        description="Directory to save processed vehicle data files.",
        default=get_root_directory() / "data" / "vehicle_data" / "processed_vehicle_data",
    )

    @field_validator("processed_data_directory_path")
    @classmethod
    def ensure_processed_data_directory_exists(cls, v: Path) -> Path:
        return Validators.directory_exists_validator(v)

    hangar_blkx_file_path: Path = Field(
        description="Path of the datamined hangar.blkx file used for vehicle info, relative to the repository's root.",
        default=Path("aces.vromfs.bin_u") / "config" / "hangar.blkx",
    )

    unittags_blkx_file_path: Path = Field(
        description="Path of the datamined unittags.blkx file used for vehicle tags, relative to the repository's root.",
        default=Path("char.vromfs.bin_u") / "config" / "unittags.blkx",
    )

    wpcost_blkx_file_path: Path = Field(
        description="Path of the datamined wpcost.blkx file used for vehicle costs and battle ratings, relative to the repository's root.",
        default=Path("char.vromfs.bin_u") / "config" / "wpcost.blkx",
    )

    units_csv_file_path: Path = Field(
        description="Name of the datamined units.csv file used for vehicle data, relative to the repository's root.",
        default=Path("lang.vromfs.bin_u") / "lang" / "units.csv",
    )


class WarthogVehicleDataGrabberConfig(BaseModel):
    """Vehicle data configuration."""

    vehicle_data_orchestrator_config: VehicleDataOrchestratorConfig = Field(
        default_factory=VehicleDataOrchestratorConfig
    )
    vehicle_data_processor_config: VehicleDataProcessorConfig = Field(default_factory=VehicleDataProcessorConfig)
