from pathlib import Path
from typing import Optional, Union

from pydantic import Field, field_serializer, field_validator

from enums import Country, VehicleType
from .battle_rating import BattleRating
from models.serializable_model import SerializableModel


class Vehicle(SerializableModel):
    """Represents a vehicle in War Thunder."""

    name: str = Field(description="Name of the vehicle")
    country: Country = Field(description="Country that fielded the vehicle")
    vehicle_type: Optional[VehicleType] = Field(default=None, description="Type of the vehicle")
    rank: int = Field(description="Rank of the vehicle", ge=1)
    battle_rating: BattleRating = Field(default_factory=BattleRating)
    is_premium: bool = Field(description="Indicates if the vehicle is a premium vehicle")

    # Lifecycle

    def __init__(self, **data):
        super().__init__(**data)

    # Magic Methods

    def __str__(self) -> str:
        return f"{self.name} ({self.country.value})"

    def __hash__(self) -> int:
        """Generate a hash based on the vehicle's name and country."""
        return hash((self.name.lower(), self.country.value.lower()))

    # Pydantic De/Serialization

    @field_validator("country", mode="before")
    @classmethod
    def validate_country(cls, v: Union[str, Country]) -> Country:
        """Convert string country values to Country enum."""
        if isinstance(v, str):
            for country_enum in Country:
                if country_enum.value == v:
                    return country_enum
            raise ValueError(f"Invalid country: {v}")
        return v

    @field_serializer("country")
    @classmethod
    def serialize_country(cls, v: Country) -> str:
        """Serialize Country enum to its string value."""
        return v.value if isinstance(v, Country) else str(v)

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def validate_vehicle_type(cls, v: Union[str, VehicleType, None]) -> Optional[VehicleType]:
        """Convert string vehicle type values to VehicleType enum."""
        if isinstance(v, str):
            for vehicle_type_enum in VehicleType:
                if vehicle_type_enum.value == v:
                    return vehicle_type_enum
            raise ValueError(f"Invalid vehicle type: {v}")
        return v

    @field_serializer("vehicle_type")
    @classmethod
    def serialize_vehicle_type(cls, v: VehicleType) -> str:
        """Serialize VehicleType enum to its string value."""
        return v.value if isinstance(v, VehicleType) else str(v)

    # Methods

    def save_to_file(self, directory: Path) -> Path:
        """Save the battle to a JSON file in the specified directory."""
        filename = f"{self.__str__().replace(' ', '_')}.json"
        file_path = directory / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

        return file_path
