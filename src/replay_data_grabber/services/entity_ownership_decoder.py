"""Decode player ownership from replay entity construction packets."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_UID_HASH = 0x5CC7E6CD
_PLAYER_ID_HASH = 0xF3D0556D
_CLASS_NAME_HASH = 0x1E9A352C
_TRANSFORM_HASH = 0xE1AD931B

_TYPE_HASHES = {
    "bool": 0xC894953D,
    "float": 0xA6C45D85,
    "int": 0x95E97E5E,
    "uint8_t": 0x306340A8,
    "uint16_t": 0x96C45519,
    "uint32_t": 0xE9B20787,
    "uint64_t": 0x682FE470,
    "int8_t": 0x40FFA2F9,
    "int16_t": 0xDFE5EDA,
    "int64_t": 0x7270198F,
    "ecs::string": 0x33E97A7B,
    "ecs::EntityId": 0xFECA5ED4,
    "dm::PartIdList": 0x53533A06,
    "ecs::UInt8List": 0x237E95BE,
    "ecs::UInt16List": 0x182F3BAD,
    "ecs::UInt32List": 0xF2FB5CB7,
    "ecs::UInt64List": 0x142BA07C,
    "ecs::Int8List": 0x2CDF7CC5,
    "ecs::Int16List": 0x58B90BE0,
    "ecs::IntList": 0x9A82F7C3,
    "ecs::Int64List": 0xBCF92C85,
    "ecs::FloatList": 0xBC46E168,
    "ecs::BoolList": 0xB408E03A,
    "ecs::Point2List": 0xB5AC176E,
    "ecs::Point3List": 0x6CA87641,
    "ecs::Point4List": 0x52B4ADC8,
    "ecs::IPoint2List": 0x73C76A29,
    "ecs::IPoint3List": 0x6D3A38B6,
    "ecs::IPoint4List": 0x133B98A3,
    "ecs::TMatrixList": 0xF7779277,
    "ecs::ColorList": 0x6DA69091,
    "ecs::EidList": 0x5A0BA408,
    "ecs::StringList": 0x885BBE83,
    "ecs::Array": 0x0F66BD43,
    "ecs::Object": 0x1D20BA79,
    "Point2": 0x6AF041B9,
    "Point3": 0x69F04026,
    "Point4": 0x6CF044DF,
    "IPoint2": 0x4863D138,
    "IPoint3": 0x4963D2CB,
    "IPoint4": 0x4E63DAAA,
    "TMatrix": 0xA27250C6,
    "E3DCOLOR": 0xA249C4A6,
}

_STORAGE_TYPE_HASHES = {
    0xA357DB48,
    0x3964D2ED,
    0x59E1F730,
    0xE758925C,
    0x8189015A,
    0xE858641D,
    0xC1CFAD49,
    0x47C321EA,
    0x841F80CE,
}

_LIST_ELEMENT_WIDTHS = {
    _TYPE_HASHES["ecs::UInt8List"]: 8,
    _TYPE_HASHES["ecs::UInt16List"]: 16,
    _TYPE_HASHES["ecs::UInt32List"]: 32,
    _TYPE_HASHES["ecs::UInt64List"]: 64,
    _TYPE_HASHES["ecs::Int8List"]: 8,
    _TYPE_HASHES["ecs::Int16List"]: 16,
    _TYPE_HASHES["ecs::IntList"]: 32,
    _TYPE_HASHES["ecs::Int64List"]: 64,
    _TYPE_HASHES["ecs::FloatList"]: 32,
    _TYPE_HASHES["ecs::Point2List"]: 64,
    _TYPE_HASHES["ecs::Point3List"]: 96,
    _TYPE_HASHES["ecs::Point4List"]: 128,
    _TYPE_HASHES["ecs::IPoint2List"]: 64,
    _TYPE_HASHES["ecs::IPoint3List"]: 96,
    _TYPE_HASHES["ecs::IPoint4List"]: 128,
    _TYPE_HASHES["ecs::TMatrixList"]: 384,
    _TYPE_HASHES["ecs::ColorList"]: 32,
}

_MAX_PACKET_SIZE = 16 * 1024 * 1024
_MAX_ENTITY_BLOCK_SIZE = 4 * 1024 * 1024
_MAX_DECOMPRESSED_PACKET_SIZE = 8 * 1024 * 1024
_MAX_COMPONENT_COUNT = 4096
_MAX_STRING_SIZE = 4096


class ECSDecodeError(ValueError):
    """Malformed or unsupported ECS data encountered in a replay stream."""


class _UnsupportedECSComponent(ECSDecodeError):
    """A valid component whose wire format is outside this focused decoder."""


@dataclass(frozen=True)
class EntityOwnership:
    """Player and vehicle identity attached to one ECS UID at a stream offset."""

    offset: int
    uid: int
    player_id: int
    vehicle_name: str | None


class _BitReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.position = 0

    def read_bits(self, count: int) -> int:
        if count < 0 or self.position + count > len(self.data) * 8:
            raise ECSDecodeError("ECS bitstream ended unexpectedly")
        value = 0
        for _ in range(count):
            value = (value << 1) | ((self.data[self.position >> 3] >> (7 - (self.position & 7))) & 1)
            self.position += 1
        return value

    def skip_bits(self, count: int) -> None:
        if count < 0 or self.position + count > len(self.data) * 8:
            raise ECSDecodeError("ECS bitstream ended unexpectedly")
        self.position += count

    def read_bytes(self, count: int) -> bytes:
        if count < 0 or count > _MAX_ENTITY_BLOCK_SIZE or self.position + count * 8 > len(self.data) * 8:
            raise ECSDecodeError("ECS byte field exceeds its enclosing block")
        return bytes(self.read_bits(8) for _ in range(count))

    def read_u8(self) -> int:
        return self.read_bits(8)

    def read_u16(self) -> int:
        return int.from_bytes(self.read_bytes(2), "little")

    def read_u32(self) -> int:
        return int.from_bytes(self.read_bytes(4), "little")

    def read_compressed(self) -> int:
        value = 0
        shift = 0
        for _ in range(10):
            byte = self.read_u8()
            value |= (byte & 0x7F) << shift
            if byte < 0x80:
                return value
            shift += 7
        raise ECSDecodeError("ECS variable-length integer is too long")

    def read_cstring(self) -> str:
        data = bytearray()
        while len(data) <= _MAX_STRING_SIZE:
            byte = self.read_u8()
            if byte == 0:
                return data.decode("utf-8", errors="replace")
            data.append(byte)
        raise ECSDecodeError("ECS string exceeds its size limit")

    def read_sized_string(self) -> str:
        length = self.read_u8()
        if length > _MAX_STRING_SIZE:
            raise ECSDecodeError("ECS template name exceeds its size limit")
        return self.read_bytes(length).decode("utf-8", errors="replace")


def decode_entity_ownership(stream_data: bytes) -> dict[int, list[EntityOwnership]]:
    """Read `uid -> unit__playerId` mappings from bounded ECS construction packets."""
    templates: dict[int, tuple[str, list[int]]] = {}
    component_definitions: dict[int, tuple[int, int]] = {}
    ownership: dict[int, list[EntityOwnership]] = {}
    malformed_packets = Counter()
    malformed_entities = Counter()
    unsupported_entities = Counter()
    position = 0

    while position < len(stream_data):
        packet_start = position
        try:
            packet_size, payload_start = _read_packet_size(stream_data, position)
        except ECSDecodeError as exc:
            logger.warning("Stopped ECS ownership scan at stream offset %d: %s", packet_start, exc)
            break
        packet_end = payload_start + packet_size
        if packet_size == 0 or packet_size > _MAX_PACKET_SIZE or packet_end > len(stream_data):
            logger.warning("Stopped ECS ownership scan at invalid packet size at offset %d", packet_start)
            break
        if payload_start >= packet_end:
            logger.warning("Stopped ECS ownership scan at empty packet at offset %d", packet_start)
            break

        header_byte = stream_data[payload_start]
        packet_type = header_byte ^ 0x10 if header_byte & 0x10 else header_byte
        header_size = 2 if header_byte & 0x10 else 6
        payload_start += header_size
        if payload_start > packet_end:
            logger.warning("Stopped ECS ownership scan at truncated packet header at offset %d", packet_start)
            break

        if packet_type == 6 and payload_start < packet_end:
            control = stream_data[payload_start]
            if control in (0x24, 0x25):
                try:
                    body = stream_data[payload_start + 1 : packet_end]
                    if control == 0x25:
                        body = _decompress_lz4_block(body)
                    _parse_construction_packet(
                        body,
                        payload_start + 1 if control == 0x24 else packet_start,
                        packet_start,
                        control == 0x24,
                        templates,
                        component_definitions,
                        ownership,
                        malformed_entities,
                        unsupported_entities,
                    )
                except ECSDecodeError as exc:
                    malformed_packets[str(exc)] += 1

        position = packet_end

    if malformed_packets:
        logger.warning(
            "Skipped %d malformed/unsupported ECS construction packets (%s)",
            sum(malformed_packets.values()),
            ", ".join(f"{reason}: {count}" for reason, count in malformed_packets.most_common(4)),
        )
    if malformed_entities:
        logger.warning(
            "Skipped %d malformed ECS entity blocks (%s)",
            sum(malformed_entities.values()),
            ", ".join(f"{reason}: {count}" for reason, count in malformed_entities.most_common(4)),
        )
    if unsupported_entities:
        logger.debug(
            "Skipped %d ECS entities with unsupported component types (%s)",
            sum(unsupported_entities.values()),
            ", ".join(f"{reason}: {count}" for reason, count in unsupported_entities.most_common(4)),
        )
    logger.debug("Decoded ECS ownership for %d UIDs", len(ownership))
    return ownership


def _read_packet_size(data: bytes, position: int) -> tuple[int, int]:
    if position >= len(data):
        raise ECSDecodeError("Missing packet size")
    first = data[position]
    position += 1
    if first & 0x80:
        return first & 0x7F, position
    if first & 0x40:
        if position >= len(data):
            raise ECSDecodeError("Truncated two-byte packet size")
        return (((first << 8) | data[position]) ^ 0x4000), position + 1
    if first & 0x20:
        if position + 2 > len(data):
            raise ECSDecodeError("Truncated three-byte packet size")
        size = (first << 16) | (data[position] << 8) | data[position + 1]
        return size ^ 0x200000, position + 2
    if first & 0x10:
        if position + 3 > len(data):
            raise ECSDecodeError("Truncated four-byte packet size")
        size = (first << 24) | (data[position] << 16) | (data[position + 1] << 8) | data[position + 2]
        return size ^ 0x10000000, position + 3
    if position + 4 > len(data):
        raise ECSDecodeError("Truncated five-byte packet size")
    return int.from_bytes(data[position : position + 4], "little"), position + 4


def _decompress_lz4_block(data: bytes) -> bytes:
    output = bytearray()
    position = 0

    while position < len(data):
        token = data[position]
        position += 1
        literal_length = token >> 4
        if literal_length == 15:
            literal_length, position = _read_lz4_length(data, position, literal_length)
        if position + literal_length > len(data):
            raise ECSDecodeError("Truncated LZ4 literal run")
        if len(output) + literal_length > _MAX_DECOMPRESSED_PACKET_SIZE:
            raise ECSDecodeError("LZ4 output exceeds its size limit")
        output.extend(data[position : position + literal_length])
        position += literal_length

        if position == len(data):
            break
        if position + 2 > len(data):
            raise ECSDecodeError("Truncated LZ4 match offset")
        match_offset = data[position] | (data[position + 1] << 8)
        position += 2
        if match_offset == 0 or match_offset > len(output):
            raise ECSDecodeError("Invalid LZ4 match offset")

        match_length = (token & 0x0F) + 4
        if (token & 0x0F) == 0x0F:
            match_length, position = _read_lz4_length(data, position, match_length)
        if len(output) + match_length > _MAX_DECOMPRESSED_PACKET_SIZE:
            raise ECSDecodeError("LZ4 output exceeds its size limit")
        for _ in range(match_length):
            output.append(output[-match_offset])

    return bytes(output)


def _read_lz4_length(data: bytes, position: int, length: int) -> tuple[int, int]:
    while True:
        if position >= len(data):
            raise ECSDecodeError("Truncated LZ4 length")
        extension = data[position]
        position += 1
        length += extension
        if extension < 0xFF:
            return length, position


def _parse_construction_packet(
    body: bytes,
    body_stream_offset: int,
    packet_start: int,
    exact_body_offset: bool,
    templates: dict[int, tuple[str, list[int]]],
    component_definitions: dict[int, tuple[int, int]],
    ownership: dict[int, list[EntityOwnership]],
    malformed_entities: Counter[str],
    unsupported_entities: Counter[str],
) -> None:
    reader = _BitReader(body)
    entity_count = reader.read_u8() + 1
    if entity_count > 256:
        raise ECSDecodeError("ECS construction entity count exceeds its size limit")

    for _ in range(entity_count):
        entity_offset = body_stream_offset + reader.position // 8 if exact_body_offset else packet_start
        _read_entity_id(reader)
        block_size = reader.read_compressed()
        if block_size > _MAX_ENTITY_BLOCK_SIZE:
            raise ECSDecodeError("ECS entity block exceeds its size limit")
        block = reader.read_bytes(block_size)
        try:
            decoded = _parse_entity_block(block, templates, component_definitions)
        except _UnsupportedECSComponent as exc:
            unsupported_entities[str(exc)] += 1
            continue
        except ECSDecodeError as exc:
            malformed_entities[str(exc)] += 1
            continue
        if decoded is None:
            continue

        uid, player_id, vehicle_name = decoded
        if uid < 0 or uid >= 0x800 or player_id < 0 or player_id > 63:
            continue
        ownership.setdefault(uid, []).append(
            EntityOwnership(
                offset=max(packet_start, entity_offset),
                uid=uid,
                player_id=player_id,
                vehicle_name=vehicle_name,
            )
        )


def _parse_entity_block(
    block: bytes,
    templates: dict[int, tuple[str, list[int]]],
    component_definitions: dict[int, tuple[int, int]],
) -> tuple[int, int, str | None] | None:
    reader = _BitReader(block)
    template_id = reader.read_compressed()
    template = templates.get(template_id)
    if template is None:
        template_name = reader.read_sized_string()
        component_count = reader.read_u16()
        if component_count > _MAX_COMPONENT_COUNT:
            raise ECSDecodeError("ECS template component count exceeds its size limit")
        component_ids = []
        for _ in range(component_count):
            component_id = reader.read_compressed()
            component_ids.append(component_id)
            if component_id not in component_definitions:
                component_definitions[component_id] = (reader.read_u32(), reader.read_u32())
        template = (template_name, component_ids)
        templates[template_id] = template

    template_name, component_ids = template
    value_count = reader.read_u8() if len(component_ids) < 256 else reader.read_compressed()
    if value_count > len(component_ids):
        raise ECSDecodeError("ECS entity component count exceeds its template")

    component_index = 0
    uid: int | None = None
    player_id: int | None = None
    vehicle_name: str | None = None

    for value_index in range(value_count):
        delta = reader.read_u8() if len(component_ids) < 256 else reader.read_compressed()
        component_index = delta if value_index == 0 else component_index + delta + 1
        if component_index >= len(component_ids):
            raise ECSDecodeError(f"ECS component index exceeds template {template_name!r}")

        component_id = component_ids[component_index]
        definition = component_definitions.get(component_id)
        if definition is None:
            raise ECSDecodeError("Missing ECS component definition")
        data_hash, type_hash = definition

        if data_hash == _UID_HASH:
            uid_value = _read_component_value(reader, type_hash, data_hash)
            uid = uid_value if isinstance(uid_value, int) else None
        elif data_hash == _PLAYER_ID_HASH:
            player_id_value = _read_component_value(reader, type_hash, data_hash)
            player_id = player_id_value if isinstance(player_id_value, int) else None
        elif data_hash == _CLASS_NAME_HASH:
            vehicle_name = _read_component_value(reader, type_hash, data_hash)
            if vehicle_name and vehicle_name.startswith("tankModels/"):
                vehicle_name = vehicle_name.removeprefix("tankModels/")
        else:
            _read_component_value(reader, type_hash, data_hash)

        if uid is not None and player_id is not None:
            return uid, player_id, vehicle_name

    return None


def _read_component_value(reader: _BitReader, type_hash: int, data_hash: int) -> int | str | None:
    if data_hash == _TRANSFORM_HASH:
        if reader.read_bits(1):
            reader.skip_bits(62)
            if reader.read_bits(1):
                reader.skip_bits(32)
        else:
            reader.skip_bits(4 * 9 * 8)
        reader.skip_bits(4 * 3 * 8)
        return None

    if type_hash in _STORAGE_TYPE_HASHES:
        reader.skip_bits(reader.read_compressed())
        return None

    if type_hash == _TYPE_HASHES["dm::PartIdList"]:
        reader.skip_bits(reader.read_compressed() * 8 * 6)
        return None

    if type_hash == _TYPE_HASHES["bool"]:
        return reader.read_bits(1)
    if type_hash == _TYPE_HASHES["ecs::string"]:
        return reader.read_cstring()
    if type_hash == _TYPE_HASHES["ecs::EntityId"]:
        return _read_entity_id(reader)

    primitive_widths = {
        _TYPE_HASHES["float"]: 32,
        _TYPE_HASHES["int"]: 32,
        _TYPE_HASHES["uint8_t"]: 8,
        _TYPE_HASHES["uint16_t"]: 16,
        _TYPE_HASHES["uint32_t"]: 32,
        _TYPE_HASHES["uint64_t"]: 64,
        _TYPE_HASHES["int8_t"]: 8,
        _TYPE_HASHES["int16_t"]: 16,
        _TYPE_HASHES["int64_t"]: 64,
        _TYPE_HASHES["Point2"]: 64,
        _TYPE_HASHES["Point3"]: 96,
        _TYPE_HASHES["Point4"]: 128,
        _TYPE_HASHES["IPoint2"]: 64,
        _TYPE_HASHES["IPoint3"]: 96,
        _TYPE_HASHES["IPoint4"]: 128,
        _TYPE_HASHES["TMatrix"]: 384,
        _TYPE_HASHES["E3DCOLOR"]: 32,
    }
    if type_hash in primitive_widths:
        width = primitive_widths[type_hash]
        raw = reader.read_bytes(width // 8) if width % 8 == 0 else b""
        if width % 8:
            reader.skip_bits(width)
        if type_hash == _TYPE_HASHES["int"]:
            return int.from_bytes(raw, "little", signed=True)
        if type_hash == _TYPE_HASHES["uint8_t"]:
            return raw[0]
        if type_hash == _TYPE_HASHES["uint16_t"]:
            return int.from_bytes(raw, "little")
        if type_hash == _TYPE_HASHES["uint32_t"]:
            return int.from_bytes(raw, "little")
        if type_hash == _TYPE_HASHES["uint64_t"]:
            return int.from_bytes(raw, "little")
        if type_hash == _TYPE_HASHES["int8_t"]:
            return int.from_bytes(raw, "little", signed=True)
        if type_hash == _TYPE_HASHES["int16_t"]:
            return int.from_bytes(raw, "little", signed=True)
        if type_hash == _TYPE_HASHES["int64_t"]:
            return int.from_bytes(raw, "little", signed=True)
        return None

    if type_hash in _LIST_ELEMENT_WIDTHS:
        count = reader.read_compressed()
        reader.skip_bits(count * _LIST_ELEMENT_WIDTHS[type_hash])
        return None
    if type_hash == _TYPE_HASHES["ecs::BoolList"]:
        reader.skip_bits(reader.read_compressed())
        return None
    if type_hash == _TYPE_HASHES["ecs::StringList"]:
        for _ in range(reader.read_compressed()):
            reader.read_cstring()
        return None
    if type_hash == _TYPE_HASHES["ecs::EidList"]:
        for _ in range(reader.read_compressed()):
            _read_entity_id(reader)
        return None

    raise _UnsupportedECSComponent(f"Unsupported ECS component type hash {type_hash:#x}")


def _read_entity_id(reader: _BitReader) -> int:
    first = reader.read_u16()
    if first & 1:
        return (first >> 2) | (((first & 2) >> 1) << 22)
    if first & 2:
        return (first >> 2) | (reader.read_u8() << 22)
    combined = (reader.read_u16() << 16) | first
    return ((combined & 0xFFFFFF) >> 2) | ((combined >> 24) << 22)
