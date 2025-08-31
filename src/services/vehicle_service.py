import logging

logger = logging.getLogger(__name__)

import json
import re
from pathlib import Path
from typing import Optional

from enums import Country, VehicleType
from models.vehicle_models import Vehicle


class VehicleService:
    """
    Handles operations related to War Thunder vehicle data.
    """

    # Statics

    VEHICLE_NAME_COUNTRY_REGEX = re.compile(r"^(.+?)\s*\(([^)\d]+)\)$")

    ## Lifecycle

    def __init__(self, vehicle_data_path: Path):
        self._vehicle_data_path = vehicle_data_path
        self._vehicle_data = self._load_vehicle_data(self._vehicle_data_path)

    ## Methods

    def _load_vehicle_data(self, vehicle_data_path: Path) -> dict[str, Vehicle]:
        """Load vehicle data from the processed JSON file."""
        if not self._vehicle_data_path.exists():
            raise ValueError(f"Vehicle data file not found at {self._vehicle_data_path}")

        with open(self._vehicle_data_path, "r", encoding="utf-8") as file:
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
        return vehicles

    def get_vehicles_by_name(
        self, name: str, *, country: Optional[Country] = None, exact_match: bool = False
    ) -> list[Vehicle]:
        """
        Find vehicles by name.

        Args:
            name: The name to search for, optionally in format "Vehicle Name (Country)"
            exact_match: If True, only return exact matches. If False, return partial matches.

        Returns:
            List of matching Vehicle objects
        """
        if not name:
            return []

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

        for candidate_vehicle in self._vehicle_data.values():
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

    def get_vehicles_by_internal_name(self, internal_name: str) -> Optional[Vehicle]:
        """
        Get a vehicle by its internal name.
        """
        return self._vehicle_data.get(internal_name)

    def get_all_vehicles(self) -> dict[str, Vehicle]:
        """
        Get all loaded vehicles.
        """
        return self._vehicle_data.copy()

    def get_vehicles_by_country(self, country: Country) -> list[Vehicle]:
        """
        Get all vehicles from a specific country.
        """
        matches = []

        for vehicle in self._vehicle_data.values():
            if vehicle.country == country:
                matches.append(vehicle)

        return matches

    def get_vehicles_by_type(self, vehicle_type: VehicleType) -> list[Vehicle]:
        """
        Get all vehicles of a specific type.
        """
        matches = []

        for vehicle in self._vehicle_data.values():
            if vehicle.vehicle_type == vehicle_type:
                matches.append(vehicle)

        return matches

    def is_vehicle_premium(self, vehicle_internal_names: list[str]) -> bool:
        """
        Check if any vehicle in a list of vehicles is premium.
        """

        for internal_name in vehicle_internal_names:
            vehicle = self.get_vehicles_by_internal_name(internal_name)
            if vehicle and vehicle.is_premium:
                return True

        return False
