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
            internal_name_to_shop_name_map, premium_vehicle_list, wpcost_blkx_data, unittags_blkx_data, hangar_blkx_data
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
                try:
                    output.append((parts[0], parts[1]))
                except IndexError:
                    logger.warning(f"Could not parse line in units CSV: {line.strip()}")
                    continue

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

    def _get_country_from_internal_name(self, internal_name: str) -> Country:
        if internal_name.startswith("cn_") or internal_name.endswith("_china"):
            return Country.CHINA
        elif internal_name.startswith("fr_") or internal_name.endswith("_france"):
            return Country.FRANCE
        elif internal_name.startswith("germ_") or internal_name.endswith("_germ") or internal_name.endswith("_germany"):
            return Country.GERMANY
        elif internal_name.startswith("il_") or internal_name.endswith("_iaf"):
            return Country.ISRAEL
        elif internal_name.startswith("it_") or internal_name.endswith("_italy"):
            return Country.ITALY
        elif internal_name.startswith("jp_") or internal_name.endswith("_japan"):
            return Country.JAPAN
        elif internal_name.startswith("sw_") or internal_name.endswith("_sweden"):
            return Country.SWEDEN
        elif internal_name.startswith("uk_") or internal_name.endswith("_britain"):
            return Country.UK
        elif internal_name.startswith("us_") or internal_name.endswith("_usa"):
            return Country.USA
        elif internal_name.startswith("ussr_") or internal_name.endswith("_ussr"):
            return Country.RUSSIA

        # If no known country prefix is found, raise an error
        raise ValueError(f"Unknown country for internal name: {internal_name}")

    def _get_country_from_country_name(self, country_name: str) -> Country:
        if country_name == "country_britain":
            return Country.UK
        elif country_name == "country_china":
            return Country.CHINA
        elif country_name == "country_france":
            return Country.FRANCE
        elif country_name == "country_germany":
            return Country.GERMANY
        elif country_name == "country_israel":
            return Country.ISRAEL
        elif country_name == "country_italy":
            return Country.ITALY
        elif country_name == "country_japan":
            return Country.JAPAN
        elif country_name == "country_sweden":
            return Country.SWEDEN
        elif country_name == "country_usa":
            return Country.USA
        elif country_name == "country_ussr":
            return Country.RUSSIA

        raise ValueError(f"Unknown country for country name: {country_name}")

    def _get_country_from_tags(self, tag_data: dict) -> Country:
        tag_country = next((key for key in tag_data.get("tags", {}).keys() if key.startswith("country_")), None)
        if tag_country is None:
            raise ValueError("No country tag found in tag data.")

        return self._get_country_from_country_name(tag_country)

    def _get_country_from_hangar(self, internal_name: str, hangar_data: dict) -> Country:
        def search_for_vehicle(data, current_country=None):
            """Recursively search for the vehicle internal name in the data structure"""
            if isinstance(data, dict):
                # Check if this dict has a key starting with "country_"
                country_key = next((key for key in data.keys() if key.startswith("country_")), None)
                if country_key:
                    current_country = country_key

                # Search through all items in the dict
                for key, value in data.items():
                    if key == internal_name or value == internal_name:
                        # Found it! Return the current country
                        if current_country:
                            return current_country

                    # Recursively search in nested structures
                    result = search_for_vehicle(value, current_country)
                    if result:
                        return result

            elif isinstance(data, list):
                # Search through list items
                for item in data:
                    result = search_for_vehicle(item, current_country)
                    if result:
                        return result

            return None

        country_key = search_for_vehicle(hangar_data)

        if not country_key:
            raise ValueError(f"Vehicle '{internal_name}' not found in hangar data")

        return self._get_country_from_country_name(country_key)

    def _get_country_from_fallback(self, internal_name: str, tag_data: dict) -> Country:
        operator_country = tag_data.get("operatorCountry")

        ## Some operator countries work exclusively with main countries, or only have a couple exclusions
        ## Note that this ignores internal names that have a country tag, and ones that have a correct country tag. This
        ## leaves mostly just specific aircraft that have a country tag set to the operator country (see h-75a-2_finland
        ## as an example).
        if operator_country == "country_argentina":
            return Country.GERMANY

        if operator_country == "country_austria":
            raise ValueError(
                "Austria isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_austria"
            )

        if operator_country == "country_australia":
            return Country.UK

        if operator_country == "country_bangladesh":
            return Country.CHINA

        if operator_country == "country_belgium":
            return Country.FRANCE

        if operator_country == "country_brazil":
            raise ValueError(
                "Brazil isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_brazil"
            )

        if operator_country == "country_britain":
            return Country.UK

        if operator_country == "country_canada" or operator_country == "country_canada_modern":
            return Country.UK

        if operator_country == "country_china":
            return Country.CHINA

        if operator_country == "country_colombia":
            raise ValueError(
                "Colombia isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_colombia"
            )

        if operator_country == "country_cuba":
            raise ValueError(
                "Cuba isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_cuba"
            )

        if operator_country == "country_czech":
            return Country.RUSSIA

        if operator_country == "country_denmark":
            return Country.SWEDEN

        if operator_country == "country_egypt":
            return Country.RUSSIA

        if operator_country == "country_finland":
            if internal_name in ["h-75a-2_finland"]:
                return Country.GERMANY
            else:
                return Country.SWEDEN

        if operator_country == "country_france":
            return Country.FRANCE

        if (
            operator_country == "country_germany"
            or operator_country == "country_gdr"
            or operator_country == "country_germany_empire"
            or operator_country == "country_germany_weimar_republic"
        ):
            return Country.GERMANY

        if operator_country == "country_greece_modern":
            raise ValueError(
                "Greece isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_greece_modern"
            )

        if operator_country == "country_hungary" or operator_country == "country_hungary_modern":
            if internal_name in ["he_112b_1"]:
                return Country.GERMANY
            else:
                return Country.ITALY

        if operator_country == "country_india":
            return Country.UK

        if operator_country == "country_indonesia":
            return Country.JAPAN

        if operator_country == "country_iran":
            raise ValueError(
                "Iran isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_iran"
            )

        if operator_country == "country_ireland":
            raise ValueError(
                "Ireland isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_ireland"
            )

        if operator_country == "country_israel":
            return Country.ISRAEL

        if operator_country == "country_italy" or operator_country == "country_italy_kingdom":
            return Country.ITALY

        if operator_country == "country_japan":
            return Country.JAPAN

        if operator_country == "country_jordan":
            raise ValueError(
                "Jordan isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_jordan"
            )

        if operator_country == "country_kazakhstan":
            raise ValueError(
                "Kazakhstan isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_kazakhstan"
            )

        if operator_country == "country_kuwait":
            raise ValueError(
                "Kuwait isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_kuwait"
            )

        if operator_country == "country_lithuania":
            raise ValueError(
                "Lithuania isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_lithuania"
            )

        if operator_country == "country_malaysia":
            return Country.JAPAN

        if operator_country == "country_netherlands":
            return Country.FRANCE

        if operator_country == "country_new_zealand":
            return Country.UK

        if operator_country == "country_north_korea":
            ## This'll almost certainly be China, but who knows if there's be some weird Russian shenanigans in the
            ## future. Currently their only plane is correctly tagged as Chinese, so this shouldn't be raised.
            raise ValueError(
                "North Korea isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_north_korea"
            )

        if operator_country == "country_norway":
            return Country.SWEDEN

        if operator_country == "country_oman":
            raise ValueError(
                "Oman isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_oman"
            )

        if operator_country == "country_pakistan":
            return Country.CHINA

        if operator_country == "country_philippines":
            raise ValueError(
                "The Philippines isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_philippines"
            )

        if operator_country == "country_poland":
            raise ValueError(
                "Poland isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_poland"
            )

        if operator_country == "country_portugal":
            raise ValueError(
                "Portugal isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_portugal"
            )

        if operator_country == "country_romania":
            return Country.ITALY

        if (
            operator_country == "country_russia"
            or operator_country == "country_ussr"
            or operator_country == "country_russia_empire"
        ):
            return Country.RUSSIA

        if operator_country == "country_saudi_arabia":
            raise ValueError(
                "Saudi Arabia isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_saudi_arabia"
            )

        if operator_country == "country_slovakia":
            raise ValueError(
                "Slovakia isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_slovakia"
            )

        if operator_country == "country_south_africa" or operator_country == "country_south_africa_modern":
            return Country.UK

        if operator_country == "country_south_vietnam":
            ## This'll almost certainly be USA in the future. Their only boat is correctly tagged as American.
            raise ValueError(
                "South Vietnam isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_south_vietnam"
            )

        if operator_country == "country_spain":
            if internal_name in ["tiger_had_spain"]:
                return Country.GERMANY
            raise ValueError(
                "Spain isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_spain"
            )

        if operator_country == "country_sweden":
            return Country.SWEDEN

        if operator_country == "country_switzerland":
            return Country.GERMANY

        if operator_country == "country_syria":
            if internal_name in ["su_22m3"]:
                return Country.RUSSIA
            raise ValueError(
                "Syria isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_syria"
            )

        if operator_country == "country_thailand":
            return Country.JAPAN

        if operator_country == "country_turkey":
            return Country.ITALY

        if operator_country == "country_usa" or operator_country == "country_usa_modern":
            return Country.USA

        if operator_country == "country_venezuela":
            raise ValueError(
                "Venezuela isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_venezuela"
            )

        if operator_country == "country_vietnam":
            raise ValueError(
                "Vietnam isn't clearly associated with any one country currently. See: https://wiki.warthunder.com/collections/operator/country_vietnam"
            )

        raise ValueError(f"Unknown country for operator country tag: {operator_country}")

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
        hangar_blkx_data: dict,
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

            # Ignore "country_invisible" vehicles (these are mostly just drones and nuclear bombers, so not really relevant)
            if tag_data.get("operatorCountry") == "country_invisible":
                logger.info(f"Internal name '{internal_name}' is tagged as 'country_invisible'. Skipping.")
                continue

            # Get the country from the tags/internal name
            try:
                country = self._get_country_from_tags(tag_data)
            except ValueError as e:
                try:
                    country = self._get_country_from_internal_name(internal_name)
                except ValueError as e:
                    try:
                        country = self._get_country_from_hangar(internal_name, hangar_blkx_data)
                    except ValueError as e:
                        try:
                            country = self._get_country_from_fallback(internal_name, tag_data)
                        except ValueError as e:
                            tag_country = next(
                                (key for key in tag_data.get("tags", {}).keys() if key.startswith("country_")), None
                            )
                            logger.error(
                                f"Error extracting country from internal name or tags. Internal name: '{internal_name}', tag country: '{tag_country}', error: {e}"
                            )
                            continue

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
