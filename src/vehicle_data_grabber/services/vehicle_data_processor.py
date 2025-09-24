import logging

logger = logging.getLogger(__name__)

import re
from pathlib import Path
from typing import Optional

from src.common.utilities import JsonTools
from src.common.enums import Country, VehicleType
from src.common.models.vehicle_models import Vehicle
from src.common.configuration import KwargConfiguration
from src.vehicle_data_grabber.configuration import VehicleDataProcessorConfig


class VehicleDataProcessor(KwargConfiguration[VehicleDataProcessorConfig]):
    """
    Processes raw, data-mined War Thunder vehicle data into a structured format that can be more easily used by Warthog.

    Uses data from: https://github.com/gszabi99/War-Thunder-Datamine

    Note that this processor class should be used infrequently, generally after major game updates where vehicle data (ex: battle ratings) has changed.
    TODO: This should really be automated to run after the relevant data is updated in the remote repository, but we'll keep it manual for now.
    """

    # Lifecycle

    def __init__(self, config: VehicleDataProcessorConfig, **kwargs):
        super().__init__(config, **kwargs)

    # Methods

    def process_vehicle_data(
        self, *, repository_version: str, repository_path: Path, output_path: Optional[Path] = None
    ) -> dict[str, Vehicle]:
        """Processes the vehicle data from the repository, building structured data for each vehicle currently available"""

        # Validate file input/output
        if not repository_path.exists() or not repository_path.is_dir():
            raise ValueError(f"Repository path {repository_path} does not exist or is not a directory.")
        if not output_path:
            output_path = (
                self._config.processed_data_directory_path / f"processed_vehicle_data.{repository_version}.json"
            )

        # Load datamined files
        hangar_blkx_data = self._load_hangar_blkx(repository_path / self._config.hangar_blkx_file_path)
        unittags_blkx_data = self._load_unittags_blkx(repository_path / self._config.unittags_blkx_file_path)
        wpcost_blkx_data = self._load_wpcost_blkx(repository_path / self._config.wpcost_blkx_file_path)
        units_csv_data = self._load_units_csv(repository_path / self._config.units_csv_file_path)

        # Process the datamined files into Vehicle data
        internal_name_to_shop_name_map = self._get_internal_name_to_shop_name_map(units_csv_data)
        premium_vehicle_list = self._build_premium_vehicle_list(wpcost_blkx_data, hangar_blkx_data)
        internal_name_to_vehicle_map = self._build_internal_name_to_vehicle_map(
            internal_name_to_shop_name_map,
            premium_vehicle_list,
            wpcost_blkx_data,
            unittags_blkx_data,
        )

        # Store the processed vehicle data
        self._store_vehicle_map_json(internal_name_to_vehicle_map, output_path)

        return internal_name_to_vehicle_map

    def get_datamined_file_paths(self) -> list[Path]:
        """Returns the paths of the datamined files used by the processor, relative to the repository root."""
        return [
            self._config.hangar_blkx_file_path,
            self._config.unittags_blkx_file_path,
            self._config.wpcost_blkx_file_path,
            self._config.units_csv_file_path,
        ]

    def _clean_unicode_string(self, text: str) -> str:
        """
        Clean Unicode characters from the beginning of strings.
        Removes common Unicode symbols, private use characters, and control characters.
        """
        if not text:
            return text

        replacement_patterns = {
            r"\xa0": " ",  # Non-breaking space to regular space
            r"\"": "",  # Remove quotes
        }
        for pattern, replacement in replacement_patterns.items():
            text = re.sub(pattern, replacement, text)

        # Define Unicode patterns to remove from the beginning of strings
        unicode_patterns = [
            r"[\uf000-\uf8ff]+",  # Private Use Area (various icons/symbols)
            r"[\u0000-\u001f]+",  # Control characters (C0)
            r"[\u007f-\u009f]+",  # Control characters (C1)
            r"[\u2000-\u206f]+",  # General Punctuation
            r"[\u2200-\u22ff]+",  # Mathematical Operators
            r"[\u2400-\u24ff]+",  # Control Pictures
            r"[\u2500-\u25ff]+",  # Box Drawing and Block Elements
            r"[\u2600-\u26ff]+",  # Miscellaneous Symbols
            r"[\u2700-\u27bf]+",  # Dingbats
            r"[\ue000-\uf8ff]+",  # Private Use Area (broader range)
        ]
        # Apply each pattern to clean the text
        for pattern in unicode_patterns:
            text = re.sub(pattern, "", text)

        # Map specific Unicode characters to ASCII equivalents
        unicode_to_ascii_map = {
            r"\u0422": "T",  # Map Cyrillic 'Т' to ASCII 'T'
            r"\u0410": "A",  # Map Cyrillic 'А' to ASCII 'A'
            r"\u041c": "M",  # Map Cyrillic 'М' to ASCII 'M'
            r"\u041a": "K",  # Map Cyrillic 'К' to ASCII 'K'
            r"\u0421": "C",  # Map Cyrillic 'С' to ASCII 'C'
        }
        for pattern, replacement in unicode_to_ascii_map.items():
            text = re.sub(pattern, replacement, text)

        # Strip any remaining whitespace from both ends
        return text.strip()

    def _store_vehicle_map_json(self, data: dict[str, Vehicle], output_path: Path) -> None:
        serializable_data = {key: vehicle.model_dump() for key, vehicle in data.items()}
        JsonTools.save_json(serializable_data, output_path)

    def _load_wpcost_blkx(self, wpcost_blkx_path: Path) -> dict:
        return JsonTools.load_json(wpcost_blkx_path)

    def _load_unittags_blkx(self, unittags_blkx_path: Path) -> dict:
        return JsonTools.load_json(unittags_blkx_path)

    def _load_hangar_blkx(self, hangar_blkx_path: Path) -> dict:
        return JsonTools.load_json(hangar_blkx_path)

    def _load_units_csv(self, units_csv_path: Path) -> list[tuple[str, str]]:
        with open(units_csv_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            output: list[tuple[str, str]] = []

            for line in lines[1:]:
                parts: list[str] = []
                for part in line.strip().split(";")[:2]:
                    # Clean the part by removing quotes and cleaning Unicode
                    part = part.strip('"')
                    part = self._clean_unicode_string(part)
                    parts.append(part)

                if any([not part.strip() for part in parts]):
                    continue

                # Only keep the internal name for the vehicle (0) and the formal name of the vehicle in English (1) for now
                output.append((parts[0], parts[1]))

        return output

    def _get_internal_name_to_shop_name_map(self, unit_csv_data: list[tuple[str, str]]) -> dict[str, str]:
        seen_internal_names = set()
        internal_name_to_shop_name_map: dict[str, str] = {}
        for raw_internal_name, shop_name in unit_csv_data:
            if not raw_internal_name.endswith("_shop"):
                # Skip internal names that do not end with "_shop"
                continue

            internal_name = raw_internal_name.removesuffix("_shop")
            if internal_name in seen_internal_names:
                # If we have already seen this internal name, skip it to avoid duplicates
                continue

            seen_internal_names.add(internal_name)
            internal_name_to_shop_name_map[internal_name] = shop_name

        return internal_name_to_shop_name_map

    def _build_premium_vehicle_list(self, wpcost_blkx_data: dict, hangar_blkx_data: dict) -> list[str]:
        premium_vehicles = set()

        for internal_name, vehicle_data in wpcost_blkx_data.items():
            if not isinstance(vehicle_data, dict):
                continue

            if vehicle_data.get("costGold", 0) > 0:
                premium_vehicles.add(internal_name)
            elif vehicle_data.get("gift") is not None:
                premium_vehicles.add(internal_name)

        for vehicle in hangar_blkx_data.get("premiumVehicle", []):
            unit_name = vehicle.get("unitName")
            if unit_name:
                premium_vehicles.add(unit_name)

        return list(premium_vehicles)

    def _calculate_battle_rating_from_economic_rating(self, economic_rating: int) -> float:
        return round(economic_rating / 3 + 1, 1)

    def _get_country_from_tags(self, tag_data: dict) -> Country:
        tags = tag_data.get("tags", {}).keys()

        if "country_australia" in tags:
            return Country.UK
        elif "country_belgium" in tags:
            return Country.FRANCE
        elif "country_britain" in tags:
            return Country.UK
        elif "country_china" in tags:
            return Country.CHINA
        elif "country_finland" in tags:
            return Country.SWEDEN
        elif "country_france" in tags:
            return Country.FRANCE
        elif "country_germany" in tags:
            return Country.GERMANY
        elif "country_hungary" in tags:
            return Country.ITALY
        elif "country_indonesia" in tags:
            return Country.JAPAN
        elif "country_israel" in tags:
            return Country.ISRAEL
        elif "country_italy" in tags:
            return Country.ITALY
        elif "country_japan" in tags:
            return Country.JAPAN
        elif "country_netherlands" in tags:
            return Country.FRANCE
        elif "country_south_africa" in tags:
            return Country.UK
        elif "country_sweden" in tags:
            return Country.SWEDEN
        elif "country_switzerland" in tags:
            return Country.GERMANY
        elif "country_thailand" in tags:
            return Country.JAPAN
        elif "country_turkey" in tags:
            return Country.ITALY
        elif "country_usa" in tags:
            return Country.USA
        elif "country_ussr" in tags:
            return Country.RUSSIA

        # If no known country is found, raise an error
        raise ValueError(f"Unknown country in tags: {tags}")

    def _get_vehicle_type_from_tags(self, tag_data: dict) -> VehicleType:
        tags = tag_data.get("tags", {}).keys()

        # Air vehicle types
        if "type_fighter" in tags:
            return VehicleType.FIGHTER
        elif "type_strike_aircraft" in tags:
            return VehicleType.STRIKE_AIRCRAFT
        elif "type_bomber" in tags:
            return VehicleType.BOMBER
        elif "type_strike_ucav" in tags:
            return VehicleType.STRIKE_AIRCRAFT

        # Helicopter types
        elif "type_attack_helicopter" in tags:
            return VehicleType.ATTACK_HELICOPTER
        elif "type_utility_helicopter" in tags:
            return VehicleType.UTILITY_HELICOPTER

        # Ground vehicle types
        elif "type_light_tank" in tags:
            return VehicleType.LIGHT_TANK
        elif "type_medium_tank" in tags:
            return VehicleType.MEDIUM_TANK
        elif "type_heavy_tank" in tags:
            return VehicleType.HEAVY_TANK
        elif "type_tank_destroyer" in tags:
            return VehicleType.TANK_DESTROYER
        elif "type_spaa" in tags:
            return VehicleType.ANTI_AIR

        # Bluewater fleet vehicle types
        elif "type_destroyer" in tags:
            return VehicleType.DESTROYER
        elif "type_light_cruiser" in tags:
            return VehicleType.LIGHT_CRUISER
        elif "type_heavy_cruiser" in tags:
            return VehicleType.HEAVY_CRUISER
        elif "type_battleship" in tags:
            return VehicleType.BATTLESHIP
        elif "type_battlecruiser" in tags:
            return VehicleType.BATTLECRUISER

        # Coastal fleet vehicle types
        elif "type_barge" in tags:
            return VehicleType.BARGE
        elif "type_boat" in tags:
            return VehicleType.BOAT
        elif "type_heavy_boat" in tags:
            return VehicleType.HEAVY_BOAT
        elif "type_frigate" in tags:
            return VehicleType.FRIGATE

        # If no known type is found, raise an error
        raise ValueError(f"Unknown vehicle type in tags: {tags}")

    def _build_internal_name_to_vehicle_map(
        self,
        internal_name_to_shop_name_map: dict[str, str],
        premium_vehicle_list: list[str],
        wpcost_blkx_data: dict,
        unittags_blkx_data: dict,
    ) -> dict[str, Vehicle]:
        output: dict[str, Vehicle] = {}
        for internal_name, shop_name in internal_name_to_shop_name_map.items():
            if internal_name not in wpcost_blkx_data:
                logger.warning(f"Internal name '{internal_name}' not found in wpcost_blkx data. Skipping.")
                continue

            vehicle_data = wpcost_blkx_data.get(internal_name)
            if not vehicle_data:
                logger.warning(f"Vehicle data for internal name '{internal_name}' is empty or missing. Skipping.")
                continue

            tag_data = unittags_blkx_data.get(internal_name)
            if not tag_data:
                logger.warning(f"Tag data for internal name '{internal_name}' is empty or missing. Skipping.")
                continue

            # Get the country from the tags
            try:
                country = self._get_country_from_tags(tag_data)
            except ValueError as e:
                logger.error(f"Error extracting country from tags for internal name '{internal_name}': {e}")
                raise e

            # Get the vehicle type from the tags
            vehicle_type = self._get_vehicle_type_from_tags(tag_data)

            battle_rating = {
                "arcade": self._calculate_battle_rating_from_economic_rating(vehicle_data.get("economicRankArcade", 0)),
                "realistic": self._calculate_battle_rating_from_economic_rating(
                    vehicle_data.get("economicRankHistorical", 0)
                ),
                "simulation": self._calculate_battle_rating_from_economic_rating(
                    vehicle_data.get("economicRankSimulation", 0)
                ),
            }
            rank = vehicle_data.get("rank")
            if rank is None:
                logger.warning(f"Rank for internal name '{internal_name}' is missing. Skipping...")
                continue

            vehicle = Vehicle(
                name=self._clean_unicode_string(shop_name),
                country=country,
                vehicle_type=vehicle_type,
                rank=int(rank),
                battle_rating=battle_rating,
                is_premium=internal_name in premium_vehicle_list,
            )

            output[internal_name] = vehicle

        return output
