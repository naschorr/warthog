from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.common.utilities import get_root_directory
from src.common.configuration.validators import Validators


class WtExtCliServiceConfig(BaseModel):
    """Configuration for replay collection and processing."""

    wt_ext_cli_path: Optional[Path] = Field(
        default=None,
        description="Path to the wt_ext_cli executable for parsing War Thunder replay blk data. If None, the service will attempt to discover the executable within the project directory.",
    )

    @field_validator("wt_ext_cli_path")
    @classmethod
    def ensure_wt_ext_cli_path_exists_if_provided(cls, v: Optional[Path]) -> Optional[Path]:
        if v is not None:
            return Validators.file_exists_validator(v)
        return v


class ReplayManagerServiceConfig(BaseModel):
    """Configuration for the Replay Manager Service."""

    processed_replay_dir: Path = Field(
        default=get_root_directory() / "output" / "replays",
        description="Directory to store replays after they've been processed.",
    )

    @field_validator("processed_replay_dir")
    @classmethod
    def ensure_processed_replay_dir_exists(cls, v: Path) -> Path:
        return Validators.directory_exists_validator(v)

    @field_validator("processed_replay_dir")
    @classmethod
    def ensure_processed_replay_dir_absolute(cls, v: Path) -> Path:
        return Validators.directory_absolute_validator(v)

    raw_replay_dir: Path = Field(description="Directory to load raw replay files from")

    @field_validator("raw_replay_dir")
    @classmethod
    def ensure_raw_replay_dir_exists(cls, v: Path) -> Path:
        return Validators.directory_exists_validator(v)

    @field_validator("raw_replay_dir")
    @classmethod
    def ensure_raw_replay_dir_absolute(cls, v: Path) -> Path:
        return Validators.directory_absolute_validator(v)

    allow_overwrite: bool = Field(
        default=False, description="Whether to overwrite existing replays in the processed replay directory."
    )


class WarthogReplayDataGrabberConfig(BaseModel):
    """Replay data grabber specific configuration."""

    wt_ext_cli_service_config: WtExtCliServiceConfig = WtExtCliServiceConfig()
    replay_manager_service_config: ReplayManagerServiceConfig
    overwrite_existing_replays: bool = Field(
        default=False,
        description="Whether to overwrite existing replays in the processed replay directory.",
    )
