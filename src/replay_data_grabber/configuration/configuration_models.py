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


class WarThunderConfig(BaseModel):
    """War Thunder specific configuration."""

    replay_dir: Path = Field(
        description="Directory where War Thunder replays are stored.",
    )

    @field_validator("replay_dir")
    @classmethod
    def ensure_replay_dir_exists(cls, v: Path) -> Path:
        return Validators.directory_exists_validator(v)


class WarthogReplayDataGrabberConfig(BaseModel):
    """Replay data grabber specific configuration."""

    wt_ext_cli_service_config: WtExtCliServiceConfig = WtExtCliServiceConfig()
    replay_manager_service_config: ReplayManagerServiceConfig = ReplayManagerServiceConfig()
    war_thunder_config: WarThunderConfig
    overwrite_existing_replays: bool = Field(
        default=False,
        description="Whether to overwrite existing replays in the processed replay directory.",
    )
