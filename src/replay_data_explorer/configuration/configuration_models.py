import datetime
from abc import ABC
from typing import Annotated, List, Literal, Optional, Union
from enum import Enum
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from src.common.utilities import get_root_directory
from src.common.enums import Country, BattleType
from src.common.configuration.validators import Validators


class GraphExportConfig(BaseModel):
    """Configuration for exporting graphs."""

    output_directory_path: Path = Field(
        default=get_root_directory() / "output" / "graphs",
        description="Directory to save exported graphs.",
    )

    @field_validator("output_directory_path")
    @classmethod
    def ensure_output_directory_exists(cls, v: Path) -> Path:
        return Validators.create_directory_validator(v)

    enable_png_export: bool = Field(
        default=False,
        description="Whether to enable exporting graphs as PNG images.",
    )

    png_width: Optional[int] = Field(
        default=1200,
        description="Width of exported PNG images in pixels.",
    )

    png_height: Optional[int] = Field(
        default=None,
        description="Height of exported PNG images in pixels.",
    )

    png_scale: float = Field(
        default=1.0,
        description="Scale factor for PNG resolution (e.g., 2.0 for 2x resolution).",
    )


class TransactionFlavor(str, Enum):
    """Enum to represent different flavors of transactions in War Thunder."""

    GOLDEN_EAGLES = "golden_eagles"
    PREMIUM_VEHICLE = "premium_vehicle"
    PREMIUM_ACCOUNT = "premium_account"
    PACK = "pack"
    CREW_SLOT = "crew_slot"
    BATTLE_PASS = "battle_pass"


class ActivationFlavor(str, Enum):
    """Enum to represent activation vs purchase for transactions (was the premium vehicle purchased from the store, or received from a battlepass?)"""

    ACTIVATION = "activation"
    PURCHASE = "purchase"


class TransactionModel(ABC, BaseModel):
    """Abstract base model for War Thunder account transactions."""

    activation: ActivationFlavor = Field(description="Whether this transaction represents an activation or purchase.")
    timestamp: datetime = Field(description="The date and time when the transaction occurred.")
    value: float = Field(description="The value of the transaction.")
    currency: str = Field(description="The currency used in the transaction.", default="usd")

    @model_validator(mode="before")
    @classmethod
    def _prevent_direct_instantiation(cls, data: object) -> object:
        if cls is TransactionModel:
            raise TypeError(
                "TransactionModel is abstract and cannot be instantiated directly; use a concrete subclass."
            )
        return data


class TransactionGoldenEagles(TransactionModel):
    flavor: Literal[TransactionFlavor.GOLDEN_EAGLES] = TransactionFlavor.GOLDEN_EAGLES
    amount: int = Field(description="The amount of golden eagles purchased.")


class TransactionPremiumVehicle(TransactionModel):
    flavor: Literal[TransactionFlavor.PREMIUM_VEHICLE] = TransactionFlavor.PREMIUM_VEHICLE
    internal_name: str = Field(description="The internal name of the premium vehicle purchased.")


class TransactionPremiumAccount(TransactionModel):
    flavor: Literal[TransactionFlavor.PREMIUM_ACCOUNT] = TransactionFlavor.PREMIUM_ACCOUNT
    duration_days: int = Field(description="The duration of the premium account purchased, in days.")


class TransactionPack(TransactionModel):
    flavor: Literal[TransactionFlavor.PACK] = TransactionFlavor.PACK
    name: str = Field(description="The name of the pack purchased.")


class TransactionCrewSlot(TransactionModel):
    flavor: Literal[TransactionFlavor.CREW_SLOT] = TransactionFlavor.CREW_SLOT
    country: Country = Field(description="The country for which the crew slot was purchased.")


class TransactionBattlePass(TransactionModel):
    flavor: Literal[TransactionFlavor.BATTLE_PASS] = TransactionFlavor.BATTLE_PASS


# Discriminated union — Pydantic uses the 'flavor' field to deserialize the correct subclass
AnyTransaction = Annotated[
    Union[
        TransactionGoldenEagles,
        TransactionPremiumVehicle,
        TransactionPremiumAccount,
        TransactionPack,
        TransactionCrewSlot,
        TransactionBattlePass,
    ],
    Field(discriminator="flavor"),
]


class WarthogReplayDataExplorerConfig(BaseModel):
    """Replay data explorer specific configuration."""

    player_name: Optional[str] = Field(
        default=None,
        description="Player name to analyze in the replays. If None, the replay author will be analyzed.",
    )

    @field_validator("player_name")
    @classmethod
    def ensure_player_name_isnt_placeholder(cls, v: Optional[str]) -> Optional[str]:
        if v and v == "<username>":  # Technically a player could be named this, but it's super unlikely
            return None
        return v

    country_filters: list[Country] = Field(
        default_factory=list,
        description="List of countries to filter replays by.",
    )

    battle_type: BattleType = Field(
        default=BattleType.REALISTIC,
        description="The type of battle to analyze.",
    )

    standard_deviation: float = Field(
        default=2.0,
        description="Number of standard deviations to use for outlier removal in performance data.",
    )

    graph_export_config: GraphExportConfig = Field(default_factory=GraphExportConfig)

    transactions: List[AnyTransaction] = Field(
        default_factory=list,
        description="List of transactions to configure for the replay data explorer.",
    )
