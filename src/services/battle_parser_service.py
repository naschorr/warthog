import logging

logger = logging.getLogger(__name__)

import re
import traceback
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable, Any

from enums import Country, BattleType
from services.vehicle_service import VehicleService
from models.vehicle_models import Vehicle
from models.battle_models.currency_models import Currency
from models.battle_models import (
    Battle,
    DamageEntry,
    CaptureEntry,
    AwardEntry,
    ActivityEntry,
    TimePlayedEntry,
    SkillBonusEntry,
    DamageSection,
    BattleSummary,
    ResearchUnit,
    ResearchProgress,
    BoosterInfo,
    ScoutingEntry,
    ScoutingDestructionEntry,
    LandingEntry,
)


class SectionDefinition:
    """Definition of a battle section with pattern and handler."""

    def __init__(
        self,
        name: str,
        pattern: str,
        handler_method: str,
        target_attr: Optional[str] = None,
        is_direct_value: bool = False,
    ):
        """
        Args:
            name: Display name for the section (for debugging)
            pattern: Regex pattern to match section name
            handler_method: Method name to call for parsing entries
            target_attr: Attribute path in battle object to store entries
            is_direct_value: Whether to store value directly instead of extending a list
        """
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.handler_method = handler_method
        self.target_attr = target_attr
        self.is_direct_value = is_direct_value


class BattleParserService:
    """
    Service for parsing War Thunder battle data, extracting structured information
    from the clipboard text format.
    """

    # Regex patterns for different sections
    HEADER_PATTERN = re.compile(r"(Victory|Defeat) in the \[(.+?)\] (.+?) mission!")

    # Header format patterns - used to identify section headers
    SECTION_HEADER_FORMATS = [
        re.compile(r"^(.+?)(?:\s+(\d+))?\s+(?:(\d+) SL)?\s*(?:(\d+) RP)?\s*$"),
        re.compile(r"^(.+?)\s+(\d+:\d+)\s+(\d+) RP\s*$"),
    ]

    # Section definitions
    SECTION_DEFINITIONS = [
        SectionDefinition(
            "Destruction Ground",
            r"destruction of ground vehicles",
            "_parse_damage_entries",
            "damage.destruction_ground",
        ),
        SectionDefinition(
            "Destruction Air",
            r"destruction of aircraft",
            "_parse_damage_entries",
            "damage.destruction_air",
        ),
        SectionDefinition(
            "Assistance",
            r"assistance in destroying",
            "_parse_damage_entries",
            "damage.assistance",
        ),
        SectionDefinition(
            "Critical Damage",
            r"critical damage",
            "_parse_damage_entries",
            "damage.critical",
        ),
        SectionDefinition(
            "Damage", r"damage to the enemy", "_parse_damage_entries", "damage.damage"
        ),
        SectionDefinition(
            "Scouting",
            r"scouting of the enemy",
            "_parse_scouting_entries",
            "scouting.scouted",
        ),
        SectionDefinition(
            "Damage by Scouted",
            r"damage taken by scouted enemies",
            "_parse_scouting_entries",
            "scouting.damage_by_scouted",
        ),
        SectionDefinition(
            "Scouted Destruction",
            r"destruction by allies of scouted enemies",
            "_parse_scouting_destruction_entries",
            "scouting.destruction_of_scouted",
        ),
        SectionDefinition(
            "Capture", r"capture of zones", "_parse_capture_entries", "captures"
        ),
        SectionDefinition(
            "Landings", r"landings", "_parse_landing_entries", "landings"
        ),
        SectionDefinition("Awards", r"awards", "_parse_award_entries", "awards"),
        SectionDefinition(
            "Activity Time", r"activity time", "_parse_activity_entries", "activity"
        ),
        SectionDefinition(
            "Time Played", r"time played", "_parse_time_played_entries", "time_played"
        ),
        SectionDefinition(
            "Reward", r"reward for", "_parse_reward", "reward", is_direct_value=True
        ),
        SectionDefinition(
            "Skill Bonus", r"skill bonus", "_parse_skill_bonus_entries", "skill_bonus"
        ),
        SectionDefinition(
            "Researched Unit",
            r"researched unit",
            "_parse_summary",
            "summary.research.research_units",
        ),
        SectionDefinition(
            "Researching Progress",
            r"researching progress",
            "_parse_summary",
            "summary.research.research_progress",
        ),
    ]

    # Damage entry patterns
    DAMAGE_ENTRY_PATTERN = re.compile(
        r"\s*(\d+:\d+)\s+(.+?)\s+(.+?)\s+(.+?)\s+(\d+) mission points\s+(\d+) SL\s+(.+?)$"
    )

    # Scouting entry patterns
    SCOUTING_ENTRY_PATTERN = re.compile(
        r"\s*(\d+:\d+)\s+(.+?)\s+(.+?)\s+(\d+) mission points\s+(\d+) SL\s*$"
    )
    SCOUTING_DESTRUCTION_ENTRY_PATTERN = re.compile(
        r"\s*(\d+:\d+)\s+(.+?)\s+(.+?)\s+(\d+) mission points\s+×\s+(\d+) SL\s+(.+?)$"
    )

    # Capture entry pattern
    CAPTURE_ENTRY_PATTERN = re.compile(
        r"\s*(\d+:\d+)\s+(.+?)\s+(\d+)%\s+(\d+) mission points\s+(\d+) SL\s+(.+?)$"
    )

    # Award entry pattern
    AWARD_ENTRY_PATTERN = re.compile(
        r"\s*(\d+:\d+)?\s+(.+?)\s+(\d+) SL(?:\s+(.+?))?\s*$"
    )

    # Activity time entry pattern
    ACTIVITY_ENTRY_PATTERN = re.compile(r"\s*(.+?)\s+(\d+) SL\s+(.+?)$")

    # Time played entry pattern
    TIME_PLAYED_ENTRY_PATTERN = re.compile(r"\s*(.+?)\s+(\d+)%\s+(\d+:\d+)\s+(.+?)$")

    # Skill bonus entry pattern
    SKILL_BONUS_ENTRY_PATTERN = re.compile(r"\s*(.+?)\s+(I+|IV|V)\s+(\d+) RP\s*$")

    # Summary patterns
    EARNINGS_PATTERN = re.compile(r"Earned: (\d+) SL, (\d+) CRP")
    ACTIVITY_PATTERN = re.compile(r"Activity: (\d+)%")
    DAMAGED_VEHICLES_PATTERN = re.compile(r"Damaged Vehicles: (.+)")
    BACKUP_VEHICLES_SPENT_PATTERN = re.compile(r"Backup vehicles spent: (.+)")
    REPAIR_COST_PATTERN = re.compile(r"Automatic repair of all vehicles: -(\d+) SL")
    AMMO_COST_PATTERN = re.compile(r"Automatic purchasing of ammo and .+?: -(\d+) SL")
    RESEARCHED_UNIT_PATTERN = re.compile(r"Researched unit:")
    RESEARCH_PROGRESS_PATTERN = re.compile(r"(.+?) - (.+?): (\d+ RP)")
    SESSION_PATTERN = re.compile(r"Session: ([a-f0-9]+)")
    TOTAL_PATTERN = re.compile(r"Total: (.+)")

    def __init__(self, vehicle_service: VehicleService):
        self._vehicle_service = vehicle_service
        self.player_vehicle_names: set[str] = set()
        self.enemy_vehicle_names: set[str] = set()

    def parse_battle(
        self,
        text: str,
        *,
        battle_type: BattleType,
        timestamp: Optional[datetime] = None,
    ) -> Optional[Battle]:
        """
        Parse the battle data from clipboard text.

        Args:
            text: The raw text from clipboard

        Returns:
            Battle object if successful, None otherwise
        """
        if not text:
            logger.warning("Empty text provided for parsing")
            return None

        try:
            lines = text.splitlines()

            # Reset used vehicles for this battle
            self.player_vehicle_names = set()
            self.enemy_vehicle_names = set()

            # Parse header (first line)
            mission_type, mission_name, victory = self._parse_header(lines[0])

            # Find session ID
            session = self._find_session(lines)
            if not session:
                logger.error("No session ID found in battle text")
                return None

            # Initialize battle object
            battle = Battle(
                timestamp=timestamp,
                session=session,
                mission_name=mission_name,
                mission_type=mission_type,
                victory=victory,
            )

            # Split text into sections and parse each one
            sections = self._split_into_sections(lines)

            # Process each section
            for section in sections:
                section_name = self._identify_section_header(section)
                if section_name:
                    self._process_section(section_name, section, battle)

            # Parse summary
            battle.summary = self._parse_summary(lines)

            # Get hydrated vehicle data for the player and enemies...
            player_vehicle_data = self._get_player_vehicles()
            enemy_vehicle_data = self._get_enemy_vehicles()

            # ...and process the player's vehicles...
            if player_vehicle_data:
                # Set the player's country based on the first vehicle found (They should all be the same country)
                battle.country = player_vehicle_data[0].country

                # Save the player vehicles in the battle object
                battle.player_vehicles = [
                    vehicle.name for vehicle in player_vehicle_data
                ]

                # Get the maximum battle rating for the player's vehicles
                player_battle_rating = max(
                    [
                        getattr(vehicle.battle_rating, battle_type.value)
                        for vehicle in player_vehicle_data
                    ]
                )
                battle.player_battle_rating = player_battle_rating
            else:
                raise ValueError("No player vehicles found in battle data")

            # ...and process the enemy's vehicles
            if enemy_vehicle_data:
                # Save the enemy vehicles in the battle object
                battle.enemy_vehicles = list(self.enemy_vehicle_names)

                # Get the maximum battle rating for the enemy vehicles
                enemy_battle_rating = max(
                    [
                        getattr(vehicle.battle_rating, battle_type.value)
                        for vehicle in enemy_vehicle_data
                    ]
                )
                battle.enemy_battle_rating = enemy_battle_rating
            else:
                raise ValueError("No enemy vehicles found in battle data")

            return battle

        except Exception as e:
            logger.error(f"Error parsing battle: {e}")
            logger.debug(traceback.format_exc())
            return None

    def _parse_header(self, header_line: str) -> Tuple[str, str, bool]:
        """Parse the battle header line to extract basic info."""
        match = self.HEADER_PATTERN.match(header_line)
        if not match:
            logger.error(f"Could not parse header: {header_line}")
            raise ValueError(f"Invalid battle header format: {header_line}")

        result, mission_type, mission_name = match.groups()
        victory = result.lower() == "victory"

        return mission_type, mission_name, victory

    def _find_session(self, lines: List[str]) -> Optional[str]:
        """Find the session ID in the battle text."""
        for line in reversed(
            lines
        ):  # Search from the end as session is near the bottom
            match = self.SESSION_PATTERN.search(line)
            if match:
                return match.group(1)
        return None

    def _process_section(
        self, section_name: str, lines: List[str], battle: Battle
    ) -> None:
        """Process a specific section of battle text."""
        # Find the section definition that matches this section
        section_def = next(
            (s for s in self.SECTION_DEFINITIONS if s.pattern.search(section_name)),
            None,
        )
        if not section_def:
            logger.warning(f"No section definition found for: {section_name}")
            return

        # Call the appropriate handler method
        handler = getattr(self, section_def.handler_method, None)
        if not handler:
            logger.warning(f"No handler method found for section: {section_def.name}")
            return

        # Process the lines using the handler method
        result = handler(lines)

        # For regular sections with a target attribute
        if section_def.target_attr:
            # Split the attribute path (e.g., "damage.destruction_ground" -> ["damage", "destruction_ground"])
            attr_path = section_def.target_attr.split(".")

            if section_def.is_direct_value:
                # For direct values (e.g. reward), just set the value
                self._set_nested_attr(battle, attr_path, result)
            else:
                # For list values (e.g. damage entries), extend the list
                target = self._get_nested_attr(battle, attr_path)
                if hasattr(target, "extend"):
                    target.extend(result)
                else:
                    logger.warning(
                        f"Cannot add to non-list attribute: {section_def.target_attr}"
                    )

    def _get_nested_attr(self, obj: Any, attr_path: List[str]) -> Any:
        """Get a nested attribute value from an object using a path list."""
        current = obj
        for attr in attr_path:
            current = getattr(current, attr, None)
            if current is None:
                return None
        return current

    def _set_nested_attr(self, obj: Any, attr_path: List[str], value: Any) -> None:
        """Set a nested attribute value on an object using a path list."""
        current = obj
        for attr in attr_path[:-1]:
            current = getattr(current, attr)
        setattr(current, attr_path[-1], value)

    def _parse_damage_entries(self, lines: List[str]) -> List[DamageEntry]:
        """Parse damage-related entries (destruction, assistance, critical, regular)."""
        entries = []

        # Skip the first line (header)
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]
            if len(parts) >= 6:  # Ensure we have enough parts
                # Extract data from parts based on typical format:
                # timestamp, attack_vehicle, ammunition, target_vehicle, mission_points, sl_reward, rp_reward
                timestamp = parts[0].strip()
                attack_vehicle = parts[1].strip()
                ammunition = parts[2].strip()
                target_vehicle = parts[3].strip()

                # Process mission points (format: "X mission points")
                mission_points_match = re.search(r"(\d+)", parts[4].strip())
                if mission_points_match:
                    mission_points = int(mission_points_match.group(1))
                else:
                    logger.warning(
                        f"Could not parse mission points: {parts[4].strip()}"
                    )
                    mission_points = 0

                # Create currency object from extracted currency values
                currency = Currency.from_strings(
                    sl=parts[5].strip(), rp=parts[6].strip()
                )

                # Track the vehicles used in the battle
                self.player_vehicle_names.add(attack_vehicle)
                self.enemy_vehicle_names.add(target_vehicle)

                entry = DamageEntry(
                    timestamp=timestamp,
                    attack_vehicle=attack_vehicle,
                    ammunition=ammunition,
                    target_vehicle=target_vehicle,
                    mission_points=mission_points,
                    currency=currency,
                )
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse damage entry (insufficient parts): {line}"
                )

        return entries

    def _parse_scouting_entries(self, lines: List[str]) -> List[ScoutingEntry]:
        """Parse scouting entries."""
        entries = []

        # Skip the first line (header)
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]
            if len(parts) >= 5:  # Ensure we have enough parts
                # Format: timestamp, vehicle, target_vehicle, mission_points, sl_reward
                timestamp = parts[0].strip()
                scout_vehicle = parts[1].strip()
                target_vehicle = parts[2].strip()

                # Process mission points (format: "X mission points")
                mission_points_match = re.search(r"(\d+)", parts[4].strip())
                if mission_points_match:
                    mission_points = int(mission_points_match.group(1))
                else:
                    logger.warning(
                        f"Could not parse mission points: {parts[4].strip()}"
                    )
                    mission_points = 0

                # Create currency object from SL string
                currency = Currency.from_strings(sl=parts[4].strip())

                # Track the vehicles used/seen in the battle
                self.player_vehicle_names.add(scout_vehicle)
                self.enemy_vehicle_names.add(target_vehicle)

                entry = ScoutingEntry(
                    timestamp=timestamp,
                    scout_vehicle=scout_vehicle,
                    target_vehicle=target_vehicle,
                    mission_points=mission_points,
                    currency=currency,
                )
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse scouting entry (insufficient parts): {line}"
                )

        return entries

    def _parse_scouting_destruction_entries(
        self, lines: List[str]
    ) -> List[ScoutingDestructionEntry]:
        """Parse destruction by allies of scouted enemies entries."""
        entries = []

        # Skip the first line (header)
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]
            if len(parts) >= 6:  # Ensure we have enough parts
                # Format: timestamp, vehicle, target_vehicle, mission_points, sl_reward (with ×), rp_reward
                timestamp = parts[0].strip()
                scout_vehicle = parts[1].strip()
                target_vehicle = parts[2].strip()

                # Process mission points (format: "X mission points")
                mission_points_match = re.search(r"(\d+)", parts[3].strip())
                if mission_points_match:
                    mission_points = int(mission_points_match.group(1))
                else:
                    logger.warning(
                        f"Could not parse mission points: {parts[3].strip()}"
                    )
                    mission_points = 0

                # Address odd formatting where mission points might be followed by "×"
                if "×" in parts[4].strip():
                    del parts[4]

                # Create currency object from extracted currency values
                currency = Currency.from_strings(
                    sl=parts[4].strip(), rp=parts[5].strip() if len(parts) > 5 else ""
                )

                # Track the vehicles used
                self.player_vehicle_names.add(scout_vehicle)
                self.enemy_vehicle_names.add(target_vehicle)

                entry = ScoutingDestructionEntry(
                    timestamp=timestamp,
                    scout_vehicle=scout_vehicle,
                    target_vehicle=target_vehicle,
                    mission_points=mission_points,
                    currency=currency,
                )
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse scouting destruction entry (insufficient parts): {line}"
                )

        return entries

    def _parse_capture_entries(self, lines: List[str]) -> List[CaptureEntry]:
        """Parse capture zone entries."""
        entries = []

        # Skip the first line (header)
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]
            if len(parts) >= 6:  # Ensure we have enough parts
                # Format: timestamp, vehicle, percentage, mission_points, sl_reward, rp_reward
                timestamp = parts[0].strip()
                vehicle = parts[1].strip()

                # Process percentage (format: "X%")
                percentage_match = re.search(r"(\d+)", parts[4].strip())
                if percentage_match:
                    percentage = int(percentage_match.group(1))
                else:
                    logger.warning(f"Could not parse percentage: {parts[2].strip()}")
                    percentage = 0

                # Process mission points (format: "X mission points")
                mission_points_match = re.search(r"(\d+)", parts[4].strip())
                if mission_points_match:
                    mission_points = int(mission_points_match.group(1))
                else:
                    logger.warning(
                        f"Could not parse mission points: {parts[4].strip()}"
                    )
                    mission_points = 0

                # Track the vehicle used
                self.player_vehicle_names.add(vehicle)

                # Create currency object from extracted currency values
                currency = Currency.from_strings(
                    sl=parts[4].strip(), rp=parts[5].strip() if len(parts) > 5 else ""
                )

                entry = CaptureEntry(
                    timestamp=timestamp,
                    vehicle=vehicle,
                    capture_percentage=percentage,
                    mission_points=mission_points,
                    currency=currency,
                )
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse capture entry (insufficient parts): {line}"
                )

        return entries

    def _parse_landing_entries(self, lines: List[str]) -> List[LandingEntry]:
        """Parse aircraft landing entries."""
        entries = []

        # Skip the first line (header)
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]
            if len(parts) >= 3:  # Ensure we have enough parts
                # Format: timestamp, vehicle, rp_reward
                timestamp = parts[0].strip()
                vehicle = parts[1].strip()
                rp_str = parts[2].strip()

                # Track the vehicle used
                self.player_vehicle_names.add(vehicle)

                # Create currency object from RP string
                currency = Currency.from_strings(rp=rp_str)

                entry = LandingEntry(
                    timestamp=timestamp,
                    vehicle=vehicle,
                    currency=currency,
                )
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse landing entry (insufficient parts): {line}"
                )

        return entries

    def _parse_award_entries(self, lines: List[str]) -> List[AwardEntry]:
        """Parse award entries."""
        entries = []

        # Skip the first line (header)
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]

            if len(parts) >= 2:  # Ensure we have enough parts
                # Format: [timestamp], name, sl_reward, [rp_reward]

                # Check if the first part is a timestamp (format: "X:XX")
                if re.match(r"\d+:\d+", parts[0]):
                    timestamp = parts[0].strip()
                    name = parts[1].strip()
                    sl_str = parts[2].strip() if len(parts) > 2 else "0 SL"
                    rp_str = (
                        parts[3].strip() if len(parts) > 3 and "RP" in parts[3] else ""
                    )
                else:
                    timestamp = None
                    name = parts[0].strip()
                    sl_str = parts[1].strip()
                    rp_str = (
                        parts[2].strip() if len(parts) > 2 and "RP" in parts[2] else ""
                    )

                # Create currency object from extracted currency values
                currency = Currency.from_strings(sl=sl_str, rp=rp_str)

                entry = AwardEntry(timestamp=timestamp, name=name, currency=currency)
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse award entry (insufficient parts): {line}"
                )

        return entries

    def _parse_activity_entries(self, lines: List[str]) -> List[ActivityEntry]:
        """Parse activity time entries."""
        entries = []

        # Skip the first line (header)
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]

            if len(parts) >= 3:  # Ensure we have enough parts
                # Format: vehicle, sl_reward, rp_reward
                vehicle = parts[0].strip()

                # Track the vehicle used
                self.player_vehicle_names.add(vehicle)

                # Create currency object from extracted currency values
                currency = Currency.from_strings(
                    sl=parts[1].strip(), rp=parts[2].strip()
                )

                entry = ActivityEntry(vehicle=vehicle, currency=currency)
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse activity entry (insufficient parts): {line}"
                )

        return entries

    def _parse_time_played_entries(self, lines: List[str]) -> List[TimePlayedEntry]:
        """Parse time played entries."""
        entries = []

        # Look for the total time first
        total_time = None
        for i, line in enumerate(lines):
            if i == 0:  # Check the header line
                time_match = re.search(r"(\d+:\d+)", line)
                if time_match:
                    total_time = time_match.group(1)
                break

        # Parse individual vehicle times
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]

            if len(parts) >= 4:  # Ensure we have enough parts
                # Format: vehicle, percentage%, time_str, rp_reward
                vehicle = parts[0].strip()

                # Process percentage (format: "X%")
                percentage_match = re.search(r"(\d+)", parts[1].strip())
                if percentage_match:
                    percentage = int(percentage_match.group(1))
                else:
                    logger.warning(f"Could not parse percentage: {parts[1].strip()}")
                    percentage = 0

                # Process time string (format: "X:XX")
                time_str = parts[2].strip()

                # Track the vehicle used
                self.player_vehicle_names.add(vehicle)

                # Create currency object using from_strings
                currency = Currency.from_strings(rp=parts[3].strip())

                entry = TimePlayedEntry(
                    vehicle=vehicle,
                    activity_percentage=percentage,
                    time_str=time_str,
                    currency=currency,
                )
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse time played entry (insufficient parts): {line}"
                )

        return entries

    def _parse_skill_bonus_entries(self, lines: List[str]) -> List[SkillBonusEntry]:
        """Parse skill bonus entries."""
        entries = []

        # Skip the header line
        for line in lines[1:]:
            if not line.strip():
                continue

            # Split by multiple whitespace (4+ spaces)
            parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]

            if len(parts) >= 3:  # Ensure we have enough parts
                # Format: vehicle, tier (Roman numeral), rp_value
                vehicle = parts[0].strip()
                tier = parts[1].strip()

                # Track the vehicle used
                self.player_vehicle_names.add(vehicle)

                # Create currency object from extracted currency values
                currency = Currency.from_strings(rp=parts[2].strip())

                entry = SkillBonusEntry(vehicle=vehicle, tier=tier, currency=currency)
                entries.append(entry)
            else:
                logger.warning(
                    f"Could not parse skill bonus entry (insufficient parts): {line}"
                )

        return entries

    def _parse_reward(self, lines: List[str]) -> Currency:
        """Parse the reward section to extract currency values."""
        currency = Currency()

        line = lines[0].strip()
        parts = [part for part in re.split(r"\s{4,}", line.strip()) if part]

        if len(parts) >= 2:
            title = parts[0].strip()
            sl = parts[1].strip()

            currency = Currency.from_strings(sl=sl)

        return currency

    def _parse_summary(self, lines: List[str]) -> BattleSummary:
        """Parse the battle summary from the text."""
        summary = BattleSummary()

        # Track if we're in the researched units section
        in_researched_units = False
        # Track if we're in the used items section
        in_used_items = False

        # We need to parse these sections from the bottom portion of the text
        for index, line in enumerate(lines):
            # Earnings
            earnings_match = self.EARNINGS_PATTERN.search(line)
            if earnings_match:
                summary.earnings.silver_lions = int(earnings_match.group(1))
                summary.earnings.convertible_research_points = int(
                    earnings_match.group(2)
                )

            # Activity percentage
            activity_match = self.ACTIVITY_PATTERN.search(line)
            if activity_match:
                summary.activity_percentage = float(int(activity_match.group(1)) / 100)

            # Damaged vehicles
            damaged_match = self.DAMAGED_VEHICLES_PATTERN.search(line)
            if damaged_match:
                vehicles = [v.strip() for v in damaged_match.group(1).split(",")]
                self.player_vehicle_names.update(vehicles)
                summary.damaged_vehicles = vehicles

            # Backup vehicles spent
            backup_match = self.BACKUP_VEHICLES_SPENT_PATTERN.search(line)
            if backup_match:
                vehicles = [v.strip() for v in backup_match.group(1).split(",")]
                self.player_vehicle_names.update(vehicles)
                summary.backup_vehicles_spent = vehicles

            # Repair cost
            repair_match = self.REPAIR_COST_PATTERN.search(line)
            if repair_match:
                summary.repair_cost = int(repair_match.group(1))

            # Ammo cost
            ammo_match = self.AMMO_COST_PATTERN.search(line)
            if ammo_match:
                summary.ammo_cost = int(ammo_match.group(1))

            # Researched units section
            researched_match = self.RESEARCHED_UNIT_PATTERN.search(line)
            if researched_match:
                in_researched_units = True
                continue

            # If we're in the researched units section, parse unit lines
            if in_researched_units:
                # Check if this line contains a unit and RP value
                if ":" in line and "RP" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        unit_name = parts[0].strip()
                        rp_value = parts[1].strip()
                        research_unit = ResearchUnit(
                            unit=unit_name,
                            currency=Currency.from_strings(rp=rp_value),
                        )
                        summary.research.research_units.append(research_unit)
                else:
                    # Stop parsing researched units if we hit a line that doesn't match the format
                    in_researched_units = False

            # Used items section
            if line.strip() == "Used items:":
                in_used_items = True
                in_researched_units = False  # Exit researched units section
                continue

            # If we're in the used items section, parse booster lines
            if in_used_items:
                line_stripped = line.strip()

                # Check if this line starts a booster category (SL or RP)
                if line_stripped.startswith("Active boosters"):
                    booster_category = (
                        "SL"
                        if "SL:" in line_stripped
                        else "RP" if "RP:" in line_stripped else None
                    )
                    if booster_category:
                        # Look ahead to parse boosters in this category
                        j = index + 1

                        while j < len(lines) and not lines[j].strip().startswith(
                            "Active boosters"
                        ):
                            booster_line = lines[j].strip()

                            # Skip empty lines and "Common:" summary lines
                            if not booster_line or booster_line.startswith("Common:"):
                                j += 1
                                continue

                            # Parse booster lines starting with "*"
                            if booster_line.startswith("*"):
                                # Extract target and percentage from lines like:
                                # "* Personal booster: +15%RP" or "* Public booster: +10%RP"
                                target = None
                                percentage = None

                                if "Personal booster" in booster_line:
                                    target = "Personal"
                                elif "Public booster" in booster_line:
                                    target = "Public"

                                # Try to extract percentage from the same line
                                percentage_match = re.search(r"\+(\d+)%", booster_line)
                                if percentage_match:
                                    percentage = int(percentage_match.group(1)) / 100.0

                                # If we found a target but no percentage, look for it in the next line
                                if target and not percentage:
                                    # Look ahead for the percentage in the next line
                                    next_j = j + 1
                                    if next_j < len(lines):
                                        next_line = lines[next_j].strip()
                                        if (
                                            next_line.startswith("+")
                                            and booster_category in next_line
                                        ):
                                            percentage_match = re.search(
                                                r"\+(\d+)%", next_line
                                            )
                                            if percentage_match:
                                                percentage = (
                                                    int(percentage_match.group(1))
                                                    / 100.0
                                                )

                                # Create booster if we have both target and percentage
                                if target and percentage:
                                    booster = BoosterInfo(
                                        type=booster_category,
                                        percentage=percentage,
                                        target=target,
                                    )
                                    summary.boosters.append(booster)

                            j += 1

                # Exit used items section if we hit a different section
                elif (
                    line_stripped
                    and not line_stripped.startswith("Active boosters")
                    and not line_stripped.startswith("Common:")
                    and not line_stripped.startswith("*")
                    and not "gives" in line_stripped
                    and not line_stripped.startswith("+")
                ):
                    in_used_items = False

            # Research progress
            progress_match = self.RESEARCH_PROGRESS_PATTERN.search(line)
            if progress_match:
                vehicle, item, rp = progress_match.groups()
                progress = ResearchProgress(
                    item=f"{vehicle.strip()} - {item.strip()}",
                    currency=Currency.from_strings(rp=rp.strip() if rp else ""),
                )
                summary.research.research_progress.append(progress)

            # Total values from the last line
            total_match = self.TOTAL_PATTERN.search(line)
            if total_match:
                sl, crp, rp = total_match.group(1).split(",")
                summary.total_currency = Currency.from_strings(
                    sl=sl.strip(), crp=crp.strip(), rp=rp.strip()
                )

        return summary

    def _split_into_sections(self, lines: List[str]) -> List[List[str]]:
        """
        Split the battle text into sections using empty lines as delimiters.

        Returns:
            List of sections, where each section is a list of lines
        """
        sections = []
        current_section = []

        # Skip the header line since it's processed separately
        for line in lines[1:]:
            if not line.strip():
                # Empty line denotes section boundary
                if current_section:
                    sections.append(current_section)
                    current_section = []
            else:
                current_section.append(line)

        # Add the last section if it exists
        if current_section:
            sections.append(current_section)

        return sections

    def _identify_section_header(self, section_lines: List[str]) -> Optional[str]:
        """
        Identify the section name from the first line of a section.

        Args:
            section_lines: Lines of a section

        Returns:
            Section name if identified, None otherwise
        """
        if not section_lines:
            return None

        # Use the header format patterns to extract the section name
        first_line = section_lines[0]
        for pattern in self.SECTION_HEADER_FORMATS:
            match = pattern.match(first_line)
            if match:
                return match.group(1).strip()

        return None

    def _get_player_vehicles(self) -> list[Vehicle]:
        """Get the hydrated player vehicles from the processed member data."""

        # Get hydrated vehicle data
        player_vehicle_data: list[Vehicle] = []
        for vehicle_name in self.player_vehicle_names:
            # Attempt to find the vehicle by name
            found_vehicles = self._vehicle_service.get_vehicles_by_name(
                vehicle_name, exact_match=True
            )
            if found_vehicles:
                player_vehicle_data.extend(found_vehicles)
            else:
                logger.warning(f"Vehicle not found: {vehicle_name}")
        if not player_vehicle_data:
            raise ValueError("No player vehicles found in battle data")

        # Count the number of vehicles returned per country, and assume the most commonly used country is the player's country
        vehicle_counter = Counter([vehicle for vehicle in player_vehicle_data])
        country = vehicle_counter.most_common(1)[0][0].country

        # Filter vehicles by the player's country
        player_vehicle_data = [
            vehicle for vehicle in player_vehicle_data if vehicle.country == country
        ]

        # Sanity check that we have the expected number of player vehicles
        if len(player_vehicle_data) != len(self.player_vehicle_names):
            raise ValueError(
                f"Mismatch in player vehicles: {len(player_vehicle_data)} found, "
                f"{len(self.player_vehicle_names)} expected"
            )

        return player_vehicle_data

    def _get_enemy_vehicles(self) -> list[Vehicle]:
        """Get the hydrated enemy vehicles from the processed member data."""

        # Get hydrated vehicle data
        enemy_vehicle_data: list[Vehicle] = []
        for vehicle_name in self.enemy_vehicle_names:
            # Attempt to find the vehicle by name
            found_vehicles = self._vehicle_service.get_vehicles_by_name(
                vehicle_name, exact_match=True
            )
            if found_vehicles:
                enemy_vehicle_data.extend(found_vehicles)
            else:
                logger.warning(f"Enemy vehicle not found: {vehicle_name}")

        return enemy_vehicle_data
