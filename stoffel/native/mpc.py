"""
Native MPC bindings using ctypes

Provides direct access to the MPC protocols (secret sharing) via C FFI.
Based on: mpc-protocols/mpc/src/ffi/honey_badger_bindings.h
"""

import ctypes
from ctypes import (
    Structure, POINTER,
    c_uint64, c_size_t, c_uint8, c_int, c_void_p, c_bool
)
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional
import os
import platform


class ShareErrorCode(IntEnum):
    """Error codes for share operations - matches ShareErrorCode enum in C"""
    SUCCESS = 0
    INSUFFICIENT_SHARES = 1
    DEGREE_MISMATCH = 2
    ID_MISMATCH = 3
    INVALID_INPUT = 4
    TYPE_MISMATCH = 5
    NO_SUITABLE_DOMAIN = 6
    POLYNOMIAL_OPERATION_ERROR = 7
    DECODING_ERROR = 8


class FieldKind(IntEnum):
    """Field type - matches FieldKind enum in C"""
    BLS12_381_FR = 0


class ShareType(IntEnum):
    """Types of secret shares"""
    SHAMIR = 0
    ROBUST = 1
    NON_ROBUST = 2


class ShareError(Exception):
    """Exception raised for share operation errors"""
    def __init__(self, message: str, error_code: ShareErrorCode):
        super().__init__(message)
        self.error_code = error_code


# C structure definitions matching honey_badger_bindings.h

class U256(Structure):
    """256-bit unsigned integer (4 x u64 limbs)"""
    _fields_ = [
        ("data", c_uint64 * 4),
    ]


class U256Slice(Structure):
    """Slice of U256 elements"""
    _fields_ = [
        ("pointer", POINTER(U256)),
        ("len", c_size_t),
    ]


class ByteSlice(Structure):
    """Slice of bytes"""
    _fields_ = [
        ("pointer", POINTER(c_uint8)),
        ("len", c_size_t),
    ]


class UsizeSlice(Structure):
    """Slice of usize values"""
    _fields_ = [
        ("pointer", POINTER(c_size_t)),
        ("len", c_size_t),
    ]


# Share structures use opaque pointers for the share data
# typedef struct FieldOpaque {} FieldOpaque;

class ShamirShare(Structure):
    """Shamir share structure - uses opaque pointer for share data"""
    _fields_ = [
        ("share", c_void_p),  # FieldOpaque *
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
    """Robust share structure - uses opaque pointer for share data"""
    _fields_ = [
        ("share", c_void_p),  # FieldOpaque *
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
    """Non-robust share structure - uses opaque pointer for share data"""
    _fields_ = [
        ("share", c_void_p),  # FieldOpaque *
        ("id", c_size_t),
        ("degree", c_size_t),
    ]


class NonRobustShareSlice(Structure):
    """Slice of non-robust shares"""
    _fields_ = [
        ("pointer", POINTER(NonRobustShare)),
        ("len", c_size_t),
    ]


@dataclass
class Share:
    """Python-friendly share representation"""
    share_bytes: bytes  # 32 bytes for BLS12-381 scalar
    party_id: int
    threshold: int
    share_type: ShareType

    @classmethod
    def from_robust_c_share(cls, c_share: RobustShare, lib: ctypes.CDLL) -> "Share":
        """Create from C robust share structure by extracting bytes via FFI"""
        # Use field_ptr_to_bytes to extract the bytes from the opaque pointer
        byte_slice = lib.field_ptr_to_bytes(c_share.share, True)  # big-endian
        share_bytes = bytes(byte_slice.pointer[:byte_slice.len])
        lib.free_bytes_slice(byte_slice)
        return cls(
            share_bytes=share_bytes,
            party_id=c_share.id,
            threshold=c_share.degree,
            share_type=ShareType.ROBUST,
        )

    @classmethod
    def from_non_robust_c_share(cls, c_share: NonRobustShare, lib: ctypes.CDLL) -> "Share":
        """Create from C non-robust share structure by extracting bytes via FFI"""
        byte_slice = lib.field_ptr_to_bytes(c_share.share, True)  # big-endian
        share_bytes = bytes(byte_slice.pointer[:byte_slice.len])
        lib.free_bytes_slice(byte_slice)
        return cls(
            share_bytes=share_bytes,
            party_id=c_share.id,
            threshold=c_share.degree,
            share_type=ShareType.NON_ROBUST,
        )


class NativeShareManager:
    """
    Native secret sharing manager using C FFI

    Provides access to HoneyBadger MPC secret sharing operations.
    Based on mpc-protocols FFI (honey_badger_bindings.h).
    """

    def __init__(
        self,
        n_parties: int,
        threshold: int,
        robust: bool = True,
        library_path: Optional[str] = None
    ):
        """
        Initialize the share manager

        Args:
            n_parties: Total number of parties
            threshold: Reconstruction threshold (t)
            robust: Whether to use robust shares (Byzantine fault tolerant)
            library_path: Path to the MPC library
        """
        # Validate HoneyBadger MPC parameters
        if n_parties < 3:
            raise ValueError(
                f"HoneyBadger MPC requires at least 3 parties, got n={n_parties}"
            )
        if n_parties < 3 * threshold + 1:
            raise ValueError(
                f"Invalid parameters: n={n_parties} must be >= 3t+1={3 * threshold + 1} "
                f"for t={threshold}"
            )

        self._n_parties = n_parties
        self._threshold = threshold
        self._robust = robust
        self._field_kind = FieldKind.BLS12_381_FR

        self._lib = self._load_library(library_path)
        self._setup_functions()

    @property
    def n_parties(self) -> int:
        return self._n_parties

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def robust(self) -> bool:
        return self._robust

    def _load_library(self, library_path: Optional[str]) -> ctypes.CDLL:
        """Load the MPC protocols shared library"""
        if library_path:
            return ctypes.CDLL(library_path)

        # Try common locations
        system = platform.system()
        if system == "Darwin":
            lib_names = ["libstoffelmpc_mpc.dylib", "libmpc_protocols.dylib"]
        elif system == "Windows":
            lib_names = ["stoffelmpc_mpc.dll", "mpc_protocols.dll"]
        else:
            lib_names = ["libstoffelmpc_mpc.so", "libmpc_protocols.so"]

        search_paths = [
            ".",
            "./target/release",
            "./target/debug",
            "./external/mpc-protocols/target/release",
            "./external/mpc-protocols/target/debug",
            "/usr/local/lib",
            "/usr/lib",
        ]

        for path in search_paths:
            for lib_name in lib_names:
                full_path = os.path.join(path, lib_name)
                if os.path.exists(full_path):
                    try:
                        return ctypes.CDLL(full_path)
                    except OSError:
                        continue

        # Try loading without path
        for lib_name in lib_names:
            try:
                return ctypes.CDLL(lib_name)
            except OSError:
                continue

        raise RuntimeError(
            "Could not find MPC protocols library. "
            "Please build it with 'cargo build --release' in external/mpc-protocols "
            "or specify the library_path parameter."
        )

    def _setup_functions(self):
        """Set up C function signatures matching honey_badger_bindings.h"""

        # field_ptr_to_bytes - converts opaque field pointer to bytes
        self._lib.field_ptr_to_bytes.argtypes = [c_void_p, c_bool]
        self._lib.field_ptr_to_bytes.restype = ByteSlice

        # free_bytes_slice
        self._lib.free_bytes_slice.argtypes = [ByteSlice]
        self._lib.free_bytes_slice.restype = None

        # be_bytes_to_u256 - convert bytes to U256
        self._lib.be_bytes_to_u256.argtypes = [ByteSlice]
        self._lib.be_bytes_to_u256.restype = U256

        # le_bytes_to_u256
        self._lib.le_bytes_to_u256.argtypes = [ByteSlice]
        self._lib.le_bytes_to_u256.restype = U256

        # u256_to_be_bytes
        self._lib.u256_to_be_bytes.argtypes = [U256]
        self._lib.u256_to_be_bytes.restype = ByteSlice

        # u256_to_le_bytes
        self._lib.u256_to_le_bytes.argtypes = [U256]
        self._lib.u256_to_le_bytes.restype = ByteSlice

        # free_u256_slice
        self._lib.free_u256_slice.argtypes = [U256Slice]
        self._lib.free_u256_slice.restype = None

        # robust_share_compute_shares
        # ShareErrorCode robust_share_compute_shares(
        #     U256 secret, uintptr_t degree, uintptr_t n,
        #     RobustShareSlice *output_shares, FieldKind field_kind)
        self._lib.robust_share_compute_shares.argtypes = [
            U256,  # secret
            c_size_t,  # degree (threshold)
            c_size_t,  # n (number of parties)
            POINTER(RobustShareSlice),  # output_shares
            c_int,  # field_kind
        ]
        self._lib.robust_share_compute_shares.restype = c_int

        # robust_share_recover_secret
        # ShareErrorCode robust_share_recover_secret(
        #     RobustShareSlice shares, uintptr_t n,
        #     U256 *output_secret, U256Slice *output_coeffs, FieldKind field_kind)
        self._lib.robust_share_recover_secret.argtypes = [
            RobustShareSlice,  # shares
            c_size_t,  # n
            POINTER(U256),  # output_secret
            POINTER(U256Slice),  # output_coeffs
            c_int,  # field_kind
        ]
        self._lib.robust_share_recover_secret.restype = c_int

        # non_robust_share_compute_shares
        self._lib.non_robust_share_compute_shares.argtypes = [
            U256,  # secret
            c_size_t,  # degree (threshold)
            c_size_t,  # n (number of parties)
            POINTER(NonRobustShareSlice),  # output_shares
            c_int,  # field_kind
        ]
        self._lib.non_robust_share_compute_shares.restype = c_int

        # non_robust_share_recover_secret
        self._lib.non_robust_share_recover_secret.argtypes = [
            NonRobustShareSlice,  # shares
            c_size_t,  # n
            POINTER(U256),  # output_secret
            POINTER(U256Slice),  # output_coeffs
            c_int,  # field_kind
        ]
        self._lib.non_robust_share_recover_secret.restype = c_int

        # free_robust_share_slice
        self._lib.free_robust_share_slice.argtypes = [RobustShareSlice]
        self._lib.free_robust_share_slice.restype = None

        # free_non_robust_share_slice
        self._lib.free_non_robust_share_slice.argtypes = [NonRobustShareSlice]
        self._lib.free_non_robust_share_slice.restype = None

        # robust_share_new - creates a share from components
        self._lib.robust_share_new.argtypes = [
            U256,  # secret value
            c_size_t,  # id
            c_size_t,  # degree
            c_int,  # field_kind
        ]
        self._lib.robust_share_new.restype = RobustShare

        # non_robust_share_new
        self._lib.non_robust_share_new.argtypes = [
            U256,  # secret value
            c_size_t,  # id
            c_size_t,  # degree
            c_int,  # field_kind
        ]
        self._lib.non_robust_share_new.restype = NonRobustShare

    def _int_to_u256(self, value: int) -> U256:
        """Convert an integer to a U256 structure"""
        u256 = U256()
        # Handle negative numbers by taking absolute value
        # (proper field negation would require the field modulus)
        if value < 0:
            value = abs(value)

        # Convert to 4 limbs (little-endian u64 array)
        data = (c_uint64 * 4)()
        data[0] = value & ((1 << 64) - 1)
        data[1] = (value >> 64) & ((1 << 64) - 1)
        data[2] = (value >> 128) & ((1 << 64) - 1)
        data[3] = (value >> 192) & ((1 << 64) - 1)
        u256.data = data
        return u256

    def _u256_to_int(self, u256: U256) -> int:
        """Convert a U256 structure to an integer"""
        result = 0
        for i in range(4):
            result |= u256.data[i] << (64 * i)

        # Check if this is a "small" value that fits in i64
        if result <= (1 << 63) - 1:
            return result

        # Otherwise return as large positive integer
        return result

    def create_shares(self, value: int) -> List[Share]:
        """
        Create secret shares for a value

        Args:
            value: The secret value to share

        Returns:
            List of Share objects, one for each party

        Raises:
            ShareError: If sharing fails
        """
        secret = self._int_to_u256(value)

        if self._robust:
            output_shares = RobustShareSlice()
            ret = self._lib.robust_share_compute_shares(
                secret,
                self._threshold,
                self._n_parties,
                ctypes.byref(output_shares),
                self._field_kind
            )

            if ret != 0:
                raise ShareError(
                    f"Failed to create robust shares: error code {ret}",
                    ShareErrorCode(ret)
                )

            try:
                shares = []
                for i in range(output_shares.len):
                    share = Share.from_robust_c_share(output_shares.pointer[i], self._lib)
                    shares.append(share)
                return shares
            finally:
                self._lib.free_robust_share_slice(output_shares)

        else:
            output_shares = NonRobustShareSlice()
            ret = self._lib.non_robust_share_compute_shares(
                secret,
                self._threshold,
                self._n_parties,
                ctypes.byref(output_shares),
                self._field_kind
            )

            if ret != 0:
                raise ShareError(
                    f"Failed to create non-robust shares: error code {ret}",
                    ShareErrorCode(ret)
                )

            try:
                shares = []
                for i in range(output_shares.len):
                    share = Share.from_non_robust_c_share(output_shares.pointer[i], self._lib)
                    shares.append(share)
                return shares
            finally:
                self._lib.free_non_robust_share_slice(output_shares)

    def reconstruct(self, shares: List[Share]) -> int:
        """
        Reconstruct a secret from shares

        Args:
            shares: List of shares (need at least threshold + 1)

        Returns:
            The reconstructed secret value

        Raises:
            ShareError: If reconstruction fails
        """
        if len(shares) < self._threshold + 1:
            raise ShareError(
                f"Need at least {self._threshold + 1} shares, got {len(shares)}",
                ShareErrorCode.INSUFFICIENT_SHARES
            )

        output_secret = U256()
        output_coeffs = U256Slice()

        if self._robust:
            # Create C array of shares
            # We need to reconstruct the C shares from our Python Share objects
            # This requires converting bytes back to FieldOpaque pointers
            # For reconstruction, we use robust_share_new to create shares
            c_shares = (RobustShare * len(shares))()
            for i, share in enumerate(shares):
                # Create a new share using robust_share_new
                secret_u256 = self._bytes_to_u256(share.share_bytes)
                c_share = self._lib.robust_share_new(
                    secret_u256,
                    share.party_id,
                    share.threshold,
                    self._field_kind
                )
                c_shares[i] = c_share

            shares_slice = RobustShareSlice()
            shares_slice.pointer = c_shares
            shares_slice.len = len(shares)

            ret = self._lib.robust_share_recover_secret(
                shares_slice,
                len(shares),  # number of shares provided, not n_parties
                ctypes.byref(output_secret),
                ctypes.byref(output_coeffs),
                self._field_kind
            )

            if ret != 0:
                raise ShareError(
                    f"Failed to reconstruct from robust shares: error code {ret}",
                    ShareErrorCode(ret)
                )

            try:
                return self._u256_to_int(output_secret)
            finally:
                if output_coeffs.pointer:
                    self._lib.free_u256_slice(output_coeffs)

        else:
            # Non-robust reconstruction
            c_shares = (NonRobustShare * len(shares))()
            for i, share in enumerate(shares):
                secret_u256 = self._bytes_to_u256(share.share_bytes)
                c_share = self._lib.non_robust_share_new(
                    secret_u256,
                    share.party_id,
                    share.threshold,
                    self._field_kind
                )
                c_shares[i] = c_share

            shares_slice = NonRobustShareSlice()
            shares_slice.pointer = c_shares
            shares_slice.len = len(shares)

            ret = self._lib.non_robust_share_recover_secret(
                shares_slice,
                len(shares),  # number of shares provided, not n_parties
                ctypes.byref(output_secret),
                ctypes.byref(output_coeffs),
                self._field_kind
            )

            if ret != 0:
                raise ShareError(
                    f"Failed to reconstruct from non-robust shares: error code {ret}",
                    ShareErrorCode(ret)
                )

            try:
                return self._u256_to_int(output_secret)
            finally:
                if output_coeffs.pointer:
                    self._lib.free_u256_slice(output_coeffs)

    def _bytes_to_u256(self, data: bytes) -> U256:
        """Convert bytes to U256 (big-endian)"""
        # Pad or truncate to 32 bytes
        if len(data) < 32:
            data = data.rjust(32, b'\x00')
        elif len(data) > 32:
            data = data[:32]

        # Create ByteSlice and use FFI to convert
        byte_array = (c_uint8 * 32)(*data)
        byte_slice = ByteSlice()
        byte_slice.pointer = ctypes.cast(byte_array, POINTER(c_uint8))
        byte_slice.len = 32

        return self._lib.be_bytes_to_u256(byte_slice)
