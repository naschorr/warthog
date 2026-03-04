import logging

logger = logging.getLogger(__name__)

import struct
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from pathlib import Path

from src.common.enums import BattleType, PlatformType, Country
from src.common.services.vehicle_service import VehicleService
from src.replay_data_grabber.models import Replay, Player
from src.replay_data_grabber.models.deaths import Deaths
from src.replay_data_grabber.models.death_detail import DeathDetail
from src.replay_data_grabber.models.kill_detail import KillDetail
from src.replay_data_grabber.services.replay_stream_decoder_service import ReplayStreamDecoderService
from src.replay_data_grabber.services.wt_ext_cli_client_service import WtExtCliClientService


class ReplayParserService:
    """
    Service for parsing War Thunder replay files (.wrpl).

    This service can extract metadata and player data from War Thunder replay files.
    For full results parsing, it requires the wt_ext_cli tool.
    """

    MAGIC = b"\xe5\xac\x00\x10"

    def __init__(self, *, vehicle_service: VehicleService, wt_ext_cli_client_service: WtExtCliClientService):
        """
        Initialize the replay parser service.
        """
        self._vehicle_service = vehicle_service
        self._wt_ext_cli_client_service = wt_ext_cli_client_service
        self._replay_stream_decoder = ReplayStreamDecoderService(vehicle_service)

    def parse_replay_data(self, replay_data: bytes) -> Replay:
        """
        Parse War Thunder replay data from bytes.

        Args:
            data: Raw bytes from a .wrpl file

        Returns:
            Replay object containing parsed replay information

        Raises:
            ValueError: If the data is not a valid replay file
        """
        ## TODO: The replay object should be constructed after the parts have been processed, and it should have stricter typing
        replay = Replay()

        # Check magic number
        if replay_data[:4] != self.MAGIC:
            raise ValueError("Invalid magic number, not a valid War Thunder replay file")

        offset = 4

        # Read version
        replay.version = struct.unpack("<I", replay_data[offset : offset + 4])[0]
        offset += 4
        logger.debug(f"Replay version: {replay.version}")

        # Read level (128 bytes)
        replay.level = self._read_string(replay_data, offset, 128)
        replay.level = replay.level.replace("levels/", "").replace(".bin", "")
        offset += 128

        # Read level settings (260 bytes)
        replay.level_settings = self._read_string(replay_data, offset, 260)
        offset += 260

        # Read battle type (128 bytes)
        _battle_type_alt = self._read_string(replay_data, offset, 128)
        offset += 128

        # Read environment (128 bytes)
        replay.environment = self._read_string(replay_data, offset, 128)
        offset += 128

        # Read visibility (32 bytes)
        replay.visibility = self._read_string(replay_data, offset, 32)
        offset += 32

        # Read results offset
        results_offset = struct.unpack("<I", replay_data[offset : offset + 4])[0]
        offset += 4

        # Read difficulty
        difficulty_byte = replay_data[offset]
        difficulty_value = int(difficulty_byte & 0x0F)
        if difficulty_value == 0:
            replay.battle_type = BattleType.ARCADE
        elif difficulty_value == 5:
            replay.battle_type = BattleType.REALISTIC
        elif difficulty_value == 10:
            replay.battle_type = BattleType.SIMULATION
        else:
            replay.battle_type = BattleType.UNKNOWN
        offset += 1

        # Skip 35 bytes
        offset += 35

        # Read session type
        replay.session_type = replay_data[offset]
        offset += 1

        # Skip 7 bytes
        offset += 7

        # Read session ID (as 64-bit unsigned int, convert to hex)
        session_id_int = struct.unpack("<Q", replay_data[offset : offset + 8])[0]
        replay.session_id = format(session_id_int, "x")
        offset += 8

        # Skip 4 bytes
        offset += 4

        # Read set size
        _set_size = struct.unpack("<I", replay_data[offset : offset + 4])[0]
        offset += 4

        # Skip 32 bytes
        offset += 32

        # Read loc name (128 bytes)
        replay.loc_name = self._read_string(replay_data, offset, 128)
        offset += 128

        # Read start time, time limit, score limit
        start_time = struct.unpack("<I", replay_data[offset : offset + 4])[0]
        replay.start_time = datetime.fromtimestamp(start_time)
        offset += 4
        replay.time_limit_minutes = struct.unpack("<I", replay_data[offset : offset + 4])[0]
        offset += 4
        replay.score_limit = struct.unpack("<I", replay_data[offset : offset + 4])[0]
        offset += 4

        # Skip 48 bytes
        offset += 48

        # Read battle class (128 bytes)
        replay.battle_class = self._read_string(replay_data, offset, 128)
        offset += 128

        # Read battle kill streak (128 bytes)
        replay.battle_kill_streak = self._read_string(replay_data, offset, 128)
        offset += 128

        logger.info(f"Parsed replay header: {replay.session_id} - {replay.level} ({replay.battle_type})")

        # Parse results if we have wt_ext_cli
        results = {}
        if results_offset > 0:
            try:
                results = self._wt_ext_cli_client_service.unpack_raw_blk(replay_data[results_offset:])
            except Exception as e:
                logger.error(f"Error unpacking results: {e}")
        else:
            logger.debug("No results data available in replay file")
        self._parse_results(replay, results)

        # Decode rec_data stream for per-vehicle kills/deaths and awards.
        # Players are already built by _parse_results; we match them by slot index.
        # Pass authoritative BLK death counts and team assignments so the decoder
        # can cap EID attribution, enforce cross-team constraints, and fill gaps
        # via timeline inference without overcounting.
        slot_deaths = {i: p.deaths.total for i, p in enumerate(replay.players)}
        slot_teams = {i: p.team for i, p in enumerate(replay.players) if p.team is not None}
        try:
            stream_result = self._replay_stream_decoder.decode_from_raw_replay(
                replay_data, slot_deaths=slot_deaths, slot_teams=slot_teams
            )
            self._apply_stream_result(replay, stream_result)
        except Exception as exc:
            logger.warning(f"Stream decode failed, skipping vehicle-level stats: {exc}")

        # Build the author player object
        author_user_id = results.get("authorUserId", "")
        replay.author = next((player for player in replay.players if player.user_id == author_user_id))

        return replay

    def parse_replay_file(self, file_path: Path) -> Replay:
        """
        Parse a War Thunder replay file.

        Args:
            file_path: Path to the .wrpl replay file

        Returns:
            Replay object containing parsed replay information

        Raises:
            FileNotFoundError: If the replay file doesn't exist
            ValueError: If the file is not a valid replay file
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Replay file not found: {file_path}")

        logger.info(f"Parsing replay file: {file_path}")

        try:
            with open(file_path, "rb") as f:
                data = f.read()
            replay = self.parse_replay_data(data)

            # Normal replays are prepended with a #, but saved ones aren't?
            replay_timestamp = file_path.stem
            if replay_timestamp.startswith("#"):
                replay_timestamp = replay_timestamp[1:]

            replay.end_time = datetime.strptime(replay_timestamp, "%Y.%m.%d %H.%M.%S")
            return replay
        except Exception as e:
            logger.error(f"Error parsing replay file {file_path}: {e}")
            raise

    def _read_string(self, data: bytes, offset: int, length: int) -> str:
        """Read a null-terminated string from the data."""
        string_data = data[offset : offset + length]
        null_index = string_data.find(b"\x00")
        if null_index != -1:
            string_data = string_data[:null_index]
        return string_data.decode("utf-8", errors="ignore")

    def _parse_results(self, replay: Replay, results: dict[str, Any]) -> None:
        """
        Parse the results JSON data and populate the replay object.

        Args:
            replay: Replay object to populate (in place)
            results: Parsed JSON results from wt_ext_cli
        """
        replay.status = results.get("status", "left")
        replay.time_played = results.get("timePlayed", 0.0)
        players_array = results.get("player", [])
        ui_scripts_data = results.get("uiScriptsData", {})
        players_info = ui_scripts_data.get("playersInfo", {})

        for player_data in players_array:
            user_id = str(player_data.get("userId", ""))

            # Find matching player info
            player_info = None
            for info_key, info_value in players_info.items():
                if str(info_value.get("id", "")) == user_id:
                    player_info = info_value
                    break

            if player_info:
                player = self._create_player_from_json(player_info, player_data, replay.battle_type, replay.start_time)
                replay.players.append(player)
            else:
                logger.warning(f"No player info found for user ID: {user_id}")

        # Set the replay battle rating to the highest player battle rating
        for player in replay.players:
            if player.battle_rating and player.battle_rating > replay.battle_rating:
                replay.battle_rating = player.battle_rating

    def _apply_stream_result(self, replay: Replay, stream_result) -> None:
        """
        Merge StreamDecodeResult data into the already-built Player objects.

        The stream decoder keys data by 0-indexed slot derived from entity names:
          t1_playerNN_0 -> slot NN-1  (slots  0-15)
          t2_playerNN_0 -> slot NN-1+16  (slots 16-31)

        Despite the t1/t2 prefix, these groups do NOT correspond to the JSON
        `team` field (1 or 2).  The slot is simply the player's 0-indexed
        position in the results player array (players_array from wt_ext_cli),
        regardless of team.  players_array order is preserved in replay.players,
        so the correct mapping is global insertion order.
        """
        from src.replay_data_grabber.services.replay_stream_decoder_service import StreamDecodeResult

        if not isinstance(stream_result, StreamDecodeResult):
            return

        # Build slot -> Player map using global position in replay.players.
        # Position 0 = slot 0, position 1 = slot 1, ..., position 31 = slot 31.
        slot_map: dict[int, "Player"] = {}
        for i, player in enumerate(replay.players):
            player.slot = i
            slot_map[i] = player

        # Apply vehicle_kills
        for slot, veh_counts in stream_result.vehicle_kills.items():
            player = slot_map.get(slot)
            if player is None:
                logger.debug(f"Stream: no player at slot {slot} for vehicle_kills")
                continue
            for veh, count in veh_counts.items():
                player.vehicle_kills[veh] = player.vehicle_kills.get(veh, 0) + count

        # Apply vehicle_deaths (best-effort)
        for slot, veh_counts in stream_result.vehicle_deaths.items():
            player = slot_map.get(slot)
            if player is None:
                logger.debug(f"Stream: no player at slot {slot} for vehicle_deaths")
                continue
            for veh, count in veh_counts.items():
                player.vehicle_deaths[veh] = player.vehicle_deaths.get(veh, 0) + count

        # Apply awards
        for slot, award_list in stream_result.awards.items():
            player = slot_map.get(slot)
            if player is None:
                logger.debug(f"Stream: no player at slot {slot} for awards")
                continue
            player.awards.extend(award_list)

        # Apply vehicle timeline: supplement lineup with vehicles seen in the stream
        # but absent from the BLK lineup (e.g. aircraft that share no tankModels/ prefix).
        # Death inference and capping is handled inside the stream decoder using the
        # slot_deaths map passed at decode time.
        for slot, timeline in stream_result.slot_vehicle_timeline.items():
            player = slot_map.get(slot)
            if player is None:
                continue
            seen: set[str] = set()
            for _offset, veh in timeline:
                if veh not in seen:
                    seen.add(veh)
                    if veh not in player.lineup:
                        player.lineup.append(veh)

        # Apply per-event kill/death detail records
        _TICK_DURATION_S = 0.1  # ~10 Hz simulation tick rate
        for detail in stream_result.kill_details:
            killer_player = slot_map.get(detail.killer_slot)
            victim_player = slot_map.get(detail.victim_slot) if detail.victim_slot is not None else None
            victim_user_id = victim_player.user_id if victim_player is not None else None
            killer_user_id = killer_player.user_id if killer_player is not None else None

            time_utc = (
                replay.start_time + timedelta(seconds=detail.tick_idx * _TICK_DURATION_S)
                if replay.start_time is not None
                else None
            )

            # Append KillDetail for every kill event where the killer is known;
            # victim fields may be None when the victim left no EID trace in the stream.
            if killer_player is not None:
                killer_player.kills.vehicles.append(
                    KillDetail(
                        killer_vehicle=detail.killer_vehicle,
                        killer_user_id=killer_player.user_id,
                        killer_username=killer_player.username,
                        killer_slot=detail.killer_slot,
                        victim_vehicle=detail.victim_vehicle,
                        victim_user_id=victim_user_id,
                        victim_username=victim_player.username if victim_player is not None else None,
                        victim_slot=detail.victim_slot,
                        time_utc=time_utc,
                    )
                )

            # Only append DeathDetail when victim vehicle + killer user_id are both resolved
            if victim_player is not None and detail.victim_vehicle is not None and killer_user_id is not None:
                victim_player.deaths.vehicles.append(
                    DeathDetail(
                        victim_vehicle=detail.victim_vehicle,
                        victim_user_id=victim_player.user_id,
                        victim_username=victim_player.username,
                        victim_slot=detail.victim_slot,
                        killer_vehicle=detail.killer_vehicle,
                        killer_user_id=killer_user_id,
                        killer_username=killer_player.username if killer_player is not None else None,
                        killer_slot=detail.killer_slot,
                        time_utc=time_utc,
                    )
                )

        logger.info(
            f"Stream stats applied: "
            f"{sum(len(v) for v in stream_result.vehicle_kills.values())} vehicle-kill entries, "
            f"{sum(len(v) for v in stream_result.vehicle_deaths.values())} vehicle-death entries, "
            f"{sum(len(v) for v in stream_result.awards.values())} award entries "
            f"across {len(slot_map)} players"
        )

    def _get_player_battle_rating(
        self, lineup: list[str], battle_type: BattleType, *, battle_datetime: Optional[datetime] = None
    ) -> float:
        """
        Get the battle rating for a player's vehicle lineup.
        """
        battle_rating = self._get_transformed_player_battle_rating(
            max, lineup, battle_type, battle_datetime=battle_datetime
        )
        if battle_rating is not None:
            return battle_rating

        raise ValueError(f"Unable to determine battle rating for lineup: {lineup} and battle_type: {battle_type}")

    def _get_player_min_battle_rating(
        self, lineup: list[str], battle_type: BattleType, *, battle_datetime: Optional[datetime] = None
    ) -> float:
        """
        Get the minimum battle rating for a player's vehicle lineup.
        """
        battle_rating = self._get_transformed_player_battle_rating(
            min, lineup, battle_type, battle_datetime=battle_datetime
        )
        if battle_rating is not None:
            return battle_rating

        raise ValueError(
            f"Unable to determine minimum battle rating for lineup: {lineup} and battle_type: {battle_type}"
        )

    def _get_player_mean_battle_rating(
        self, lineup: list[str], battle_type: BattleType, *, battle_datetime: Optional[datetime] = None
    ) -> float:
        """
        Get the mean battle rating for a player's vehicle lineup.
        """

        def compute_battle_rating_mean(battle_ratings: list[float]) -> float:
            return round(sum(battle_ratings) / len(battle_ratings), 2)

        battle_rating = self._get_transformed_player_battle_rating(
            compute_battle_rating_mean, lineup, battle_type, battle_datetime=battle_datetime
        )
        if battle_rating is not None:
            return battle_rating

        raise ValueError(f"Unable to determine mean battle rating for lineup: {lineup} and battle_type: {battle_type}")

    def _get_transformed_player_battle_rating(
        self,
        transform_func: Callable,
        lineup: list[str],
        battle_type: BattleType,
        *,
        battle_datetime: Optional[datetime] = None,
    ) -> float:
        """
        Get the battle rating for a player's vehicle lineup.
        """
        vehicles = []
        for vehicle_name in lineup:
            vehicle = self._vehicle_service.get_vehicles_by_internal_name(vehicle_name, search_datetime=battle_datetime)
            if vehicle:
                vehicles.append(vehicle)

        battle_ratings = []
        for vehicle in vehicles:
            if battle_type == BattleType.ARCADE:
                battle_ratings.append(vehicle.battle_rating.arcade)
            elif battle_type == BattleType.REALISTIC:
                battle_ratings.append(vehicle.battle_rating.realistic)
            elif battle_type == BattleType.SIMULATION:
                battle_ratings.append(vehicle.battle_rating.simulation)
            else:
                raise ValueError(f"Unknown battle type: {battle_type}")

        battle_rating = transform_func(battle_ratings)
        return battle_rating

    def _create_player_from_json(
        self,
        player_info: dict[str, Any],
        player_data: dict[str, Any],
        battle_type: BattleType,
        start_time: Optional[datetime] = None,
    ) -> Player:
        """Create a Player object from JSON data."""
        player = Player()

        # Player identity fields
        player.user_id = str(player_info.get("id", ""))
        player.squadron_id = str(player_info.get("clanId", ""))
        player.squadron_tag = player_info.get("clanTag", "")

        # Clean up username and platform
        username = player_info.get("name", "")
        platform = player_info.get("platform", "")
        player.platform = platform
        if "xbox" in platform.lower():
            player.username = username.split("@")[0]
            player.platform_type = PlatformType.XBOXLIVE
        elif "ps" in platform.lower():
            player.username = username.split("@")[0]
            player.platform_type = PlatformType.PSN
        elif "win" in platform.lower():
            player.username = username.split("@")[0]
            player.platform_type = PlatformType.PC
        elif "mac" in platform.lower():
            player.username = username.split("@")[0]
            player.platform_type = PlatformType.PC
        elif "linux" in platform.lower():
            player.username = username.split("@")[0]
            player.platform_type = PlatformType.PC
        elif "pc" in platform.lower():
            player.username = username.split("@")[0]
            player.platform_type = PlatformType.PC
        else:
            raise ValueError(f"Unknown platform type: {platform}")

        # Clean up squadron data
        if player.squadron_id == "-1":
            player.squadron_id = None
        if not player.squadron_tag:
            player.squadron_tag = None

        # Set the country
        player.country = Country.get_country_by_name(player_info.get("country", ""))

        # Vehicle lineup
        crafts = player_info.get("crafts", {})
        player.lineup = list(crafts.values())
        player.is_premium = self._vehicle_service.is_vehicle_premium(player.lineup, search_datetime=start_time)

        # Replay metadata
        player.team = player_data.get("team")
        player.squad = player_data.get("squadId")
        player.auto_squad = bool(player_data.get("autoSquad", 1))
        player.tier = player_info.get("tier")
        player.rank = player_info.get("rank")
        player.m_rank = player_info.get("mrank")
        player.wait_time = player_info.get("wait_time", 0.0)
        player.battle_rating = self._get_player_battle_rating(player.lineup, battle_type, battle_datetime=start_time)
        player.min_battle_rating = self._get_player_min_battle_rating(
            player.lineup, battle_type, battle_datetime=start_time
        )
        player.mean_battle_rating = self._get_player_mean_battle_rating(
            player.lineup, battle_type, battle_datetime=start_time
        )

        # Kill statistics
        player.kills.air = player_data.get("kills", 0)
        player.kills.ground = player_data.get("groundKills", 0)
        player.kills.naval = player_data.get("navalKills", 0)
        player.kills.team = player_data.get("teamKills", 0)
        player.kills.ai_air = player_data.get("aiKills", 0)
        player.kills.ai_ground = player_data.get("aiGroundKills", 0)
        player.kills.ai_naval = player_data.get("aiNavalKills", 0)

        player.assists = player_data.get("assists", 0)
        player.deaths = Deaths(total=player_data.get("deaths", 0))
        player.capture_zone = player_data.get("captureZone", 0)
        player.damage_zone = player_data.get("damageZone", 0)
        player.score = player_data.get("score", 0)
        player.award_damage = player_data.get("awardDamage", 0)
        player.missile_evades = player_data.get("missileEvades", 0)

        return player
