"""
MPC Message types and serialization

This module defines the message protocol for MPC communication.
Messages are serialized as length-prefixed binary data.
"""

import struct
import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union


class MessageType(IntEnum):
    """Types of MPC messages"""
    # Client -> Server messages
    INPUT_SHARE = 1           # Secret-shared input from client
    CLIENT_READY = 2          # Client is ready for computation

    # Server -> Client messages
    OUTPUT_SHARE = 10         # Output share for reconstruction
    COMPUTATION_COMPLETE = 11 # Computation finished
    ERROR = 12                # Error message

    # Server <-> Server messages
    PREPROCESSING_REQUEST = 20   # Request preprocessing material
    PREPROCESSING_RESPONSE = 21  # Preprocessing material
    BEAVER_TRIPLE = 22           # Beaver triple share
    RANDOM_SHARE = 23            # Random share for masking

    # Protocol messages
    PROTOCOL_MESSAGE = 30     # HoneyBadger protocol message
    RBC_MESSAGE = 31          # Reliable broadcast message

    # Control messages
    HANDSHAKE = 100           # Initial connection handshake
    HANDSHAKE_ACK = 101       # Handshake acknowledgment
    PING = 102                # Keep-alive ping
    PONG = 103                # Keep-alive pong
    DISCONNECT = 104          # Graceful disconnect


@dataclass
class MPCMessage:
    """Base MPC message"""
    msg_type: MessageType
    sender_id: int
    instance_id: int
    payload: bytes = field(default_factory=bytes)

    def to_bytes(self) -> bytes:
        """Serialize message to bytes"""
        # Header: msg_type (1) + sender_id (4) + instance_id (4) + payload_len (4)
        header = struct.pack(
            "!BIII",
            self.msg_type,
            self.sender_id,
            self.instance_id,
            len(self.payload)
        )
        return header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "MPCMessage":
        """Deserialize message from bytes"""
        if len(data) < 13:
            raise ValueError(f"Message too short: {len(data)} bytes")

        msg_type, sender_id, instance_id, payload_len = struct.unpack(
            "!BIII", data[:13]
        )

        if len(data) < 13 + payload_len:
            raise ValueError(
                f"Message payload truncated: expected {payload_len}, got {len(data) - 13}"
            )

        payload = data[13:13 + payload_len]

        return cls(
            msg_type=MessageType(msg_type),
            sender_id=sender_id,
            instance_id=instance_id,
            payload=payload,
        )


@dataclass
class ShareMessage:
    """Message containing a secret share"""
    input_index: int          # Which input this share is for
    share_bytes: bytes        # The actual share data (32 bytes for BLS12-381)
    party_id: int             # Which party this share is for
    threshold: int            # Reconstruction threshold
    is_robust: bool           # Whether this is a robust share

    def to_payload(self) -> bytes:
        """Serialize to message payload"""
        # Fixed header + share bytes
        header = struct.pack(
            "!IIIB",
            self.input_index,
            self.party_id,
            self.threshold,
            1 if self.is_robust else 0,
        )
        return header + self.share_bytes

    @classmethod
    def from_payload(cls, payload: bytes) -> "ShareMessage":
        """Deserialize from message payload"""
        if len(payload) < 13:
            raise ValueError("ShareMessage payload too short")

        input_index, party_id, threshold, is_robust = struct.unpack(
            "!IIIB", payload[:13]
        )
        share_bytes = payload[13:]

        return cls(
            input_index=input_index,
            share_bytes=share_bytes,
            party_id=party_id,
            threshold=threshold,
            is_robust=bool(is_robust),
        )


@dataclass
class OutputShareMessage:
    """Message containing an output share for reconstruction"""
    output_index: int         # Which output this share is for
    share_bytes: bytes        # The share data
    party_id: int             # Which party sent this share

    def to_payload(self) -> bytes:
        """Serialize to message payload"""
        header = struct.pack("!II", self.output_index, self.party_id)
        return header + self.share_bytes

    @classmethod
    def from_payload(cls, payload: bytes) -> "OutputShareMessage":
        """Deserialize from message payload"""
        if len(payload) < 8:
            raise ValueError("OutputShareMessage payload too short")

        output_index, party_id = struct.unpack("!II", payload[:8])
        share_bytes = payload[8:]

        return cls(
            output_index=output_index,
            share_bytes=share_bytes,
            party_id=party_id,
        )


@dataclass
class PreprocessingMessage:
    """Message for preprocessing material exchange"""
    triple_index: int         # Index of this triple/random share
    data_type: str            # "triple" or "random"
    share_bytes: bytes        # The share data

    def to_payload(self) -> bytes:
        """Serialize to message payload"""
        data_type_bytes = self.data_type.encode("utf-8")
        header = struct.pack("!IB", self.triple_index, len(data_type_bytes))
        return header + data_type_bytes + self.share_bytes

    @classmethod
    def from_payload(cls, payload: bytes) -> "PreprocessingMessage":
        """Deserialize from message payload"""
        if len(payload) < 5:
            raise ValueError("PreprocessingMessage payload too short")

        triple_index, type_len = struct.unpack("!IB", payload[:5])
        data_type = payload[5:5 + type_len].decode("utf-8")
        share_bytes = payload[5 + type_len:]

        return cls(
            triple_index=triple_index,
            data_type=data_type,
            share_bytes=share_bytes,
        )


@dataclass
class HandshakeMessage:
    """Initial connection handshake"""
    party_id: int
    is_client: bool
    n_parties: int
    threshold: int
    instance_id: int
    protocol_version: int = 1

    def to_payload(self) -> bytes:
        """Serialize to message payload"""
        return struct.pack(
            "!IBIIII",
            self.party_id,
            1 if self.is_client else 0,
            self.n_parties,
            self.threshold,
            self.instance_id,
            self.protocol_version,
        )

    @classmethod
    def from_payload(cls, payload: bytes) -> "HandshakeMessage":
        """Deserialize from message payload"""
        if len(payload) < 21:
            raise ValueError("HandshakeMessage payload too short")

        party_id, is_client, n_parties, threshold, instance_id, protocol_version = (
            struct.unpack("!IBIIII", payload[:21])
        )

        return cls(
            party_id=party_id,
            is_client=bool(is_client),
            n_parties=n_parties,
            threshold=threshold,
            instance_id=instance_id,
            protocol_version=protocol_version,
        )


def serialize_message(msg: MPCMessage) -> bytes:
    """
    Serialize an MPC message with length prefix

    Format: [length (4 bytes)] [message bytes]
    """
    msg_bytes = msg.to_bytes()
    return struct.pack("!I", len(msg_bytes)) + msg_bytes


def deserialize_message(data: bytes) -> tuple[MPCMessage, int]:
    """
    Deserialize an MPC message from length-prefixed data

    Returns:
        Tuple of (message, bytes_consumed)
    """
    if len(data) < 4:
        raise ValueError("Not enough data for length prefix")

    msg_len = struct.unpack("!I", data[:4])[0]

    if len(data) < 4 + msg_len:
        raise ValueError(f"Not enough data for message: need {msg_len}, have {len(data) - 4}")

    msg = MPCMessage.from_bytes(data[4:4 + msg_len])
    return msg, 4 + msg_len
