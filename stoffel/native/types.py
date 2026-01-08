"""
ctypes structure definitions for Stoffel FFI

Based on: mpc-protocols/mpc/src/ffi/honey_badger_bindings.h

This module defines all the C structures needed to interface with the
native MPC protocols library via ctypes.
"""

import ctypes
from ctypes import Structure, POINTER, c_uint64, c_uint8, c_size_t, c_void_p, c_int
from enum import IntEnum
from typing import List, Optional
from dataclasses import dataclass


# ==============================================================================
# Enums
# ==============================================================================

class FieldKind(IntEnum):
    """Field type - matches FieldKind enum in C"""
    BLS12_381_FR = 0


class ProtocolType(IntEnum):
    """MPC protocol types - matches ProtocolType enum in C"""
    NONE = 0
    RANDOUSHA = 1
    RANSHA = 2
    INPUT = 3
    RBC = 4
    TRIPLE = 5
    BATCH_RECON = 6
    DOUSHA = 7
    MUL = 8


class RbcMessageType(IntEnum):
    """RBC message types - matches RbcMessageType enum in C"""
    BRACHA_INIT = 0
    BRACHA_ECHO = 1
    BRACHA_READY = 2
    BRACHA_UNKNOWN = 3
    AVID_SEND = 4
    AVID_ECHO = 5
    AVID_READY = 6
    AVID_UNKNOWN = 7
    ABA_EST = 8
    ABA_AUX = 9
    ABA_KEY = 10
    ABA_COIN = 11
    ABA_UNKNOWN = 12
    ACS = 13
    ACS_UNKNOWN = 14


# ==============================================================================
# Basic Structures
# ==============================================================================

class U256(Structure):
    """
    256-bit unsigned integer (4 x u64 limbs, little-endian)

    Used for field elements in BLS12-381.
    """
    _fields_ = [
        ("data", c_uint64 * 4),
    ]

    @classmethod
    def from_int(cls, value: int) -> "U256":
        """Create U256 from Python integer"""
        u256 = cls()
        if value < 0:
            value = abs(value)
        data = (c_uint64 * 4)()
        data[0] = value & ((1 << 64) - 1)
        data[1] = (value >> 64) & ((1 << 64) - 1)
        data[2] = (value >> 128) & ((1 << 64) - 1)
        data[3] = (value >> 192) & ((1 << 64) - 1)
        u256.data = data
        return u256

    def to_int(self) -> int:
        """Convert U256 to Python integer"""
        result = 0
        for i in range(4):
            result |= self.data[i] << (64 * i)
        return result


class U256Slice(Structure):
    """Slice of U256 elements"""
    _fields_ = [
        ("pointer", POINTER(U256)),
        ("len", c_size_t),
    ]


class ByteSlice(Structure):
    """
    Slice of bytes

    Used for passing binary data to/from FFI functions.
    """
    _fields_ = [
        ("pointer", POINTER(c_uint8)),
        ("len", c_size_t),
    ]

    @classmethod
    def from_bytes(cls, data: bytes) -> "ByteSlice":
        """Create ByteSlice from Python bytes"""
        byte_array = (c_uint8 * len(data))(*data)
        slice_ = cls()
        slice_.pointer = ctypes.cast(byte_array, POINTER(c_uint8))
        slice_.len = len(data)
        # Keep reference to array to prevent garbage collection
        slice_._buffer = byte_array
        return slice_

    def to_bytes(self) -> bytes:
        """Convert ByteSlice to Python bytes"""
        if not self.pointer or self.len == 0:
            return b""
        return bytes(self.pointer[:self.len])


class UsizeSlice(Structure):
    """Slice of usize values"""
    _fields_ = [
        ("pointer", POINTER(c_size_t)),
        ("len", c_size_t),
    ]


# ==============================================================================
# Opaque Pointer Types (for FFI handles)
# ==============================================================================

class HoneyBadgerMPCClientOpaque(Structure):
    """Opaque handle for HoneyBadger MPC Client"""
    pass


class NetworkOpaque(Structure):
    """Opaque handle for generic network (FakeNetwork or QuicNetworkManager)"""
    pass


class QuicNetworkOpaque(Structure):
    """Opaque handle for QUIC network manager"""
    pass


class QuicPeerConnectionsOpaque(Structure):
    """Opaque handle for QUIC peer connections map"""
    pass


class FakeNetworkReceiversOpaque(Structure):
    """Opaque handle for fake network receivers (testing)"""
    pass


class BrachaOpaque(Structure):
    """Opaque handle for Bracha RBC instance"""
    pass


class AvidOpaque(Structure):
    """Opaque handle for AVID RBC instance"""
    pass


class AbaOpaque(Structure):
    """Opaque handle for ABA consensus instance"""
    pass


class FieldOpaque(Structure):
    """Opaque handle for field element"""
    pass


# ==============================================================================
# Secret Share Structures
# ==============================================================================

class ShamirShare(Structure):
    """
    Shamir secret share

    Fields:
        share: Opaque pointer to the field element
        id: Party ID (1-indexed in Shamir)
        degree: Polynomial degree (threshold)
    """
    _fields_ = [
        ("share", POINTER(FieldOpaque)),
        ("id", c_size_t),
        ("degree", c_size_t),
    ]


class ShamirShareSlice(Structure):
    """Slice of Shamir shares"""
    _fields_ = [
        ("pointer", POINTER(ShamirShare)),
        ("len", c_size_t),
    ]


class RobustShare(Structure):
    """
    Robust secret share (Reed-Solomon error correction)

    Used in HoneyBadger for Byzantine fault tolerance.
    Can detect and correct errors from malicious parties.

    Fields:
        share: Opaque pointer to the field element
        id: Party ID (0-indexed)
        degree: Polynomial degree (threshold)
    """
    _fields_ = [
        ("share", POINTER(FieldOpaque)),
        ("id", c_size_t),
        ("degree", c_size_t),
    ]


class RobustShareSlice(Structure):
    """Slice of robust shares"""
    _fields_ = [
        ("pointer", POINTER(RobustShare)),
        ("len", c_size_t),
    ]


class NonRobustShare(Structure):
    """
    Non-robust secret share (standard Shamir)

    Faster than robust shares but requires honest parties.
    Cannot detect or correct errors.

    Fields:
        share: Opaque pointer to the field element
        id: Party ID (0-indexed)
        degree: Polynomial degree (threshold)
    """
    _fields_ = [
        ("share", POINTER(FieldOpaque)),
        ("id", c_size_t),
        ("degree", c_size_t),
    ]


class NonRobustShareSlice(Structure):
    """Slice of non-robust shares"""
    _fields_ = [
        ("pointer", POINTER(NonRobustShare)),
        ("len", c_size_t),
    ]


# ==============================================================================
# RBC Message Structure
# ==============================================================================

class RbcMsg(Structure):
    """
    Reliable Broadcast message

    Used for Bracha, AVID, and ABA protocols.
    """
    _fields_ = [
        ("sender_id", c_size_t),
        ("session_id", c_uint64),
        ("round_id", c_size_t),
        ("payload", ByteSlice),
        ("metadata", ByteSlice),
        ("msg_type", c_int),  # RbcMessageType
        ("msg_len", c_size_t),
    ]


# ==============================================================================
# Python-friendly Share Wrapper
# ==============================================================================

@dataclass
class Share:
    """
    Python-friendly secret share representation

    This is a pure Python class that holds share data extracted from
    the C FFI structures. It can be serialized and used without
    keeping references to C memory.
    """
    share_bytes: bytes  # 32 bytes for BLS12-381 scalar
    party_id: int
    threshold: int
    share_type: str  # "robust", "non_robust", or "shamir"

    @classmethod
    def from_robust_ffi(cls, c_share: RobustShare, lib: ctypes.CDLL) -> "Share":
        """
        Create from C robust share structure

        Args:
            c_share: The RobustShare structure from FFI
            lib: The loaded MPC library with field_ptr_to_bytes function

        Returns:
            Python Share object with extracted data
        """
        byte_slice = lib.field_ptr_to_bytes(c_share.share, True)  # big-endian
        share_bytes = bytes(byte_slice.pointer[:byte_slice.len])
        lib.free_bytes_slice(byte_slice)
        return cls(
            share_bytes=share_bytes,
            party_id=c_share.id,
            threshold=c_share.degree,
            share_type="robust",
        )

    @classmethod
    def from_non_robust_ffi(cls, c_share: NonRobustShare, lib: ctypes.CDLL) -> "Share":
        """
        Create from C non-robust share structure

        Args:
            c_share: The NonRobustShare structure from FFI
            lib: The loaded MPC library with field_ptr_to_bytes function

        Returns:
            Python Share object with extracted data
        """
        byte_slice = lib.field_ptr_to_bytes(c_share.share, True)  # big-endian
        share_bytes = bytes(byte_slice.pointer[:byte_slice.len])
        lib.free_bytes_slice(byte_slice)
        return cls(
            share_bytes=share_bytes,
            party_id=c_share.id,
            threshold=c_share.degree,
            share_type="non_robust",
        )

    @classmethod
    def from_shamir_ffi(cls, c_share: ShamirShare, lib: ctypes.CDLL) -> "Share":
        """
        Create from C Shamir share structure

        Args:
            c_share: The ShamirShare structure from FFI
            lib: The loaded MPC library with field_ptr_to_bytes function

        Returns:
            Python Share object with extracted data
        """
        byte_slice = lib.field_ptr_to_bytes(c_share.share, True)  # big-endian
        share_bytes = bytes(byte_slice.pointer[:byte_slice.len])
        lib.free_bytes_slice(byte_slice)
        return cls(
            share_bytes=share_bytes,
            party_id=c_share.id,
            threshold=c_share.degree,
            share_type="shamir",
        )
