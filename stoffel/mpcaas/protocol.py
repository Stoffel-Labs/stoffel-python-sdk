"""
MPCaaS Protocol Messages

Defines message types and serialization for MPCaaS client-server communication.
Wire format is compatible with Rust SDK's protocol.rs.

Format: [MAGIC:4][VERSION:1][LENGTH:4][PAYLOAD:LENGTH]
MAGIC = b"MPCS" (0x4D, 0x50, 0x43, 0x53)
VERSION = 1
PAYLOAD = bincode-compatible serialized message

Bincode serialization notes:
- Enum variants use u32 index (little-endian)
- Struct fields serialized in definition order
- Strings: u64 length (little-endian) + UTF-8 bytes
- Integers: little-endian
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Tuple, Union, List


# Protocol constants
MPCAAS_MAGIC = bytes([0x4D, 0x50, 0x43, 0x53])  # "MPCS"
PROTOCOL_VERSION = 1


class ErrorCode(IntEnum):
    """Error codes for MPCaaS protocol errors"""
    INVALID_MESSAGE = 0
    CONFIGURATION_MISMATCH = 1
    TOO_MANY_CLIENTS = 2
    NOT_READY = 3
    TIMEOUT = 4
    INTERNAL_ERROR = 5
    CLIENT_DISCONNECTED = 6
    PREPROCESSING_EXHAUSTED = 7


@dataclass
class ServerInfo:
    """Server information sent after client connects"""
    n_parties: int
    threshold: int
    instance_id: int
    party_id: int


@dataclass
class ClientReady:
    """Client announces readiness with input count"""
    client_id: int
    num_inputs: int


@dataclass
class ComputationTrigger:
    """Trigger computation (sent by coordinating party)"""
    session_id: int


@dataclass
class ComputationComplete:
    """Computation complete notification"""
    session_id: int


@dataclass
class HoneyBadgerPayload:
    """Wrapped HoneyBadger protocol message"""
    data: bytes


@dataclass
class ErrorMessage:
    """Error message"""
    code: ErrorCode
    message: str


@dataclass
class Ping:
    """Heartbeat/keepalive"""
    pass


@dataclass
class Pong:
    """Heartbeat response"""
    pass


# Union type for all message types
MPCaaSMessage = Union[
    ServerInfo,
    ClientReady,
    ComputationTrigger,
    ComputationComplete,
    HoneyBadgerPayload,
    ErrorMessage,
    Ping,
    Pong,
]


# Message variant indices (matches Rust enum order)
class MessageVariant(IntEnum):
    SERVER_INFO = 0
    CLIENT_READY = 1
    COMPUTATION_TRIGGER = 2
    COMPUTATION_COMPLETE = 3
    HONEY_BADGER = 4
    ERROR = 5
    PING = 6
    PONG = 7


def _serialize_usize(value: int) -> bytes:
    """Serialize usize (u64 on 64-bit) in little-endian"""
    return struct.pack('<Q', value)


def _serialize_u64(value: int) -> bytes:
    """Serialize u64 in little-endian"""
    return struct.pack('<Q', value)


def _serialize_u32(value: int) -> bytes:
    """Serialize u32 in little-endian"""
    return struct.pack('<I', value)


def _serialize_string(s: str) -> bytes:
    """Serialize string (bincode format: u64 length + UTF-8 bytes)"""
    encoded = s.encode('utf-8')
    return struct.pack('<Q', len(encoded)) + encoded


def _serialize_bytes(data: bytes) -> bytes:
    """Serialize byte slice (bincode format: u64 length + bytes)"""
    return struct.pack('<Q', len(data)) + data


def _deserialize_usize(data: bytes, offset: int) -> Tuple[int, int]:
    """Deserialize usize from bytes, return (value, new_offset)"""
    value = struct.unpack_from('<Q', data, offset)[0]
    return value, offset + 8


def _deserialize_u64(data: bytes, offset: int) -> Tuple[int, int]:
    """Deserialize u64 from bytes, return (value, new_offset)"""
    value = struct.unpack_from('<Q', data, offset)[0]
    return value, offset + 8


def _deserialize_u32(data: bytes, offset: int) -> Tuple[int, int]:
    """Deserialize u32 from bytes, return (value, new_offset)"""
    value = struct.unpack_from('<I', data, offset)[0]
    return value, offset + 4


def _deserialize_string(data: bytes, offset: int) -> Tuple[str, int]:
    """Deserialize string from bytes, return (value, new_offset)"""
    length, offset = _deserialize_u64(data, offset)
    s = data[offset:offset + length].decode('utf-8')
    return s, offset + length


def _deserialize_bytes(data: bytes, offset: int) -> Tuple[bytes, int]:
    """Deserialize byte slice from bytes, return (value, new_offset)"""
    length, offset = _deserialize_u64(data, offset)
    b = data[offset:offset + length]
    return b, offset + length


def _serialize_payload(msg: MPCaaSMessage) -> bytes:
    """Serialize message payload (bincode format)"""
    if isinstance(msg, ServerInfo):
        return (
            _serialize_u32(MessageVariant.SERVER_INFO) +
            _serialize_usize(msg.n_parties) +
            _serialize_usize(msg.threshold) +
            _serialize_u64(msg.instance_id) +
            _serialize_usize(msg.party_id)
        )
    elif isinstance(msg, ClientReady):
        return (
            _serialize_u32(MessageVariant.CLIENT_READY) +
            _serialize_usize(msg.client_id) +
            _serialize_usize(msg.num_inputs)
        )
    elif isinstance(msg, ComputationTrigger):
        return (
            _serialize_u32(MessageVariant.COMPUTATION_TRIGGER) +
            _serialize_u64(msg.session_id)
        )
    elif isinstance(msg, ComputationComplete):
        return (
            _serialize_u32(MessageVariant.COMPUTATION_COMPLETE) +
            _serialize_u64(msg.session_id)
        )
    elif isinstance(msg, HoneyBadgerPayload):
        return (
            _serialize_u32(MessageVariant.HONEY_BADGER) +
            _serialize_bytes(msg.data)
        )
    elif isinstance(msg, ErrorMessage):
        return (
            _serialize_u32(MessageVariant.ERROR) +
            _serialize_u32(msg.code) +
            _serialize_string(msg.message)
        )
    elif isinstance(msg, Ping):
        return _serialize_u32(MessageVariant.PING)
    elif isinstance(msg, Pong):
        return _serialize_u32(MessageVariant.PONG)
    else:
        raise ValueError(f"Unknown message type: {type(msg)}")


def _deserialize_payload(data: bytes) -> MPCaaSMessage:
    """Deserialize message payload (bincode format)"""
    if len(data) < 4:
        raise ValueError("Payload too short for variant index")

    variant, offset = _deserialize_u32(data, 0)

    if variant == MessageVariant.SERVER_INFO:
        n_parties, offset = _deserialize_usize(data, offset)
        threshold, offset = _deserialize_usize(data, offset)
        instance_id, offset = _deserialize_u64(data, offset)
        party_id, offset = _deserialize_usize(data, offset)
        return ServerInfo(n_parties, threshold, instance_id, party_id)

    elif variant == MessageVariant.CLIENT_READY:
        client_id, offset = _deserialize_usize(data, offset)
        num_inputs, offset = _deserialize_usize(data, offset)
        return ClientReady(client_id, num_inputs)

    elif variant == MessageVariant.COMPUTATION_TRIGGER:
        session_id, offset = _deserialize_u64(data, offset)
        return ComputationTrigger(session_id)

    elif variant == MessageVariant.COMPUTATION_COMPLETE:
        session_id, offset = _deserialize_u64(data, offset)
        return ComputationComplete(session_id)

    elif variant == MessageVariant.HONEY_BADGER:
        payload, offset = _deserialize_bytes(data, offset)
        return HoneyBadgerPayload(payload)

    elif variant == MessageVariant.ERROR:
        code, offset = _deserialize_u32(data, offset)
        message, offset = _deserialize_string(data, offset)
        return ErrorMessage(ErrorCode(code), message)

    elif variant == MessageVariant.PING:
        return Ping()

    elif variant == MessageVariant.PONG:
        return Pong()

    else:
        raise ValueError(f"Unknown message variant: {variant}")


def serialize_message(msg: MPCaaSMessage) -> bytes:
    """
    Serialize an MPCaaS message for transport

    Format: [MAGIC:4][VERSION:1][LENGTH:4][PAYLOAD:LENGTH]

    Args:
        msg: Message to serialize

    Returns:
        Serialized bytes ready for transport
    """
    payload = _serialize_payload(msg)
    length = len(payload)

    result = bytearray()
    result.extend(MPCAAS_MAGIC)
    result.append(PROTOCOL_VERSION)
    result.extend(struct.pack('>I', length))  # Big-endian length (matches Rust)
    result.extend(payload)

    return bytes(result)


def deserialize_message(data: bytes) -> Tuple[MPCaaSMessage, int]:
    """
    Deserialize an MPCaaS message from transport bytes

    Args:
        data: Raw bytes from transport

    Returns:
        Tuple of (parsed message, number of bytes consumed)

    Raises:
        ValueError: If message is invalid or incomplete
    """
    # Minimum size: magic (4) + version (1) + length (4) = 9 bytes
    if len(data) < 9:
        raise ValueError("Message too short")

    # Check magic bytes
    if data[0:4] != MPCAAS_MAGIC:
        raise ValueError("Invalid MPCaaS magic bytes")

    # Check version
    version = data[4]
    if version != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version: {version} (expected {PROTOCOL_VERSION})")

    # Read length (big-endian)
    length = struct.unpack('>I', data[5:9])[0]

    # Check we have enough data
    total_size = 9 + length
    if len(data) < total_size:
        raise ValueError(f"Incomplete message: expected {total_size} bytes, got {len(data)}")

    # Deserialize payload
    payload = data[9:total_size]
    msg = _deserialize_payload(payload)

    return msg, total_size


class MessageBuffer:
    """
    Message buffer for handling partial reads

    QUIC may deliver data in chunks, so we need to buffer until
    we have a complete message.

    Example:
        buffer = MessageBuffer()

        # Receive partial data
        buffer.append(partial_data_1)
        msg = buffer.try_parse()  # Returns None if incomplete

        # Receive more data
        buffer.append(partial_data_2)
        msg = buffer.try_parse()  # Returns message if complete
    """

    def __init__(self):
        self._buffer = bytearray()

    def append(self, data: bytes) -> None:
        """Append data to the buffer"""
        self._buffer.extend(data)

    def try_parse(self) -> Optional[MPCaaSMessage]:
        """
        Try to extract a complete message from the buffer

        Returns:
            Message if complete, None if more data is needed

        Raises:
            ValueError: If protocol error (invalid magic, etc.)
        """
        if len(self._buffer) < 9:
            return None

        # Check magic bytes
        if self._buffer[0:4] != MPCAAS_MAGIC:
            self._buffer.clear()
            raise ValueError("Invalid MPCaaS magic bytes")

        # Read length
        length = struct.unpack('>I', bytes(self._buffer[5:9]))[0]

        total_size = 9 + length
        if len(self._buffer) < total_size:
            return None

        # Parse and consume the message
        try:
            msg, consumed = deserialize_message(bytes(self._buffer))
            del self._buffer[:consumed]
            return msg
        except ValueError:
            self._buffer.clear()
            raise

    def clear(self) -> None:
        """Clear the buffer"""
        self._buffer.clear()

    def is_empty(self) -> bool:
        """Check if buffer is empty"""
        return len(self._buffer) == 0

    def __len__(self) -> int:
        """Get current buffer size"""
        return len(self._buffer)
