"""
War Thunder replay rec_data stream decoder service.

Parses the compressed binary rec_data stream embedded in .wrpl files to extract:
  - Per-vehicle kill counts per player (vehicle_kills)
  - Per-vehicle death counts per player (vehicle_deaths) — best-effort, partial coverage
  - Award names received per player (awards)

## Event structures (all multi-byte integers are little-endian)

### Kill event  (marker: 02 58 58 f0)
  [02 58 58 f0][total_len u8][00 fe 3f]
  [slot u32]               killer's 0-indexed slot (0-31)
  [vehicle_name_length u8] length of killer vehicle name
  [vehicle_name bytes]     killer vehicle internal name (ASCII)
  [victim_entity_id u16]   victim entity ID
  [killer_entity_id u16]   killer entity ID
  [FF FF FF FF]
  [3-byte suffix]

### Award event  (marker: 02 58 78 f0)
  [02 58 78 f0][total_length u8][00][3e]
  [slot u32]               recipient's 0-indexed slot
  [name_length u8]         length of award name
  [award_name bytes]       award internal identifier (ASCII)
  [padding + tail]

### Late-spawn/respawn event  (marker: 02 58 56 f0)  — sparse, ~6 per replay
  [02 58 56 f0][total_length u16][7e]
  [entity_id u16]          entity ID assigned to this vehicle spawn
  [slot u32]               player's 0-indexed slot
  [name_length u8]         length of vehicle name
  [vehicle_name bytes]     vehicle internal name (ASCII)
  [FF FF 01 03 70 ...]
  These fire on mid-game respawns / vehicle switches, NOT for initial spawns.

### Vehicle activation event  (two variants, no fixed 4-byte marker)
  Ground vehicles:
    [length_byte][tankModels/][vehicle_name][0x0d][entity_name][...]
    length_byte covers the full 'tankModels/vehicle_name' string.
  Aircraft / helicopters / naval:
    [length_byte][vehicle_name][0x0d][entity_name][...]
    No path prefix; length_byte covers only the bare vehicle name.
  entity_name encodes the player slot: t1_playerNN_0 -> slot NN-1
                                        t2_playerNN_0 -> slot NN+15
  ~59+ per replay (ground) + additional for non-ground spawns.  No entity ID.
  Records every vehicle activation / switch for all vehicle classes.
  This is the comprehensive source for the slot->vehicle timeline.

## Death attribution strategy
  1. killer_entity_id lookup:  victim entity ID appears as killer entity ID in another kill event.
  2. late_spawn:               victim entity ID appears in a 02 58 56 f0 event -> slot + vehicle directly.
  3. Timeline-based inference: per-slot vehicle-switch timeline (from tankModels events) attributes
                               remaining deaths by matching consecutive vehicle transitions; a per-
                               vehicle credit counter prevents double-counting EID-resolved deaths.
  4. Kill-event supplement:    slots with zero tankModels events but that appear as killers get a
                               synthetic timeline seeded from their kill-event (slot, vehicle, offset)
                               pairs.
  5. Physics-gap inference:    for victims with no EID history, index 025873f0 physics events
                               and use tick-frame boundaries (02582df0, ~10 Hz) to identify the
                               current entity incarnation: the first physics event after a gap of
                               >= 10 ticks (~1 s) in the EID's stream marks a new spawn.  The
                               tankModels event immediately preceding that spawn point (within
                               500 ticks / ~50 s) supplies slot + vehicle.  Accepted only when
                               no other tankModels event fired in the window and the attributed
                               slot differs from the killer's slot.
  6. Unresolvable (~0-3/replay): players who died in their initial vehicle without ever killing,
                               respawning, or producing an unambiguous tankModels activation.
                               The stream contains no vehicle identity data for them.

Stream exploration (02 58 37 f0, 02 58 73 f0, 02 58 2d f0) confirmed no undiscovered event type
gives (entity_id, slot, vehicle) for initial spawns.  The kill event (02 58 58 f0) contains the
KILLER's slot + vehicle + victim EID, but not the victim's slot or vehicle.

## Vehicle timeline (slot_vehicle_timeline)
  Derived from vehicle activation events (both strategies).  Maps each slot to an ordered
  list of (stream_offset, vehicle_name) pairs recording every vehicle the player activated,
  including ground vehicles, aircraft, helicopters, and naval vessels.
"""

import bisect
import logging
import struct
import zlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from src.common.services.vehicle_service import VehicleService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Game-simulation tick frame delimiter.  Every structured event (kill, award,
# late-spawn, physics) falls within a tick frame.  Each tick ≈ 100 ms at ~10 Hz.
_TICK_MARKER = bytes([0x02, 0x58, 0x2D, 0xF0])
_TICK_EVENT_SIZE: int = 22  # confirmed: 22 bytes fixed, start-to-start min gap
_KILL_MARKER = bytes([0x02, 0x58, 0x58, 0xF0])
_AWARD_MARKER = bytes([0x02, 0x58, 0x78, 0xF0])
_LATE_SPAWN_MARKER = bytes([0x02, 0x58, 0x56, 0xF0])
_PHYSICS_73_MARKER = bytes([0x02, 0x58, 0x73, 0xF0])
# Entity interaction event: pairs two EIDs (e.g. proximity, hit).
# Structure: [02 58 37 f0] [07 00 06] [eid_A u16 LE] [eid_B u16 LE] [6c ...]
_INTERACTION_37_MARKER = bytes([0x02, 0x58, 0x37, 0xF0])
_TANKMODELS_PREFIX = b"tankModels/"

# Absolute maximum sane slot index (32-player lobbies have slots 0-31)
_MAX_SLOT = 63

# Physics-gap spawn inference tuning (tick-based; 1 tick ≈ 100 ms at ~10 Hz)
# A gap of this many ticks between consecutive physics73 events for the same EID
# signals a death / EID-reassignment boundary (entity was absent for ≥1 second).
_PHYSICS_INCARNATION_TICKS: int = 10
# The tankModels event immediately before the inferred spawn must be within this
# many ticks of the first new physics event (vehicle activated then started moving).
_PHYSICS_TM_MAX_TICKS: int = 250  # ≈ 25 s; TM event must be close to the physics gap
# Maximum gap (in ticks) between the last physics73 event before the kill and the
# kill event itself.  If the gap exceeds this threshold the entity must have died
# after the identified spawn incarnation ended and the EID was subsequently reused;
# the physics-derived attribution would be stale and is discarded.
_PHYSICS_STALE_TICKS: int = 500  # ≈ 50 s; generous upper bound for activity silence

# Minimum number of physics73 events required for an EID before it is considered a
# reliable physics anchor.  The u16 at offset+4 in physics73 events is a sub-type
# header, NOT an entity-ID in the kill-event sense; matches to kill-event EIDs are
# purely coincidental.  Real physics-tracked entities produce 100+ events while
# false positives typically yield < 10.
_MIN_PHYSICS_EVENTS: int = 15
# For the *initial* incarnation (first physics73 event for an EID) the matched TM
# event must also be temporally isolated on its left side: no other TM event may
# have fired within this many ticks before it.  At match-start many vehicles spawn
# simultaneously, so TM events cluster within a few ticks; requiring isolation
# prevents matching an EID's first physics event to a neighbour's TM event.
_INITIAL_SPAWN_ISOLATION_TICKS: int = 10  # 1 s; match-start clusters are ≪ 1 s apart

# Sentinel slot value used to mark an EID as unresolvable after a known death
# (prevents physics-inferred attributions from leaking into later EID reuse windows).
_INVALID_SLOT: int = -1


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class _KillEvent:
    offset: int
    tick_idx: int
    slot: int
    vehicle_name: str
    victim_entity_id: int
    killer_entity_id: int


@dataclass
class _AwardEvent:
    offset: int
    slot: int
    award_name: str


@dataclass
class _LateSpawnEvent:
    offset: int
    entity_id: int
    slot: int
    vehicle_name: str


@dataclass
class _TankModelsEvent:
    offset: int
    slot: int
    vehicle_name: str


@dataclass
class _RawKillDetail:
    """
    Resolved per-kill event data, ready for the parser service to build
    ``KillDetail`` / ``DeathDetail`` objects with user_id resolution.
    """

    killer_slot: int
    killer_vehicle: str
    victim_slot: Optional[int]  # None if victim_entity_id could not be resolved
    victim_vehicle: Optional[str]  # None if victim_entity_id could not be resolved
    tick_idx: int = 0


@dataclass
class StreamDecodeResult:
    """
    Parsed stream data keyed by 0-indexed player slot.

    vehicle_kills[slot]          -> {veh_name: kill_count}
    vehicle_deaths[slot]         -> {veh_name: death_count}  (best-effort, partial)
    awards[slot]                 -> [award_name, ...]  (may contain duplicates)
    slot_vehicle_timeline[slot]  -> [(stream_offset, veh_name), ...]  ordered by offset
                                   Every vehicle activation/switch recorded in tankModels
                                   events; includes lineup vehicles never used in a kill.
    """

    vehicle_kills: dict[int, dict[str, int]] = field(default_factory=dict)
    vehicle_deaths: dict[int, dict[str, int]] = field(default_factory=dict)
    awards: dict[int, list[str]] = field(default_factory=dict)
    slot_vehicle_timeline: dict[int, list[tuple[int, str]]] = field(default_factory=dict)
    kill_details: list[_RawKillDetail] = field(default_factory=list)


@dataclass
class _StreamParseState:
    """
    Mutable accumulator populated during tick-iterating stream parse.

    Passed to every event handler so each handler can both read already-seen
    state and append new events.  After ``_iterate_stream`` completes, the
    fully-populated state is handed to ``_build_result`` for final resolution.
    """

    # Temporal skeleton — tick-frame offsets from ``_parse_tick_boundaries``
    tick_offsets: list[int] = field(default_factory=list)

    # Structured events collected during tick iteration
    kill_events: list[_KillEvent] = field(default_factory=list)
    award_events: list[_AwardEvent] = field(default_factory=list)
    late_spawn_events: list[_LateSpawnEvent] = field(default_factory=list)

    # tankModels events pre-populated from the dedicated parser (complex multi-
    # strategy scan kept separate; not emitted by the tick iterator)
    vehicle_activation_events: list[_TankModelsEvent] = field(default_factory=list)

    # Physics update index: EID -> sorted list of stream offsets for all
    # 025873f0 events.  Built incrementally by the physics handler.
    physics_eid_offsets: dict[int, list[int]] = field(default_factory=dict)

    # Interaction (UNKNOWN_37) index: EID -> sorted list of stream offsets
    # for all 025837f0 events where the EID appears as eid_A or eid_B.
    # Provides additional "entity was active at tick T" evidence used to
    # narrow dead-window disambiguation candidates.
    interaction_eid_offsets: dict[int, list[int]] = field(default_factory=dict)

    # Local-player EID sequence from 025837f0 events.  eid_A is always the
    # replay recorder's current entity.  Tracking distinct values in order
    # gives every respawn EID the recorder used, including vehicles where
    # they never got a kill.  Stored as list[(offset, eid_a)].
    local_player_eid_sequence: list[tuple[int, int]] = field(default_factory=list)


class ReplayStreamDecoderService:
    """Decodes the compressed rec_data stream from a War Thunder replay."""

    # Fallback scan cap used when no VehicleService is provided.
    # 11 (tankModels/ prefix) + 64 (generous vehicle-name headroom) = 75.
    # Rounded up to 80 to leave room for new additions without a code change.
    _DEFAULT_MAX_VEHICLE_PATH_LEN: int = 80

    def __init__(self, vehicle_service: "VehicleService | None" = None) -> None:
        """
        Args:
            vehicle_service: Optional service used to derive the backward-scan
                cap for vehicle-activation event parsing.  When provided the cap
                is set to ``len('tankModels/') + max(len(n) for n in all_internal_names)``
                so it automatically grows as new vehicles are added.  When
                omitted a generous hardcoded fallback is used instead.
                Also used for vehicle-type lookups in dead-window attribution.
        """
        self._vehicle_service = vehicle_service
        if vehicle_service is not None:
            all_names = vehicle_service.get_all_vehicles().keys()
            longest = max((len(n) for n in all_names), default=0)
            prefix_len = len(_TANKMODELS_PREFIX)  # 11
            self._max_vehicle_path_len: int = prefix_len + longest
            logger.debug(
                "tankModels scan cap: %d (prefix=%d + longest_name=%d)",
                self._max_vehicle_path_len,
                prefix_len,
                longest,
            )
        else:
            self._max_vehicle_path_len = self._DEFAULT_MAX_VEHICLE_PATH_LEN

    def decode_from_raw_replay(
        self,
        raw: bytes,
        *,
        slot_deaths: dict[int, int] | None = None,
        slot_teams: dict[int, int] | None = None,
    ) -> StreamDecodeResult:
        """
        Decompress the rec_data stream from raw .wrpl bytes and decode events.

        Args:
            raw:         Full contents of a .wrpl replay file.
            slot_deaths: Optional mapping of slot index -> authoritative death count
                         from the parsed BLK JSON.  When provided, EID death
                         attribution is capped per slot and timeline inference fills
                         any remaining gap.
            slot_teams:  Optional mapping of slot index -> team number (1 or 2)
                         from the parsed BLK JSON.  When provided, cross-team
                         checks in victim EID inference use authoritative team
                         data instead of heuristic slot-based guesses.

        Returns:
            StreamDecodeResult with vehicle_kills, vehicle_deaths, awards.
        """
        try:
            stream_data = self._decompress_stream(raw)
        except Exception as exc:
            logger.warning(f"Failed to decompress rec_data stream: {exc}")
            return StreamDecodeResult()

        return self.decode_stream(stream_data, slot_deaths=slot_deaths, slot_teams=slot_teams)

    def decode_stream(
        self,
        stream_data: bytes,
        *,
        slot_deaths: dict[int, int] | None = None,
        slot_teams: dict[int, int] | None = None,
    ) -> StreamDecodeResult:
        """
        Decode events directly from already-decompressed stream bytes.

        Execution phases:
          1. Tick boundary parsing  — locate all 02582df0 tick-frame markers so
             that every subsequent step works in tick-index space rather than raw
             byte-offset space.
          2. tankModels parsing     — dedicated multi-strategy scanner for vehicle
             activation events (complex backward-scan logic; kept separate).
          3. Tick iteration         — single pass through every tick frame;
             dispatches each 02 58 XX f0 event to a typed handler that appends to
             a shared ``_StreamParseState``.  Adding support for a new event type
             is a matter of registering one handler in ``_EVENT_HANDLERS``.
          4. EID resolution & build — builds ``eid_history`` from accumulated
             kill / late-spawn events, runs physics-gap spawn inference, then
             constructs the final ``StreamDecodeResult``.

        Args:
            stream_data: Decompressed rec_data stream bytes.
            slot_deaths: Optional mapping of slot index -> authoritative death count
                         from the parsed BLK JSON.  When provided, EID death
                         attribution is capped per slot and timeline inference fills
                         any remaining gap.
            slot_teams:  Optional mapping of slot index -> team number (1 or 2)
                         from the parsed BLK JSON.  When provided, cross-team
                         checks in victim EID inference use authoritative team
                         data instead of heuristic slot-based guesses.

        Returns:
            StreamDecodeResult with vehicle_kills, vehicle_deaths, awards.
        """
        # Phase 1: tick boundaries (stream's temporal skeleton)
        tick_offsets = self._parse_tick_boundaries(stream_data)

        # Phase 2: vehicle activation events (complex multi-strategy scan)
        vehicle_activation_events = self._parse_vehicle_activation_events(stream_data)

        # Phase 3: single-pass tick iteration
        state = _StreamParseState(tick_offsets=tick_offsets, vehicle_activation_events=vehicle_activation_events)
        self._iterate_stream(stream_data, state)
        # Use full-stream physics scan (covers events before the first tick marker)
        state.physics_eid_offsets = self._index_physics_eid_offsets(stream_data)

        logger.debug(
            "Stream parse: %d kills, %d awards, %d late-spawn events, " "%d tankModels events, %d unique physics EIDs",
            len(state.kill_events),
            len(state.award_events),
            len(state.late_spawn_events),
            len(state.vehicle_activation_events),
            len(state.physics_eid_offsets),
        )

        # Phase 4: EID resolution and result construction
        return self._build_result(state, slot_deaths=slot_deaths, slot_teams=slot_teams)

    # ------------------------------------------------------------------
    # Tick-iterating stream parser
    # ------------------------------------------------------------------

    #: Dispatch table: event type byte -> handler method name.
    #: Register a new entry here plus a ``_handle_<name>`` method to support
    #: additional 02 58 XX f0 event types without touching ``_iterate_stream``.
    _EVENT_HANDLERS: dict[int, str] = {
        0x58: "_handle_kill_event",
        0x78: "_handle_award_event",
        0x56: "_handle_late_spawn_event",
        0x73: "_handle_physics73_event",
        0x37: "_handle_interaction37_event",
    }

    def _iterate_stream(self, stream_data: bytes, state: _StreamParseState) -> None:
        """
        Single-pass tick-by-tick iteration over all structured (02 58 XX f0) events.

        For each tick frame the method scans the frame's payload bytes and
        dispatches every recognised event type to its handler.  Unrecognised bytes
        (the opaque per-entity physics-state binary blobs that make up ~87% of
        the stream) are skipped one byte at a time.

        Each handler receives ``(stream_data, offset, tick_idx, state)`` and is
        responsible for validating and parsing its event before appending to
        *state*.  Handlers are looked up via ``_EVENT_HANDLERS``; adding support
        for a new event type requires only a new dispatch entry and a new method.
        """
        N = len(stream_data)
        tick_offsets = state.tick_offsets
        num_ticks = len(tick_offsets)

        # Resolve handler names to bound methods once before the loop
        handlers: dict[int, Callable[[bytes, int, int, _StreamParseState], None]] = {
            type_byte: getattr(self, method_name) for type_byte, method_name in self._EVENT_HANDLERS.items()
        }

        for tick_idx in range(num_ticks):
            tick_start = tick_offsets[tick_idx]
            tick_end = tick_offsets[tick_idx + 1] if tick_idx + 1 < num_ticks else N

            pos = tick_start + _TICK_EVENT_SIZE  # skip the 22-byte tick marker itself
            while pos < tick_end - 3:
                if stream_data[pos] == 0x02 and stream_data[pos + 1] == 0x58 and stream_data[pos + 3] == 0xF0:
                    handler = handlers.get(stream_data[pos + 2])
                    if handler is not None:
                        handler(stream_data, pos, tick_idx, state)
                    pos += 4
                else:
                    pos += 1

    def _handle_kill_event(self, stream_data: bytes, offset: int, tick_idx: int, state: _StreamParseState) -> None:
        """Parse and accumulate a kill event (02 58 58 f0)."""
        N = len(stream_data)
        if offset + 13 > N:
            return
        if stream_data[offset + 5] != 0x00 or stream_data[offset + 6] != 0xFE or stream_data[offset + 7] != 0x3F:
            return
        player_slot = struct.unpack("<I", stream_data[offset + 8 : offset + 12])[0]
        if player_slot > _MAX_SLOT:
            return
        vehicle_name_length = stream_data[offset + 12]
        if vehicle_name_length < 1 or vehicle_name_length > 64:
            return
        vehicle_name_end = offset + 13 + vehicle_name_length
        if vehicle_name_end + 8 > N:
            return
        vehicle_name_bytes = stream_data[offset + 13 : vehicle_name_end]
        if not all(32 <= b < 127 for b in vehicle_name_bytes):
            return
        vehicle_name = vehicle_name_bytes.decode("ascii")
        victim_entity_id = struct.unpack("<H", stream_data[vehicle_name_end : vehicle_name_end + 2])[0]
        killer_entity_id = struct.unpack("<H", stream_data[vehicle_name_end + 2 : vehicle_name_end + 4])[0]
        if stream_data[vehicle_name_end + 4 : vehicle_name_end + 8] != b"\xff\xff\xff\xff":
            return
        state.kill_events.append(
            _KillEvent(
                offset=offset,
                tick_idx=tick_idx,
                slot=player_slot,
                vehicle_name=vehicle_name,
                victim_entity_id=victim_entity_id,
                killer_entity_id=killer_entity_id,
            )
        )

    def _handle_award_event(self, stream_data: bytes, offset: int, tick_idx: int, state: _StreamParseState) -> None:
        """Parse and accumulate an award event (02 58 78 f0)."""
        N = len(stream_data)
        if offset + 12 > N:
            return
        total_length = stream_data[offset + 4]
        if total_length < 6:
            return
        if stream_data[offset + 5] != 0x00 or stream_data[offset + 6] != 0x3E:
            return
        player_slot = struct.unpack("<I", stream_data[offset + 7 : offset + 11])[0]
        if player_slot > _MAX_SLOT:
            return
        name_length = stream_data[offset + 11]
        if name_length < 1 or name_length > 64:
            return
        name_bytes_end = offset + 12 + name_length
        if name_bytes_end > N:
            return
        name_bytes = stream_data[offset + 12 : name_bytes_end]
        if not all(32 <= b < 127 for b in name_bytes):
            return
        state.award_events.append(_AwardEvent(offset=offset, slot=player_slot, award_name=name_bytes.decode("ascii")))

    def _handle_late_spawn_event(
        self, stream_data: bytes, offset: int, tick_idx: int, state: _StreamParseState
    ) -> None:
        """Parse and accumulate a late-spawn/respawn event (02 58 56 f0)."""
        N = len(stream_data)
        if offset + 14 > N:
            return
        if stream_data[offset + 6] != 0x7E:
            return
        entity_id = struct.unpack("<H", stream_data[offset + 7 : offset + 9])[0]
        player_slot = struct.unpack("<I", stream_data[offset + 9 : offset + 13])[0]
        if player_slot > _MAX_SLOT:
            return
        vehicle_name_length = stream_data[offset + 13]
        if vehicle_name_length < 1 or vehicle_name_length > 64:
            return
        name_bytes_end = offset + 14 + vehicle_name_length
        if name_bytes_end > N:
            return
        name_bytes = stream_data[offset + 14 : name_bytes_end]
        if not all(32 <= b < 127 for b in name_bytes):
            return
        state.late_spawn_events.append(
            _LateSpawnEvent(
                offset=offset,
                entity_id=entity_id,
                slot=player_slot,
                vehicle_name=name_bytes.decode("ascii"),
            )
        )

    def _handle_physics73_event(self, stream_data: bytes, offset: int, tick_idx: int, state: _StreamParseState) -> None:
        """Index a physics73 event (02 58 73 f0) by EID for spawn inference."""
        if offset + 6 <= len(stream_data):
            eid = struct.unpack_from("<H", stream_data, offset + 4)[0]
            state.physics_eid_offsets.setdefault(eid, []).append(offset)

    def _handle_interaction37_event(
        self, stream_data: bytes, offset: int, tick_idx: int, state: _StreamParseState
    ) -> None:
        """Index an interaction event (02 58 37 f0) by both EIDs.

        Structure: [02 58 37 f0] [07 00 06] [eid_A u16 LE@+7] [eid_B u16 LE@+9] ...
        eid_A is always the replay recorder's (local player's) current entity.
        Both eid_A and eid_B are recorded — the event proves both entities were
        alive at this tick, providing disambiguation evidence for dead-window
        attribution.

        Additionally, eid_A is tracked in local_player_eid_sequence: each time
        eid_A changes, the player has respawned in a new vehicle with a new EID.
        """
        if offset + 11 > len(stream_data):
            return
        eid_a = struct.unpack_from("<H", stream_data, offset + 7)[0]
        eid_b = struct.unpack_from("<H", stream_data, offset + 9)[0]
        state.interaction_eid_offsets.setdefault(eid_a, []).append(offset)
        if eid_b != eid_a:
            state.interaction_eid_offsets.setdefault(eid_b, []).append(offset)

        # Track local-player EID changes (eid_a is the recorder's entity)
        if not state.local_player_eid_sequence or state.local_player_eid_sequence[-1][1] != eid_a:
            state.local_player_eid_sequence.append((offset, eid_a))

    # ------------------------------------------------------------------
    # Result builder (Phase 4: EID resolution + StreamDecodeResult)
    # ------------------------------------------------------------------

    def _build_result(
        self,
        state: _StreamParseState,
        *,
        slot_deaths: dict[int, int] | None = None,
        slot_teams: dict[int, int] | None = None,
    ) -> StreamDecodeResult:
        """
        Build a ``StreamDecodeResult`` from fully-accumulated ``_StreamParseState``.

        Covers:
          - Vehicle kill / award / timeline population
          - EID history construction (Methods 1 & 2)
          - Physics-gap spawn inference (Method 5)
          - Per-event kill detail resolution
          - EID-based death attribution with BLK-cap enforcement
          - Timeline-based death inference for any remaining gap
        """
        result = StreamDecodeResult()

        # --- Vehicle kills ---
        for event in state.kill_events:
            slot_dict = result.vehicle_kills.setdefault(event.slot, {})
            slot_dict[event.vehicle_name] = slot_dict.get(event.vehicle_name, 0) + 1

        # --- Awards ---
        for event in state.award_events:
            result.awards.setdefault(event.slot, []).append(event.award_name)

        # --- Vehicle timeline (from tankModels events) ---
        for event in state.vehicle_activation_events:
            result.slot_vehicle_timeline.setdefault(event.slot, []).append((event.offset, event.vehicle_name))
        for slot in result.slot_vehicle_timeline:
            result.slot_vehicle_timeline[slot].sort(key=lambda x: x[0])

        # --- Supplement timeline from kill events (slots with no tankModels coverage) ---
        # Some players' vehicle activations are never captured by the tankModels parser
        # (e.g. their spawn event used a format variant we don't recognise yet).  For
        # those slots, kill events give us (slot, vehicle_name, offset) directly — use
        # them as synthetic timeline anchors so timeline inference can still run.
        # Only applies to slots that have deaths and zero tankModels entries.
        if slot_deaths:
            slots_needing_supplement = {
                s for s in slot_deaths if s not in result.slot_vehicle_timeline and slot_deaths[s] > 0
            }
            for event in state.kill_events:
                if event.slot in slots_needing_supplement:
                    result.slot_vehicle_timeline.setdefault(event.slot, []).append((event.offset, event.vehicle_name))
            for slot in slots_needing_supplement:
                if slot in result.slot_vehicle_timeline:
                    result.slot_vehicle_timeline[slot].sort(key=lambda x: x[0])

        # --- EID history (Methods 1 & 2) ---
        # Entity IDs are 16-bit values reused across vehicle lives.  Store every
        # observed assignment as (offset, slot, vehicle_name) and resolve at
        # query time using the closest-preceding entry to avoid EID-reuse errors.
        eid_history: dict[int, list[tuple[int, int, str]]] = {}

        for event in state.kill_events:
            eid_history.setdefault(event.killer_entity_id, []).append((event.offset, event.slot, event.vehicle_name))
        for spawn_event in state.late_spawn_events:
            eid_history.setdefault(spawn_event.entity_id, []).append(
                (spawn_event.offset, spawn_event.slot, spawn_event.vehicle_name)
            )
        for entries in eid_history.values():
            entries.sort(key=lambda x: x[0])

        # --- Physics-gap spawn inference (Method 5) ---
        new_inferences = self._infer_physics_spawn_attributions(
            state.kill_events,
            eid_history,
            state.vehicle_activation_events,
            state.physics_eid_offsets,
            state.tick_offsets,
        )
        if new_inferences:
            logger.debug("Physics-inferred spawn attributions: %d new EID mappings", new_inferences)
            for entries in eid_history.values():
                if len(entries) > 1:
                    entries.sort(key=lambda x: x[0])

        # --- Initial-spawn EID inference (Method 6) ---
        # Derives missing initial-spawn EIDs from the observed pattern
        # eid = base_eid + slot, where base_eid is the session-wide EID base
        # detected from already-resolved kill-event entries in eid_history.
        new_initial = self._infer_initial_spawn_eids(
            eid_history,
            state.vehicle_activation_events,
            state.physics_eid_offsets,
        )
        if new_initial:
            logger.debug("Initial-spawn EID inferences: %d new EID mappings", new_initial)

        # --- Local-player respawn EID inference (Method 6b) ---
        # The 025837f0 interaction events encode the recorder's current EID as
        # eid_A.  Each distinct eid_A value corresponds to a new vehicle life.
        # Using the initial eid_A and the base+slot formula, we can derive the
        # recorder's slot, then register ALL of their respawn EIDs — including
        # vehicles where they never scored a kill.
        new_local = self._infer_local_player_respawn_eids(
            eid_history,
            state.local_player_eid_sequence,
            state.vehicle_activation_events,
        )
        if new_local:
            logger.debug("Local-player respawn EID inferences: %d new EID mappings", new_local)

        # --- Dead-window TM activation inference (Method 7, multi-pass) ---
        # For victim EIDs with physics73 events, the entity was spawned (TM
        # activation) during the gap between the last physics event and the kill.
        # Finds the unique slot whose first new-vehicle TM in that window is
        # still their active vehicle at kill time.
        # Runs in a loop: each pass may resolve new EIDs whose attributions then
        # act as additional constraints (e/f) in the next pass, allowing further
        # disambiguation.  Stops when no new EIDs are resolved.
        total_deadwindow = 0
        m7_ambiguous_eids: set[int] = set()
        while True:
            new_deadwindow, new_ambiguous = self._infer_deadwindow_victim_eids(
                state.kill_events,
                eid_history,
                state.vehicle_activation_events,
                state.physics_eid_offsets,
                state.tick_offsets,
                slot_deaths,
                state.interaction_eid_offsets,
                slot_teams=slot_teams,
            )
            total_deadwindow += new_deadwindow
            m7_ambiguous_eids |= new_ambiguous
            if not new_deadwindow:
                break
        # Remove EIDs that were eventually resolved in later passes
        m7_ambiguous_eids -= set(eid_history.keys())
        if total_deadwindow:
            logger.debug("Dead-window TM inferences: %d new EID mappings (multi-pass)", total_deadwindow)

        # --- TM-transition death matching (Method 8) ---
        # For each slot where BLK deaths > EID-resolved deaths, walk the TM
        # timeline.  Each consecutive TM transition (vehicle_A → vehicle_B)
        # implies a death in vehicle_A.  When no EID-resolved death already
        # covers that transition, search for an unresolved kill event whose
        # victim_eid is absent from eid_history AND whose tick falls between
        # the current vehicle's TM activation and the next vehicle's TM
        # activation.  Pick the candidate closest to the next TM event (the
        # death most likely triggering the respawn).  Add the mapping
        # victim_eid → (slot, vehicle_A) to eid_history.
        #
        # This resolves victims who never killed anyone (so their EID never
        # appears as killer_entity_id) and never triggered a late-spawn event.
        new_tm_death = self._infer_tm_transition_deaths(
            state.kill_events,
            eid_history,
            result.slot_vehicle_timeline if result.slot_vehicle_timeline else {},
            state.tick_offsets,
            slot_deaths,
            state.physics_eid_offsets,
            m7_ambiguous_eids,
            slot_teams=slot_teams,
        )
        if new_tm_death:
            logger.debug("TM-transition death inferences: %d new EID mappings", new_tm_death)

        def _lookup_eid(eid: int, at_offset: int) -> "tuple[int, str] | None":
            """Return (slot, vehicle_name) for the EID as of *at_offset*, or None."""
            entries = eid_history.get(eid)
            if not entries:
                return None
            result_entry = None
            for offset, slot, vehicle in entries:
                if offset <= at_offset:
                    result_entry = (slot, vehicle)
                else:
                    break
            if result_entry is None:
                return None
            # Sentinel: EID was reused after a physics-inferred death boundary;
            # this offset is past the valid attribution window.
            if result_entry[0] == _INVALID_SLOT:
                return None
            return result_entry

        # --- Per-event kill detail records (resolved) ---
        # Populated for ALL kill events regardless of the death cap so that
        # kills.vehicles always reflects every event in the stream.
        for event in state.kill_events:
            victim_slot: Optional[int] = None
            victim_vehicle: Optional[str] = None
            resolved = _lookup_eid(event.victim_entity_id, event.offset)
            if resolved is not None:
                _v_slot, _v_vehicle = resolved
                # A player cannot kill themselves in normal gameplay — if the EID
                # lookup resolves the victim to the same slot as the killer it is
                # a false attribution caused by EID reuse.  Discard it.
                if _v_slot != event.slot:
                    victim_slot, victim_vehicle = _v_slot, _v_vehicle
            result.kill_details.append(
                _RawKillDetail(
                    killer_slot=event.slot,
                    killer_vehicle=event.vehicle_name,
                    victim_slot=victim_slot,
                    victim_vehicle=victim_vehicle,
                    tick_idx=event.tick_idx,
                )
            )

        # --- EID-based death attribution ---
        # slot_death_counts caps each slot at its BLK death count, filtering out
        # kills that don't increment the scoreboard (e.g. team kills).
        slot_death_counts: dict[int, int] = {}
        resolved_count = 0
        unresolved_count = 0
        for event in state.kill_events:
            resolved = _lookup_eid(event.victim_entity_id, event.offset)
            if resolved is not None:
                victim_slot, victim_vehicle = resolved
                # Discard self-kill attributions (EID reuse artefact)
                if victim_slot == event.slot:
                    unresolved_count += 1
                    continue
                if slot_deaths is not None:
                    death_cap = slot_deaths.get(victim_slot, 0)
                    if slot_death_counts.get(victim_slot, 0) >= death_cap:
                        unresolved_count += 1
                        continue
                slot_dict = result.vehicle_deaths.setdefault(victim_slot, {})
                slot_dict[victim_vehicle] = slot_dict.get(victim_vehicle, 0) + 1
                slot_death_counts[victim_slot] = slot_death_counts.get(victim_slot, 0) + 1
                resolved_count += 1
            else:
                unresolved_count += 1

        logger.debug("Death attribution: %d resolved, %d unresolvable/filtered", resolved_count, unresolved_count)

        # --- Timeline-based death inference ---
        # For slots where EID attribution didn't cover all BLK deaths, use the
        # vehicle switch timeline: each consecutive vehicle switch implies one death
        # in the preceding vehicle.
        #
        # Known edge case: aircraft can spawn via spawn points without a death, so a
        # ground->air transition may not imply a death in the ground vehicle.
        if slot_deaths:
            for slot, timeline in result.slot_vehicle_timeline.items():
                total_deaths = slot_deaths.get(slot, 0)
                if total_deaths == 0:
                    continue
                already_attributed = sum(result.vehicle_deaths.get(slot, {}).values())
                remaining_deaths = total_deaths - already_attributed
                if remaining_deaths <= 0:
                    continue

                ordered_vehicles = [vehicle_name for _, vehicle_name in timeline]
                if not ordered_vehicles:
                    continue

                # EID resolution may have already attributed some deaths to specific
                # vehicles.  To avoid double-counting, we track per-vehicle "credits"
                # — each credit represents one death already counted by EID for that
                # vehicle.  As we walk the timeline, each transition whose vehicle has
                # a credit "consumes" that credit instead of adding another death.
                eid_credits: dict[str, int] = dict(result.vehicle_deaths.get(slot, {}))

                if len(ordered_vehicles) == 1:
                    vehicle_name = ordered_vehicles[0]
                    slot_dict = result.vehicle_deaths.setdefault(slot, {})
                    slot_dict[vehicle_name] = slot_dict.get(vehicle_name, 0) + remaining_deaths
                    continue

                for i in range(len(ordered_vehicles) - 1):
                    if remaining_deaths <= 0:
                        break
                    vehicle_name = ordered_vehicles[i]
                    if eid_credits.get(vehicle_name, 0) > 0:
                        eid_credits[vehicle_name] -= 1  # consume EID credit; death already counted
                    else:
                        slot_dict = result.vehicle_deaths.setdefault(slot, {})
                        slot_dict[vehicle_name] = slot_dict.get(vehicle_name, 0) + 1
                        remaining_deaths -= 1

                if remaining_deaths > 0:
                    final_vehicle = ordered_vehicles[-1]
                    slot_dict = result.vehicle_deaths.setdefault(slot, {})
                    slot_dict[final_vehicle] = slot_dict.get(final_vehicle, 0) + remaining_deaths

        return result

    # ------------------------------------------------------------------
    # Decompression
    # ------------------------------------------------------------------

    @staticmethod
    def _decompress_stream(raw: bytes) -> bytes:
        """
        Extract and decompress the rec_data stream from raw .wrpl bytes.

        Offsets determined empirically:
          684-688  results_offset     (u32 LE) — start of the results BLK section
          748-752  stream_header_size (u32 LE) — size of the stream header block
          1224+stream_header_size  start of zlib-compressed data (skip first 2 bytes = zlib header)
        """
        if len(raw) < 752:
            raise ValueError("Replay too short to contain stream offsets")
        stream_header_size = struct.unpack("<I", raw[748:752])[0]
        results_offset = struct.unpack("<I", raw[684:688])[0]
        compressed_start = 1224 + stream_header_size + 2  # skip 2-byte zlib header
        compressed_data = raw[compressed_start:results_offset]
        return zlib.decompress(compressed_data)

    # ------------------------------------------------------------------
    # Event parsers
    # ------------------------------------------------------------------

    def _parse_tick_boundaries(self, stream_data: bytes) -> list[int]:
        """
        Return the sorted stream offsets of all 02582df0 tick-frame markers.

        The stream is organised as a sequence of ~10 Hz simulation tick frames,
        each delimited by a 22-byte ``02582df0`` event.  Every structured event
        (kill, award, late-spawn, physics update) falls inside a tick frame.
        Using tick indices instead of raw byte offsets gives semantically
        meaningful proximity measurements for spawn correlation.
        """
        offsets: list[int] = []
        pos = 0
        while True:
            idx = stream_data.find(_TICK_MARKER, pos)
            if idx == -1:
                break
            pos = idx + 1
            offsets.append(idx)
        return offsets

    def _index_physics_eid_offsets(self, stream_data: bytes) -> dict[int, list[int]]:
        """
        Index all 025873f0 physics-update events by entity ID.

        Physics event structure (confirmed empirically):
          [00..03]  marker    02 58 73 f0
          [04..05]  EID       (u16 LE)  — entity ID of the vehicle
          [06..07]  phystype  (u16 LE)  — vehicle physics class; NOT player slot
          [08+]     other fields

        Returns:
            EID -> sorted list of stream offsets for every physics event with that EID.
        """
        result: dict[int, list[int]] = {}
        pos = 0
        while True:
            idx = stream_data.find(_PHYSICS_73_MARKER, pos)
            if idx == -1:
                break
            pos = idx + 1
            if idx + 6 <= len(stream_data):
                eid = struct.unpack_from("<H", stream_data, idx + 4)[0]
                result.setdefault(eid, []).append(idx)
        for lst in result.values():
            lst.sort()
        return result

    def _infer_physics_spawn_attributions(
        self,
        kill_events: list[_KillEvent],
        eid_history: dict[int, list[tuple[int, int, str]]],
        vehicle_activation_events: list[_TankModelsEvent],
        physics_eid_offsets: dict[int, list[int]],
        tick_offsets: list[int],
    ) -> int:
        """
        Attribute unresolved victim EIDs using physics-gap spawn analysis.

        For each victim EID not yet in *eid_history*, locates the most recent
        physics73 gap (>= _PHYSICS_INCARNATION_TICKS ticks) before the anchor
        kill.  The first physics73 event after the gap is the re-spawn offset;
        it is matched to the nearest preceding vehicle-activation event subject to:
          (a) within _PHYSICS_TM_MAX_TICKS ticks of the re-spawn
          (b) no other TM event fires between it and the re-spawn
          (c) attributed slot != killer slot (guards against EID-reuse artefacts)

        Returns the number of new EID attributions added to *eid_history*.
        """
        if not vehicle_activation_events:
            return 0

        tm_sorted_offsets = [tm.offset for tm in vehicle_activation_events]
        tm_by_offset: dict[int, _TankModelsEvent] = {tm.offset: tm for tm in vehicle_activation_events}

        def tick_of(offset: int) -> int:
            return bisect.bisect_right(tick_offsets, offset) - 1

        # Only process victim EIDs that are not yet in eid_history
        # Use the LAST kill event for each unique victim EID as the anchor
        # (gives the tightest before-kill physics window for gap detection)
        unresolved: dict[int, _KillEvent] = {}
        for event in kill_events:
            if event.victim_entity_id not in eid_history:
                unresolved[event.victim_entity_id] = event  # last kill event wins

        if not unresolved:
            return 0

        added = 0

        for victim_eid, kill_event in unresolved.items():
            all_phys = physics_eid_offsets.get(victim_eid, [])
            before_kill = [o for o in all_phys if o < kill_event.offset]
            if len(before_kill) < _MIN_PHYSICS_EVENTS:
                continue  # too few physics events — likely false-positive matches

            # Find the LAST gap > _PHYSICS_INCARNATION_TICKS (strictly greater)
            last_boundary: int | None = None
            for i in range(len(before_kill) - 1, 0, -1):
                if tick_of(before_kill[i]) - tick_of(before_kill[i - 1]) > _PHYSICS_INCARNATION_TICKS:
                    last_boundary = before_kill[i]
                    break
            if last_boundary is None:
                continue

            spawn_offset = last_boundary

            # (d) Staleness guard: if the last physics event before the kill is
            # much earlier than the kill itself, the entity died after the
            # spawned incarnation ended and the EID was reused.  Reject the
            # attribution to avoid poisoning the eid_history with a stale
            # incarnation's slot/vehicle.
            last_phys_before_kill_tick = tick_of(before_kill[-1])
            kill_tick = kill_event.tick_idx
            if kill_tick - last_phys_before_kill_tick > _PHYSICS_STALE_TICKS:
                continue

            idx = bisect.bisect_right(tm_sorted_offsets, spawn_offset) - 1
            if idx < 0:
                continue

            nearest_tm_off = tm_sorted_offsets[idx]
            nearest_tm = tm_by_offset[nearest_tm_off]

            # (a) TM event must be within proximity window of re-spawn
            if tick_of(spawn_offset) - tick_of(nearest_tm_off) > _PHYSICS_TM_MAX_TICKS:
                continue
            # (b) No other TM event between nearest_tm and spawn
            if any(nearest_tm_off < o < spawn_offset for o in tm_sorted_offsets):
                continue
            # (c) Attributed slot must differ from killer slot
            if nearest_tm.slot == kill_event.slot:
                continue

            eid_history[victim_eid] = [(spawn_offset, nearest_tm.slot, nearest_tm.vehicle_name)]
            added += 1
            logger.debug(
                "Physics-inferred attribution: EID %d → slot %d %r (spawn tick=%d)",
                victim_eid,
                nearest_tm.slot,
                nearest_tm.vehicle_name,
                tick_of(spawn_offset),
            )

        return added

    def _infer_deadwindow_victim_eids(
        self,
        kill_events: list[_KillEvent],
        eid_history: dict[int, list[tuple[int, int, str]]],
        vehicle_activation_events: list[_TankModelsEvent],
        physics_eid_offsets: dict[int, list[int]],
        tick_offsets: list[int],
        slot_deaths: dict[int, int] | None,
        interaction_eid_offsets: dict[int, list[int]] | None = None,
        slot_teams: dict[int, int] | None = None,
    ) -> "tuple[int, set[int]]":
        """
        Attribute unresolved victim EIDs using dead-window TM activation (Method 7).

        When an entity is killed but has no eid_history entry, it was spawned
        during the "dead window": the interval between its last observed physics73
        event and the kill event.  The spawning vehicle is recorded via a TM
        activation event that falls inside this window.  This method finds the
        unique slot whose most-recent TM activation in the dead window is still
        their active vehicle at kill time (no subsequent TM before the kill).

        Constraints applied to each candidate slot S:
          (a) S has at least one TM activation strictly between last_phys_tick
              and kill_tick (the dead window).
          (b) The most recent TM activation for S in that window is still their
              active vehicle at kill_tick (no later TM for S before the kill).
          (c) S != killer slot.
          (d) slot_deaths.get(S, 0) > 0  (S has at least one recorded death).
          (e) (S, vehicle) has NOT been attributed to any other known EID at any
              offset <= kill_event.offset (all-historical, not just latest entry).
          (f) (S, vehicle) has NOT been attributed to any other known EID in any
              kill event AFTER kill_event.offset (forward attribution constraint).
          (j) If the victim EID has interaction37 activity within the dead window,
              the candidate's TM must fire BEFORE that activity tick (the entity
              was already alive, so it cannot have been spawned after).
          (n) S must be on the opposite team from the killer.  When BLK team
              data is available (via *slot_teams*), authoritative assignments are
              used; otherwise falls back to a heuristic (slots 0-15 = team 1,
              16-31 = team 2).  Players do not kill teammates in RB.

        Additionally, if VehicleService is available and the killer vehicle type
        can be determined:
          (g) If the killer is a ground non-AA vehicle (Tank Destroyer, etc.),
              aircraft candidates are excluded (they would not appear as ground
              kill targets).

        Attribution is only made when exactly one candidate slot satisfies all
        constraints — ties are left unresolved to avoid false positives.

        Only processes victim EIDs that have at least one physics73 event
        (zero-physics EIDs lack the dead-window anchor and are skipped).

        Returns a tuple of (count_added, ambiguous_eids) where count_added is
        the number of new EID attributions added and ambiguous_eids is the set
        of victim EIDs that had multiple candidates (i.e. Method 7 tried but
        could not disambiguate).
        """
        if not vehicle_activation_events:
            return 0

        from src.common.enums.vehicle_type import VehicleType

        _AIR_TYPES = frozenset({VehicleType.FIGHTER, VehicleType.BOMBER, VehicleType.STRIKE_AIRCRAFT})
        _HELI_TYPES = frozenset({VehicleType.ATTACK_HELICOPTER, VehicleType.UTILITY_HELICOPTER})

        def tick_of(offset: int) -> int:
            return bisect.bisect_right(tick_offsets, offset) - 1

        def _get_vtype(vehicle_name: str) -> "VehicleType | None":
            """Look up a vehicle's type from VehicleService; returns None if unavailable."""
            if self._vehicle_service is None:
                return None
            v = self._vehicle_service.get_vehicles_by_internal_name(vehicle_name)
            if v is None:
                return None
            return v.vehicle_type

        # Build per-slot sorted TM list once
        slot_tms: dict[int, list[_TankModelsEvent]] = {}
        for tm in sorted(vehicle_activation_events, key=lambda e: e.offset):
            slot_tms.setdefault(tm.slot, []).append(tm)

        # Process victim EIDs that have at least one physics73 event before
        # the kill AND a non-trivial dead window (last_phys_tick < kill_tick).
        # This includes EIDs not yet in eid_history AND EIDs whose covering
        # entry may belong to a prior incarnation (e.g. Method 6 placed an
        # entry for the wrong slot due to EID reuse between incarnations).
        # Use the last kill event for each victim EID as the anchor.
        candidates_by_eid: dict[int, _KillEvent] = {}
        for event in kill_events:
            candidates_by_eid[event.victim_entity_id] = event  # last kill wins

        added = 0
        ambiguous_eids: set[int] = set()

        for victim_eid, kill_event in candidates_by_eid.items():
            all_phys = physics_eid_offsets.get(victim_eid, [])
            before_kill = [o for o in all_phys if o < kill_event.offset]
            if len(before_kill) < _MIN_PHYSICS_EVENTS:
                continue  # too few physics events — likely false-positive pattern matches

            last_phys_tick = tick_of(before_kill[-1])
            kill_tick = kill_event.tick_idx

            if kill_tick <= last_phys_tick:
                continue  # no dead window

            # --- Interaction-based activity floor ---
            # If the victim EID appears in an interaction37 event between
            # last_phys_tick and kill_tick, the entity was provably alive at
            # that tick.  Any candidate whose TM activation is AFTER that tick
            # cannot be the spawner (the entity already existed).
            last_activity_tick = last_phys_tick
            if interaction_eid_offsets:
                ia_offsets = interaction_eid_offsets.get(victim_eid, [])
                for ia_off in ia_offsets:
                    ia_tick = tick_of(ia_off)
                    if last_phys_tick < ia_tick < kill_tick and ia_tick > last_activity_tick:
                        last_activity_tick = ia_tick

            # Skip EIDs already attributed in a prior pass of Method 7:
            # if eid_history already contains an entry with offset > last_phys
            # anchor (i.e., inside or after the dead window), this incarnation
            # is already resolved and re-processing it would add a duplicate.
            existing_entries = eid_history.get(victim_eid)
            if existing_entries:
                last_anchor_offset = before_kill[-1]
                if any(off > last_anchor_offset for off, _sl, _veh in existing_entries):
                    continue  # already resolved in a prior pass

            # (e) Build attributed_at_kill: (slot, vehicle) pairs that are
            # "taken" by a known EID that is *still alive* at kill_event.offset.
            # A slot is only considered taken if the attributed EID has NOT been
            # killed before kill_event.offset — if that EID was already killed,
            # the slot is free to have respawned in the same vehicle (e.g. no
            # new TM event on respawn), so we must not exclude it.
            # Build EID->kill_offset map (last kill per EID wins).
            eid_kill_offset: dict[int, int] = {}
            for ev in kill_events:
                eid_kill_offset[ev.victim_entity_id] = ev.offset

            attributed_at_kill: set[tuple[int, str]] = set()
            for known_eid, entries in eid_history.items():
                if known_eid == victim_eid:
                    continue
                eid_kill = eid_kill_offset.get(known_eid)
                for off, sl, veh in entries:
                    if off <= kill_event.offset:
                        # Only "take" this attribution if the entity is still
                        # alive at kill_event.offset (never killed, or killed
                        # at or after the current kill).
                        if eid_kill is None or eid_kill >= kill_event.offset:
                            attributed_at_kill.add((sl, veh))
                    # Do NOT break — check all entries to catch all attributions

            # (g-pre) Build death_tick_per_slot: for each slot, the tick of
            # their most recent confirmed death strictly before kill_event.offset.
            # Used by constraint (g) to require that a candidate slot actually
            # died and respawned within the dead window.
            death_tick_per_slot: dict[int, int] = {}
            for ev in kill_events:
                if ev.offset >= kill_event.offset:
                    continue  # only deaths before the current kill
                victim_hist = eid_history.get(ev.victim_entity_id)
                if not victim_hist:
                    continue
                resolved_slot: "int | None" = None
                for off, sl, _veh in victim_hist:
                    if off <= ev.offset:
                        resolved_slot = sl
                    else:
                        break
                if resolved_slot is not None:
                    if ev.tick_idx > death_tick_per_slot.get(resolved_slot, -1):
                        death_tick_per_slot[resolved_slot] = ev.tick_idx

            # (f) Build a set of (slot, vehicle) pairs attributed to known EIDs
            # in kill events AFTER kill_event.offset.  A vehicle that later
            # appears as a victim with a resolved EID cannot simultaneously be
            # the unresolved victim now.
            forward_attributed: set[tuple[int, str]] = set()
            for later_ev in kill_events:
                if later_ev.offset <= kill_event.offset:
                    continue
                if later_ev.victim_entity_id == victim_eid:
                    continue
                later_hist = eid_history.get(later_ev.victim_entity_id)
                if later_hist is None:
                    continue
                fwd_best: "tuple[int, str] | None" = None
                for off, sl, veh in later_hist:
                    if off <= later_ev.offset:
                        fwd_best = (sl, veh)
                    else:
                        break
                if fwd_best is not None:
                    forward_attributed.add(fwd_best)

            # Find candidate slots: TM in (last_phys_tick, kill_tick),
            # still active at kill_tick, not killer, deaths > 0, not already
            # attributed to a known EID.
            cands: list[tuple[int, str]] = []  # (slot, vehicle_name)

            for slot, tms in slot_tms.items():
                if slot == kill_event.slot:  # (c) exclude killer
                    continue
                if slot_deaths is not None and slot_deaths.get(slot, 0) == 0:  # (d)
                    continue

                # Find TMs for this slot strictly inside the dead window
                window_tms = [tm for tm in tms if last_phys_tick < tick_of(tm.offset) < kill_tick]
                if not window_tms:
                    continue  # (a) no TM in dead window

                # Most-recent TM in the dead window
                latest_window_tm = window_tms[-1]
                latest_window_tick = tick_of(latest_window_tm.offset)

                # (j) interaction-activity: if we know the victim EID was active
                # at last_activity_tick (from interaction37 evidence), the
                # spawning TM must have fired BEFORE that activity.  A TM that
                # fires after the entity was already observed active cannot be
                # the spawn that produced this entity.
                if last_activity_tick > last_phys_tick and latest_window_tick > last_activity_tick:
                    continue

                # (b) no TM for this slot between latest_window_tm and kill_tick
                subsequent = [tm for tm in tms if latest_window_tick < tick_of(tm.offset) < kill_tick]
                if subsequent:
                    continue  # vehicle changed before kill — not this spawn

                vname = latest_window_tm.vehicle_name

                # (e) exclude candidates attributed to a live known EID
                if (slot, vname) in attributed_at_kill:
                    continue

                # (f) exclude candidates attributed to a known EID in a later kill
                if (slot, vname) in forward_attributed:
                    continue

                # (g) spawn-after-death: only accept a candidate slot when we
                # have a confirmed death for it *after* last_phys_tick.
                if death_tick_per_slot.get(slot, -1) <= last_phys_tick:
                    continue

                # (h/k) The victim EID has physics73 events — physics73 tracks
                # ground entities while aircraft use physics74.  Exclude
                # aircraft/helicopter candidates since a ground entity cannot
                # belong to an airborne spawn.  (Subsumes the former
                # killer-based ground-non-AA filter which was a weaker check.)
                cand_vtype = _get_vtype(vname)
                if cand_vtype in _AIR_TYPES or cand_vtype in _HELI_TYPES:
                    continue

                # (i) TM-after-death: the TM event must come AFTER the slot's last
                # confirmed death (proving it's a respawn, not an ongoing life).
                slot_last_death = death_tick_per_slot.get(slot, -1)
                if slot_last_death >= 0 and latest_window_tick <= slot_last_death:
                    continue

                # (n) Cross-team: victim slot must be on the opposite team from
                # the killer.  When authoritative team data is available (from
                # BLK), use it directly; otherwise fall back to the slot-based
                # heuristic (slots 0-15 = team 1, 16-31 = team 2).
                if slot_teams:
                    killer_team = slot_teams.get(kill_event.slot)
                    slot_team = slot_teams.get(slot)
                else:
                    killer_team = 1 if kill_event.slot < 16 else 2
                    slot_team = 1 if slot < 16 else 2
                if slot_team == killer_team:
                    continue

                cands.append((slot, vname, latest_window_tm.offset))

            # (l) Post-kill respawn evidence: if multiple candidates remain
            # and exactly one has a TM (vehicle switch) shortly after the kill,
            # prefer it — respawning proves they died in that window.
            _RESPAWN_MAX_TICKS = 500
            if len(cands) > 1:
                with_respawn: list[tuple[int, str, int]] = []
                for s, v, o in cands:
                    tms_for_s = slot_tms.get(s, [])
                    next_tms = [tm for tm in tms_for_s if tick_of(tm.offset) > kill_tick]
                    if next_tms:
                        first_next_tick = tick_of(next_tms[0].offset)
                        if first_next_tick - kill_tick <= _RESPAWN_MAX_TICKS:
                            with_respawn.append((s, v, o))
                if len(with_respawn) == 1:
                    cands = with_respawn

            if len(cands) != 1:
                if len(cands) > 1:
                    ambiguous_eids.add(victim_eid)
                continue  # ambiguous or no match

            inferred_slot, inferred_vehicle, tm_offset = cands[0]

            # Insert/update the entry.  If the EID already has history entries
            # from a prior incarnation (e.g. Methods 1/2), append the new
            # attribution at the TM offset so _lookup_eid uses it for the kill.
            existing = eid_history.get(victim_eid)
            new_entry = (tm_offset, inferred_slot, inferred_vehicle)
            if existing is None:
                eid_history[victim_eid] = [new_entry]
            else:
                existing.append(new_entry)
                existing.sort(key=lambda x: x[0])
            added += 1
            logger.debug(
                "Dead-window EID inferred: EID %d \u2192 slot %d %r " "(dead_window ticks %d\u2013%d)",
                victim_eid,
                inferred_slot,
                inferred_vehicle,
                last_phys_tick,
                kill_tick,
            )

        return added, ambiguous_eids

    def _infer_tm_transition_deaths(
        self,
        kill_events: list[_KillEvent],
        eid_history: dict[int, list[tuple[int, int, str]]],
        slot_vehicle_timeline: dict[int, list[tuple[int, str]]],
        tick_offsets: list[int],
        slot_deaths: dict[int, int] | None,
        physics_eid_offsets: dict[int, list[int]] | None = None,
        m7_ambiguous_eids: set[int] | None = None,
        slot_teams: dict[int, int] | None = None,
    ) -> int:
        """
        Attribute unresolved victim EIDs using TM-timeline transition matching.

        Each consecutive vehicle transition in a slot's TM timeline implies at
        least one death in the preceding vehicle (more with backup respawns).
        When a death is not already covered by an EID-resolved kill event, this
        method searches for unresolved kill events whose tick falls between the
        current vehicle activation and the next.

        Among matching candidates, the one whose tick is closest to (and before)
        the next TM activation is selected — it is the kill most likely to have
        triggered the respawn.

        Uses a greedy one-pass approach: slots are processed in order and each
        claimed EID is immediately committed so it cannot be taken by later
        slots.

        Only processes slots where BLK deaths exceed EID-resolved deaths, and
        only fills the gap (never exceeds the BLK cap).

        Returns the number of new EID attributions added to *eid_history*.
        """
        if not slot_deaths or not slot_vehicle_timeline:
            return 0

        from src.common.enums.vehicle_type import VehicleType

        _AIR_TYPES = frozenset({VehicleType.FIGHTER, VehicleType.BOMBER, VehicleType.STRIKE_AIRCRAFT})
        _HELI_TYPES = frozenset({VehicleType.ATTACK_HELICOPTER, VehicleType.UTILITY_HELICOPTER})
        _GROUND_NON_AA = frozenset(
            {
                VehicleType.LIGHT_TANK,
                VehicleType.MEDIUM_TANK,
                VehicleType.HEAVY_TANK,
                VehicleType.TANK_DESTROYER,
            }
        )

        def _get_vtype(vehicle_name: str) -> "VehicleType | None":
            if self._vehicle_service is None:
                return None
            v = self._vehicle_service.get_vehicles_by_internal_name(vehicle_name)
            if v is None:
                return None
            return v.vehicle_type

        def _is_air(vehicle_name: str) -> bool:
            vt = _get_vtype(vehicle_name)
            return vt in _AIR_TYPES or vt in _HELI_TYPES

        def _is_ground_non_aa(vehicle_name: str) -> bool:
            return _get_vtype(vehicle_name) in _GROUND_NON_AA

        def tick_of(offset: int) -> int:
            return bisect.bisect_right(tick_offsets, offset) - 1

        # Pre-compute per-slot EID-resolved death counts.
        resolved_deaths_by_slot: dict[int, list[tuple[str, int]]] = {}
        for ev in kill_events:
            entries = eid_history.get(ev.victim_entity_id)
            if not entries:
                continue
            best_entry: tuple[int, str] | None = None
            for off, sl, veh in entries:
                if off <= ev.offset:
                    best_entry = (sl, veh)
                else:
                    break
            if best_entry is None:
                continue
            victim_slot, victim_vehicle = best_entry
            if victim_slot == _INVALID_SLOT or victim_slot == ev.slot:
                continue
            resolved_deaths_by_slot.setdefault(victim_slot, []).append((victim_vehicle, ev.tick_idx))

        slot_resolved_counts: dict[int, int] = {}
        for slot, deaths in resolved_deaths_by_slot.items():
            slot_resolved_counts[slot] = len(deaths)

        # Build list of unresolved kill events sorted by tick.
        # NOTE: M7-ambiguous EIDs (where Method 7 found multiple candidates)
        # are NOT filtered here — they participate in the greedy assignment
        # to preserve the correct cascade order.  Instead, M8's claims for
        # M7-ambiguous EIDs are stripped out AFTER the greedy pass.
        _m7_skip = m7_ambiguous_eids or set()
        unresolved_kills: list[_KillEvent] = []
        for ev in kill_events:
            if ev.victim_entity_id not in eid_history:
                unresolved_kills.append(ev)
        unresolved_kills.sort(key=lambda e: e.tick_idx)

        # Track EIDs claimed during this pass so each EID goes to at most one slot.
        claimed_eids: set[int] = set()

        added = 0

        # ------------------------------------------------------------------
        # Two-pass assignment:
        #
        # Pass 1 — Transition windows (finite span):
        #   Each consecutive TM pair (A@tick_i, B@tick_j) represents exactly
        #   ONE death in vehicle A.  For each window, pick the best candidate
        #   kill event (closest to the window end / respawn tick).  Sort all
        #   proposals by window span (tightest first) and assign greedily.
        #   Ties in span are broken by distance-to-end (closest first).
        #
        # Pass 2 — Final-vehicle windows (open-ended):
        #   For slots that still have remaining death budget and a final
        #   vehicle with no subsequent transition, assign unresolved kills
        #   that occur after the last TM activation.  These are inherently
        #   less certain, so they are processed after all transition windows.
        # ------------------------------------------------------------------

        # Per-slot remaining-deaths budget.
        slot_budget: dict[int, int] = {}
        for slot, timeline in slot_vehicle_timeline.items():
            total_deaths = slot_deaths.get(slot, 0)
            if total_deaths == 0:
                continue
            already_resolved = slot_resolved_counts.get(slot, 0)
            remaining = total_deaths - already_resolved
            if remaining <= 0:
                continue
            slot_budget[slot] = remaining

        # === Pass 1: Transition-window proposals ===
        # _TransProposal: (window_span, dist_to_end, eid, slot, vehicle, tm_offset)
        _TransProposal = tuple[int, int, int, int, str, int]
        trans_proposals: list[_TransProposal] = []

        for slot, timeline in slot_vehicle_timeline.items():
            if slot not in slot_budget:
                continue

            for i in range(len(timeline) - 1):
                tm_offset_curr, vehicle_curr = timeline[i]
                tm_offset_next, _vehicle_next = timeline[i + 1]
                tick_curr = tick_of(tm_offset_curr)
                tick_next = tick_of(tm_offset_next)
                window_span = tick_next - tick_curr

                # Find the best candidate for this window: closest to end.
                best_ev: _KillEvent | None = None
                best_dist: int = window_span + 1
                for ev in unresolved_kills:
                    if ev.tick_idx <= tick_curr:
                        continue
                    if ev.tick_idx > tick_next:
                        break
                    if ev.slot == slot:
                        continue
                    if slot_teams and slot_teams.get(ev.slot) == slot_teams.get(slot):
                        continue
                    if _is_air(vehicle_curr) and _is_ground_non_aa(ev.vehicle_name):
                        continue
                    if _is_ground_non_aa(vehicle_curr) and _is_air(ev.vehicle_name):
                        continue
                    dist = tick_next - ev.tick_idx
                    if dist < best_dist:
                        best_dist = dist
                        best_ev = ev

                if best_ev is not None:
                    trans_proposals.append(
                        (
                            window_span,
                            best_dist,
                            best_ev.victim_entity_id,
                            slot,
                            vehicle_curr,
                            tm_offset_curr,
                        )
                    )

        # Sort by (window_span ASC, dist_to_end ASC) — tightest windows first.
        trans_proposals.sort()

        for window_span, dist_to_end, eid, slot, vehicle, tm_offset in trans_proposals:
            if eid in claimed_eids:
                continue
            budget = slot_budget.get(slot, 0)
            if budget <= 0:
                continue

            new_entry = (tm_offset, slot, vehicle)
            existing = eid_history.get(eid)
            if existing is None:
                eid_history[eid] = [new_entry]
            else:
                existing.append(new_entry)
                existing.sort(key=lambda x: x[0])
            claimed_eids.add(eid)
            slot_budget[slot] = budget - 1
            added += 1
            logger.debug(
                "TM-transition death: EID %d -> slot %d %r (window_span %d, dist_to_end %d)",
                eid,
                slot,
                vehicle,
                window_span,
                dist_to_end,
            )

        # === Pass 2: Final-vehicle windows (open-ended) ===
        # Collect (eid, slot, vehicle, tm_offset) proposals, then sort
        # so that more-constrained slots (lower remaining budget) are
        # processed first — they have fewer options, so their assignments
        # are more likely to be correct.
        remaining_kills: list[_KillEvent] = [ev for ev in unresolved_kills if ev.victim_entity_id not in claimed_eids]

        _FinalProp = tuple[int, int, int, str, int]  # (budget, eid, slot, vehicle, tm_offset)
        final_proposals: list[_FinalProp] = []

        for slot, timeline in slot_vehicle_timeline.items():
            budget = slot_budget.get(slot, 0)
            if budget <= 0 or not timeline:
                continue

            last_tm_offset, last_vehicle = timeline[-1]
            last_tick = tick_of(last_tm_offset)

            for ev in remaining_kills:
                if ev.tick_idx <= last_tick:
                    continue
                if ev.slot == slot:
                    continue
                if slot_teams and slot_teams.get(ev.slot) == slot_teams.get(slot):
                    continue
                if _is_air(last_vehicle) and _is_ground_non_aa(ev.vehicle_name):
                    continue
                if _is_ground_non_aa(last_vehicle) and _is_air(ev.vehicle_name):
                    continue
                final_proposals.append((budget, ev.victim_entity_id, slot, last_vehicle, last_tm_offset))

        # Sort by budget ASC (most-constrained slots first), then by
        # EID (deterministic for same-budget).
        final_proposals.sort(key=lambda p: (p[0], p[1]))

        for budget_at_proposal, eid, slot, vehicle, tm_offset in final_proposals:
            if eid in claimed_eids:
                continue
            budget = slot_budget.get(slot, 0)
            if budget <= 0:
                continue

            new_entry = (tm_offset, slot, vehicle)
            existing = eid_history.get(eid)
            if existing is None:
                eid_history[eid] = [new_entry]
            else:
                existing.append(new_entry)
                existing.sort(key=lambda x: x[0])
            claimed_eids.add(eid)
            slot_budget[slot] = budget - 1
            added += 1
            logger.debug(
                "TM-transition death (final): EID %d -> slot %d %r (after tick %d, budget %d)",
                eid,
                slot,
                vehicle,
                tick_of(tm_offset),
                budget,
            )

        # Post-greedy cleanup: remove M8 claims for EIDs that Method 7
        # flagged as ambiguous.  The greedy pass needed these EIDs in the pool
        # to preserve correct assignment ordering, but the actual M8 assignments
        # for M7-ambiguous EIDs are unreliable (M7's physics evidence is
        # stronger, and M8 may have assigned them to wrong slots).
        if _m7_skip:
            for eid in claimed_eids & _m7_skip:
                entries = eid_history.get(eid)
                if entries is not None:
                    del eid_history[eid]
                    added -= 1

        return added

    def _infer_initial_spawn_eids(
        self,
        eid_history: dict[int, list[tuple[int, int, str]]],
        vehicle_activation_events: list[_TankModelsEvent],
        physics_eid_offsets: "dict[int, list[int]] | None" = None,
    ) -> int:
        """
        Infer missing initial-spawn EID assignments using the per-battle formula
        ``eid = base_eid + slot`` (Method 6).

        War Thunder assigns the first entity ID for each player's initial vehicle
        as ``base_eid + slot``, where ``base_eid`` is the same for all 32 slots
        in a given battle.  Players who never kill anyone before dying will never
        appear as ``killer_entity_id`` in any kill event, so their initial EID is
        absent from *eid_history* (which is populated from killer EIDs only).

        This method:
          1. Detects ``base_eid`` from the most common ``eid - slot`` value among
             existing *eid_history* entries (requires at least 3 confirmations).
          2. For every slot with a ``tankModels`` activation event whose predicted
             EID (``base_eid + slot``) is absent from *eid_history*, inserts a
             synthetic entry anchored at the first tankModels activation offset,
             **provided** the predicted EID has no physics73 events that predate
             that first TM activation (which would indicate the EID was already
             in use by a different entity before this slot spawned).

        Returns the number of new EID attributions added.
        """
        from collections import Counter

        # Step 1: compute base_eid as the mode of (eid - slot) across all
        # existing eid_history entries.  Initial-spawn EIDs form a dense cluster
        # (32 entries all at the same base) while respawn EIDs each have their
        # own unique base, so the mode reliably identifies the initial base.
        base_counter: Counter[int] = Counter()
        for eid, entries in eid_history.items():
            for _, slot, _ in entries:
                if 0 <= slot <= _MAX_SLOT:
                    base_counter[eid - slot] += 1

        if not base_counter:
            return 0

        # Only consider bases high enough to be ground-vehicle EIDs (aircraft
        # EIDs are small, typically < 256, giving low base values).
        _MIN_INITIAL_BASE = 64
        valid_bases = {b: c for b, c in base_counter.items() if b >= _MIN_INITIAL_BASE}
        if not valid_bases:
            return 0

        base_eid = max(valid_bases, key=lambda b: valid_bases[b])
        if valid_bases[base_eid] < 3:  # Require at least 3 confirmations
            return 0

        # Step 2: for each slot with a tankModels first-activation, register the
        # predicted initial EID if it is not already in eid_history.
        slot_first_tm: dict[int, _TankModelsEvent] = {}
        for tm in sorted(vehicle_activation_events, key=lambda e: e.offset):
            if tm.slot not in slot_first_tm:
                slot_first_tm[tm.slot] = tm

        added = 0
        for slot in range(_MAX_SLOT + 1):
            predicted_eid = base_eid + slot
            if predicted_eid in eid_history:
                continue
            tm = slot_first_tm.get(slot)
            if tm is None:
                continue
            # Guard: if this EID already has physics73 events before the first
            # TM activation it was already occupied by a different entity —
            # inserting a wrong attribution here would corrupt later lookups.
            if physics_eid_offsets is not None:
                prior_phys = physics_eid_offsets.get(predicted_eid, [])
                if any(phys_off < tm.offset for phys_off in prior_phys):
                    logger.debug(
                        "Initial-spawn EID %d skipped: physics predate TM for slot %d",
                        predicted_eid,
                        slot,
                    )
                    continue
            eid_history[predicted_eid] = [(tm.offset, slot, tm.vehicle_name)]
            added += 1
            logger.debug(
                "Initial-spawn EID inferred: EID %d → slot %d %r (base=%d)",
                predicted_eid,
                slot,
                tm.vehicle_name,
                base_eid,
            )

        return added

    def _infer_local_player_respawn_eids(
        self,
        eid_history: dict[int, list[tuple[int, int, str]]],
        local_player_eid_sequence: list[tuple[int, int]],
        vehicle_activation_events: list[_TankModelsEvent],
    ) -> int:
        """
        Register all of the replay recorder's respawn EIDs (Method 6b).

        The ``02 58 37 f0`` interaction events always carry the recorder's
        (local player's) current entity ID as ``eid_A``.  Each time ``eid_A``
        changes value, the recorder has respawned with a new entity.

        Algorithm:
          1.  Derive the local player's slot from the *first* ``eid_A`` in
              the sequence using the ``base_eid + slot`` formula already
              established by Method 6.
          2.  For each distinct ``eid_A`` that is not yet in *eid_history*,
              find the most-recent TM activation for the local slot whose
              offset is <= the first appearance of that ``eid_A``.  That TM
              gives us the vehicle name for the new entity.
          3.  Insert ``(offset, slot, vehicle_name)`` into *eid_history*.

        Returns the number of new EID attributions added.
        """
        if not local_player_eid_sequence:
            return 0

        from collections import Counter

        # Step 1: derive base_eid from existing eid_history
        base_counter: Counter[int] = Counter()
        for eid, entries in eid_history.items():
            for _, slot, _ in entries:
                if 0 <= slot <= _MAX_SLOT:
                    base_counter[eid - slot] += 1

        _MIN_INITIAL_BASE = 64
        valid_bases = {b: c for b, c in base_counter.items() if b >= _MIN_INITIAL_BASE}
        if not valid_bases:
            return 0

        base_eid = max(valid_bases, key=lambda b: valid_bases[b])
        if valid_bases[base_eid] < 3:
            return 0

        # Derive local player slot from their first eid_A
        first_eid_a = local_player_eid_sequence[0][1]
        local_slot: int | None = None

        # Check if first_eid_a is an initial EID (base_eid + slot)
        if base_eid <= first_eid_a <= base_eid + _MAX_SLOT:
            local_slot = first_eid_a - base_eid
        else:
            # first_eid_a is a respawn EID; look it up in eid_history
            entries = eid_history.get(first_eid_a)
            if entries:
                local_slot = entries[0][1]

        if local_slot is None:
            return 0

        # Step 2: build TM timeline for local slot
        slot_tms: list[_TankModelsEvent] = sorted(
            [tm for tm in vehicle_activation_events if tm.slot == local_slot],
            key=lambda e: e.offset,
        )

        # Collect distinct eid_a values (preserving first-seen order and offset)
        seen_eids: dict[int, int] = {}  # eid -> first offset
        for offset, eid_a in local_player_eid_sequence:
            if eid_a not in seen_eids:
                seen_eids[eid_a] = offset

        added = 0
        for eid_a, first_offset in seen_eids.items():
            if eid_a in eid_history:
                continue  # already known

            # Find the most-recent TM activation at or before first_offset
            vehicle_name: str | None = None
            for tm in reversed(slot_tms):
                if tm.offset <= first_offset:
                    vehicle_name = tm.vehicle_name
                    break

            if vehicle_name is None:
                continue

            eid_history[eid_a] = [(first_offset, local_slot, vehicle_name)]
            added += 1
            logger.debug(
                "Local-player respawn EID inferred: EID %d → slot %d %r",
                eid_a,
                local_slot,
                vehicle_name,
            )

        return added

    def _parse_kill_events(self, stream_data: bytes) -> list[_KillEvent]:
        """
        Parse all kill events from the stream.

        Structure (from offset of marker):
          [00] [01] [02] [03]  marker              02 58 58 f0
          [04]                 total_length        (u8)
          [05] [06] [07]       00 fe 3f
          [08..11]             player_slot         (u32 LE)
          [12]                 vehicle_name_length (u8)
          [13..13+length-1]    vehicle_name        (ASCII)
          [13+length..+1]      victim_entity_id    (u16 LE)
          [+2..+3]             killer_entity_id    (u16 LE)
          [+4..+7]             FF FF FF FF
          [+8..+10]            3-byte suffix
        """
        events: list[_KillEvent] = []
        search_position = 0
        while True:
            offset = stream_data.find(_KILL_MARKER, search_position)
            if offset == -1:
                break
            search_position = offset + 1

            # Need at least marker(4) + total_length(1) + 3 fixed + slot(4) + vehicle_name_length(1) = 13
            if offset + 13 > len(stream_data):
                continue

            # Fixed bytes check: 00 fe 3f
            if stream_data[offset + 5] != 0x00 or stream_data[offset + 6] != 0xFE or stream_data[offset + 7] != 0x3F:
                continue

            player_slot = struct.unpack("<I", stream_data[offset + 8 : offset + 12])[0]
            if player_slot > _MAX_SLOT:
                continue

            vehicle_name_length = stream_data[offset + 12]
            if vehicle_name_length < 1 or vehicle_name_length > 64:
                continue

            vehicle_name_end = offset + 13 + vehicle_name_length
            if vehicle_name_end + 8 > len(stream_data):
                continue

            vehicle_name_bytes = stream_data[offset + 13 : vehicle_name_end]
            if not all(32 <= b < 127 for b in vehicle_name_bytes):
                continue

            vehicle_name = vehicle_name_bytes.decode("ascii")

            victim_entity_id = struct.unpack("<H", stream_data[vehicle_name_end : vehicle_name_end + 2])[0]
            killer_entity_id = struct.unpack("<H", stream_data[vehicle_name_end + 2 : vehicle_name_end + 4])[0]

            # Sanity: FF FF FF FF should follow immediately
            if stream_data[vehicle_name_end + 4 : vehicle_name_end + 8] != b"\xff\xff\xff\xff":
                continue

            events.append(
                _KillEvent(
                    offset=offset,
                    slot=player_slot,
                    vehicle_name=vehicle_name,
                    victim_entity_id=victim_entity_id,
                    killer_entity_id=killer_entity_id,
                )
            )

        logger.debug(f"Parsed {len(events)} kill events")
        return events

    def _parse_award_events(self, stream_data: bytes) -> list[_AwardEvent]:
        """
        Parse all award events from the stream.

        Structure (from offset of marker):
          [00..03]  marker        02 58 78 f0
          [04]      total_length  (u8)
          [05]      00
          [06]      3e
          [07..10]  player_slot   (u32 LE)
          [11]      name_length   (u8)
          [12..12+length-1]  award_name (ASCII)
          [remainder]  padding + tail (up to total_length bytes from [05])
        """
        events: list[_AwardEvent] = []
        search_position = 0
        while True:
            offset = stream_data.find(_AWARD_MARKER, search_position)
            if offset == -1:
                break
            search_position = offset + 1

            # Need marker(4) + total_length(1) + 00(1) + 3e(1) + slot(4) + name_length(1) = 12
            if offset + 12 > len(stream_data):
                continue

            total_length = stream_data[offset + 4]
            if total_length < 6:
                continue

            if stream_data[offset + 5] != 0x00 or stream_data[offset + 6] != 0x3E:
                continue

            player_slot = struct.unpack("<I", stream_data[offset + 7 : offset + 11])[0]
            if player_slot > _MAX_SLOT:
                continue

            name_length = stream_data[offset + 11]
            if name_length < 1 or name_length > 64:
                continue

            name_bytes_end = offset + 12 + name_length
            if name_bytes_end > len(stream_data):
                continue

            name_bytes = stream_data[offset + 12 : name_bytes_end]
            if not all(32 <= b < 127 for b in name_bytes):
                continue

            award_name = name_bytes.decode("ascii")
            events.append(_AwardEvent(offset=offset, slot=player_slot, award_name=award_name))

        logger.debug(f"Parsed {len(events)} award events")
        return events

    def _parse_late_spawn_events(self, stream_data: bytes) -> list[_LateSpawnEvent]:
        """
        Parse late-spawn / respawn events from the stream.

        These fire for mid-game vehicle switches and respawns (NOT initial spawns).
        Typically ~6 per replay.  They give entity_id -> slot + vehicle_name mappings
        that help attribute a small number of deaths.

        Structure (from offset of marker):
          [00..03]  marker               02 58 56 f0
          [04..05]  total_length         (u16 LE)
          [06]      7e
          [07..08]  entity_id            (u16 LE)
          [09..12]  player_slot          (u32 LE)
          [13]      vehicle_name_length  (u8)
          [14..14+length-1]  vehicle_name (ASCII)
          [FF FF 01 03 70 ...]
        """
        events: list[_LateSpawnEvent] = []
        search_position = 0
        while True:
            offset = stream_data.find(_LATE_SPAWN_MARKER, search_position)
            if offset == -1:
                break
            search_position = offset + 1

            # Need marker(4) + total_length(2) + 7e(1) + entity_id(2) + slot(4) + vehicle_name_length(1) = 14
            if offset + 14 > len(stream_data):
                continue

            if stream_data[offset + 6] != 0x7E:
                continue

            entity_id = struct.unpack("<H", stream_data[offset + 7 : offset + 9])[0]
            player_slot = struct.unpack("<I", stream_data[offset + 9 : offset + 13])[0]
            if player_slot > _MAX_SLOT:
                continue

            vehicle_name_length = stream_data[offset + 13]
            if vehicle_name_length < 1 or vehicle_name_length > 64:
                continue

            name_bytes_end = offset + 14 + vehicle_name_length
            if name_bytes_end > len(stream_data):
                continue

            name_bytes = stream_data[offset + 14 : name_bytes_end]
            if not all(32 <= b < 127 for b in name_bytes):
                continue

            vehicle_name = name_bytes.decode("ascii")
            events.append(
                _LateSpawnEvent(offset=offset, entity_id=entity_id, slot=player_slot, vehicle_name=vehicle_name)
            )

        logger.debug(f"Parsed {len(events)} late-spawn events")
        return events

    def _parse_vehicle_activation_events(self, stream_data: bytes) -> list[_TankModelsEvent]:
        """
        Parse vehicle activation events from the stream.

        Binary format:
            [length_byte][vehicle_path][0x0d][entity_name]

        ``vehicle_path`` is either a bare name (aircraft / heli / naval) or
        prefixed with ``tankModels/`` (ground vehicles).  The prefix is stripped
        so the stored ``vehicle_name`` is always the bare internal name.

        Search anchor: each entity-name immediately follows the ``0x0d``
        separator as ``t1_playerNN_0`` or ``t2_playerNN_0``.  This is a precise
        anchor that rejects false positives from the opaque binary blobs.

        Length cross-check: the byte preceding the printable-ASCII run must
        equal the length of that run.  Mismatches (accidental matches in binary
        data) are discarded.  The backward scan cap of 80 bytes accommodates
        the 11-char ``tankModels/`` prefix plus any realistic vehicle name.
        """
        _PREFIX_LEN = len(_TANKMODELS_PREFIX)  # 11 == len("tankModels/")
        _MAX_NAME_LEN = self._max_vehicle_path_len

        events: list[_TankModelsEvent] = []

        for team_marker in (b"\x0dt1_player", b"\x0dt2_player"):
            pos = 0
            while True:
                sep_offset = stream_data.find(team_marker, pos)
                if sep_offset == -1:
                    break
                pos = sep_offset + 1

                # Parse entity name (alphanumeric + underscore)
                ent_start = sep_offset + 1
                ent_end = ent_start
                while ent_end < len(stream_data) and ent_end - ent_start < 32:
                    b = stream_data[ent_end]
                    if b"a"[0] <= b <= b"z"[0] or b"A"[0] <= b <= b"Z"[0] or b"0"[0] <= b <= b"9"[0] or b == b"_"[0]:
                        ent_end += 1
                    else:
                        break
                entity_name = stream_data[ent_start:ent_end].decode("ascii", errors="ignore")

                player_slot = self._entity_name_to_slot(entity_name)
                if player_slot is None:
                    continue

                # Scan backward from sep_offset for a contiguous printable-ASCII run.
                # The byte immediately before the run is the declared length field.
                scan = sep_offset - 1
                while scan >= 0 and (sep_offset - scan) <= _MAX_NAME_LEN and 32 <= stream_data[scan] < 127:
                    scan -= 1

                raw_name_len = sep_offset - scan - 1
                if raw_name_len < 1 or scan < 0:
                    continue

                if stream_data[scan] != raw_name_len:  # length-byte cross-check
                    continue

                raw_name = stream_data[scan + 1 : sep_offset].decode("ascii")

                # Strip 'tankModels/' prefix present on ground-vehicle paths
                vehicle_name = raw_name[_PREFIX_LEN:] if raw_name.startswith("tankModels/") else raw_name
                if not vehicle_name:
                    continue

                events.append(_TankModelsEvent(offset=scan + 1, slot=player_slot, vehicle_name=vehicle_name))

        events.sort(key=lambda e: e.offset)
        logger.debug("Parsed %d vehicle activation events", len(events))
        return events

    @staticmethod
    def _entity_name_to_slot(entity_name: str) -> Optional[int]:
        """
        Convert a War Thunder entity name to a 0-indexed player slot.

        t1_playerNN_0  ->  slot NN - 1          (team-1 slots  0-15)
        t2_playerNN_0  ->  slot NN - 1 + 16     (team-2 slots 16-31)

        Returns None if the name does not match either pattern.
        """
        if entity_name.startswith("t1_player") and entity_name.endswith("_0"):
            try:
                nn = int(entity_name[9:-2])
                return nn - 1
            except ValueError:
                return None
        if entity_name.startswith("t2_player") and entity_name.endswith("_0"):
            try:
                nn = int(entity_name[9:-2])
                return nn - 1 + 16
            except ValueError:
                return None
        return None
