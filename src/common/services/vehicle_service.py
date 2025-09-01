import logging

logger = logging.getLogger(__name__)

import json
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.common.configuration import VehicleServiceConfig
from src.common.enums import Country, VehicleType
from src.common.models.vehicle_models import Vehicle


class VehicleService:
    """
    Handles operations related to War Thunder vehicle data.
    """

    # Statics

    VEHICLE_NAME_COUNTRY_REGEX = re.compile(r"^(.+?)\s*\(([^)\d]+)\)$")

    ## Lifecycle

    def __init__(self, config: VehicleServiceConfig):
        self._config = config

        self._vehicle_data_directory_path = self._config.processed_vehicle_data_directory_path
        self._game_version_to_release_datetime_path = self._config.game_version_to_release_datetime_file_path

        self._vehicle_data = self._load_vehicle_data(
            self._vehicle_data_directory_path, self._game_version_to_release_datetime_path
        )

    ## Methods

    def _load_vehicle_data(
        self, vehicle_data_directory_path: Path, game_version_to_release_datetime_path: Path
    ) -> dict[datetime, dict[str, Vehicle]]:
        """
        Load vehicle data from directory containing the processed JSON files.
        """
        # Validate paths
        if not vehicle_data_directory_path.exists():
            raise ValueError(f"Vehicle data directory not found at {vehicle_data_directory_path}")
        if not game_version_to_release_datetime_path.exists():
            raise ValueError(
                f"Game version to release datetime file not found at {game_version_to_release_datetime_path}"
            )

        # Load game version to release datetime mapping
        game_version_to_release_datetime: dict[str, datetime] = {}
        with open(game_version_to_release_datetime_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            for version, datetime_str in data.items():
                try:
                    game_version_to_release_datetime[version] = datetime.fromisoformat(datetime_str)
                except ValueError as e:
                    logger.error(
                        f"Invalid datetime format for version {version} in {game_version_to_release_datetime_path}: {e}"
                    )

        # Build output map
        datetime_to_vehicle_data: dict[datetime, dict[str, Vehicle]] = {}

        # Find all candidate processed vehicle data files
        processed_vehicle_data_paths = list(vehicle_data_directory_path.glob("*.json"))
        for vehicle_data_path in processed_vehicle_data_paths:
            # Extract the game version from the file name
            file_name = vehicle_data_path.stem
            file_name_parts = file_name.split(".")
            game_version = ".".join(file_name_parts[1:])

            with open(vehicle_data_path, "r", encoding="utf-8") as file:
                raw_data = json.load(file)

            # Convert dictionaries back to Vehicle objects
            vehicles: dict[str, Vehicle] = {}
            for internal_name, vehicle_data in raw_data.items():
                try:
                    # Pydantic will automatically convert string enum values to actual enums
                    vehicle = Vehicle.model_validate(vehicle_data)
                    vehicles[internal_name] = vehicle
                except Exception as e:
                    logger.error(f"Failed to load vehicle {internal_name}: {e}")

            logger.info(f"Loaded {len(vehicles)} vehicles from {vehicle_data_path}")
            datetime_to_vehicle_data[game_version_to_release_datetime[game_version]] = vehicles

        return datetime_to_vehicle_data

    def _get_vehicle_data_bucket(self, search_datetime: datetime) -> dict[str, Vehicle]:
        """
        Get the vehicle data bucket for a specific datetime.
        """
        datetime_buckets = sorted(self._vehicle_data.keys(), reverse=True)
        best_datetime_bucket: Optional[datetime] = None
        previous_datetime_bucket: Optional[datetime] = None
        for datetime_bucket in datetime_buckets:
            if previous_datetime_bucket is not None:
                if search_datetime >= datetime_bucket and search_datetime <= previous_datetime_bucket:
                    best_datetime_bucket = datetime_bucket

                if search_datetime >= previous_datetime_bucket:
                    best_datetime_bucket = previous_datetime_bucket
                    # We've passed the search datetime, so we can stop looking
                    break

            previous_datetime_bucket = datetime_bucket

        # No bucket? Use the newest one.
        if best_datetime_bucket is None:
            best_datetime_bucket = datetime_buckets[0]

        return self._vehicle_data[best_datetime_bucket]

    def get_vehicles_by_name(
        self,
        name: str,
        *,
        country: Optional[Country] = None,
        exact_match: bool = False,
        search_datetime: Optional[datetime] = None,
    ) -> list[Vehicle]:
        """
        Find vehicles by name.

        Args:
            name: Name or partial name of the vehicle to search for.
            country: Optional country to filter by.
            exact_match: Whether to require an exact match (default is False, which allows partial matches).
            search_datetime: Optional datetime to filter vehicles available up to that date (default is None, which uses the latest data).

        Returns:
            List of matching Vehicle objects
        """
        search_vehicle_name = name.strip().lower()
        search_vehicle_country = country
        vehicle_matches = []

        # Check if name contains country specification in format "Name (Country)"
        country_match_candidate = self.VEHICLE_NAME_COUNTRY_REGEX.match(search_vehicle_name)
        country_match_found = False
        if country_match_candidate:
            # Validate the country
            country_name_candidate = country_match_candidate.group(2).strip()
            if country_name_candidate:
                try:
                    search_vehicle_country = Country.get_country_by_name(country_name_candidate)
                    country_match_found = True
                except ValueError:
                    logger.warning(f"Invalid country name '{country_name_candidate}' in vehicle name '{name}'")

            # If a valid country was found, then we can also use the extracted name when searching
            if country_match_found:
                search_vehicle_name = country_match_candidate.group(1).strip().lower()

        # Strip quotes and empty parentheses from the name for improved searching
        search_vehicle_name = search_vehicle_name.replace('"', "")
        search_vehicle_name = search_vehicle_name.replace("()", "")

        # Find the most recent vehicle data up to the search datetime
        search_datetime = search_datetime or datetime.now()
        vehicle_data = self._get_vehicle_data_bucket(search_datetime)

        for candidate_vehicle in vehicle_data.values():
            candidate_vehicle_name = candidate_vehicle.name.lower()

            if exact_match:
                if search_vehicle_name == candidate_vehicle_name and (
                    search_vehicle_country is None or search_vehicle_country == candidate_vehicle.country
                ):
                    vehicle_matches.append(candidate_vehicle)
            else:
                if search_vehicle_name in candidate_vehicle_name and (
                    search_vehicle_country is None or search_vehicle_country == candidate_vehicle.country
                ):
                    vehicle_matches.append(candidate_vehicle)

        return vehicle_matches

    def get_vehicles_by_internal_name(
        self, internal_name: str, *, search_datetime: Optional[datetime] = None
    ) -> Optional[Vehicle]:
        """
        Get a vehicle by its internal name.
        """
        search_datetime = search_datetime or datetime.now()
        vehicle_data = self._get_vehicle_data_bucket(search_datetime)

        return vehicle_data.get(internal_name)

    def get_all_vehicles(self, *, search_datetime: Optional[datetime] = None) -> dict[str, Vehicle]:
        """
        Get all loaded vehicles.
        """
        search_datetime = search_datetime or datetime.now()
        vehicle_data = self._get_vehicle_data_bucket(search_datetime)

        return vehicle_data

    def get_vehicles_by_country(self, country: Country, *, search_datetime: Optional[datetime] = None) -> list[Vehicle]:
        """
        Get all vehicles from a specific country.
        """
        matches = []

        search_datetime = search_datetime or datetime.now()
        vehicle_data = self._get_vehicle_data_bucket(search_datetime)

        for vehicle in vehicle_data.values():
            if vehicle.country == country:
                matches.append(vehicle)

        return matches

    def get_vehicles_by_type(
        self, vehicle_type: VehicleType, *, search_datetime: Optional[datetime] = None
    ) -> list[Vehicle]:
        """
        Get all vehicles of a specific type.
        """
        matches = []

        search_datetime = search_datetime or datetime.now()
        vehicle_data = self._get_vehicle_data_bucket(search_datetime)

        for vehicle in vehicle_data.values():
            if vehicle.vehicle_type == vehicle_type:
                matches.append(vehicle)

        return matches

    def is_vehicle_premium(
        self, vehicle_internal_names: list[str], *, search_datetime: Optional[datetime] = None
    ) -> bool:
        """
        Check if any vehicle in a list of vehicles is premium.
        """

        for internal_name in vehicle_internal_names:
            vehicle = self.get_vehicles_by_internal_name(internal_name, search_datetime=search_datetime)
            if vehicle and vehicle.is_premium:
                return True

        return False
