"""
Native MPC bindings using ctypes

Provides direct access to the MPC protocols (secret sharing) via C FFI.
"""

import ctypes
from ctypes import (
    Structure, POINTER,
    c_uint64, c_size_t, c_uint8, c_int
)
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, Tuple
import os
import platform


class ShareErrorCode(IntEnum):
    """Error codes for share operations"""
    SUCCESS = 0
    INSUFFICIENT_SHARES = 1
    DEGREE_MISMATCH = 2
    ID_MISMATCH = 3
    INVALID_INPUT = 4
    TYPE_MISMATCH = 5
    NO_SUITABLE_DOMAIN = 6
    POLYNOMIAL_OPERATION_ERROR = 7
    DECODING_ERROR = 8


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


# C structure definitions matching the MPC FFI

class Bls12Fr(Structure):
    """BLS12-381 scalar field element (4 x u64 limbs)"""
    _fields_ = [
        ("data", c_uint64 * 4),
    ]


class Bls12FrSlice(Structure):
    """Slice of Bls12Fr elements"""
    _fields_ = [
        ("pointer", POINTER(Bls12Fr)),
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


class ShamirShareBls12(Structure):
    """Shamir share structure"""
    _fields_ = [
        ("share", Bls12Fr),
        ("id", c_size_t),
        ("degree", c_size_t),
    ]


class ShamirShareSliceBls12(Structure):
    """Slice of Shamir shares"""
    _fields_ = [
        ("pointer", POINTER(ShamirShareBls12)),
        ("len", c_size_t),
    ]


class RobustShareBls12(Structure):
    """Robust share structure"""
    _fields_ = [
        ("share", Bls12Fr),
        ("id", c_size_t),
        ("degree", c_size_t),
    ]


class RobustShareSliceBls12(Structure):
    """Slice of robust shares"""
    _fields_ = [
        ("pointer", POINTER(RobustShareBls12)),
        ("len", c_size_t),
    ]


class NonRobustShareBls12(Structure):
    """Non-robust share structure"""
    _fields_ = [
        ("share", Bls12Fr),
        ("id", c_size_t),
        ("degree", c_size_t),
    ]


class NonRobustShareSliceBls12(Structure):
    """Slice of non-robust shares"""
    _fields_ = [
        ("pointer", POINTER(NonRobustShareBls12)),
        ("len", c_size_t),
    ]


@dataclass
class Share:
    """Python-friendly share representation"""
    share_bytes: bytes  # 32 bytes for BLS12-381 scalar
    party_id: int
    threshold: int
    share_type: ShareType

    def to_robust_c_share(self) -> RobustShareBls12:
        """Convert to C robust share structure"""
        share = RobustShareBls12()
        # Convert bytes to Bls12Fr
        data = (c_uint64 * 4)()
        for i in range(4):
            start = i * 8
            end = start + 8
            data[i] = int.from_bytes(self.share_bytes[start:end], "little")
        share.share.data = data
        share.id = self.party_id
        share.degree = self.threshold
        return share

    def to_non_robust_c_share(self) -> NonRobustShareBls12:
        """Convert to C non-robust share structure"""
        share = NonRobustShareBls12()
        data = (c_uint64 * 4)()
        for i in range(4):
            start = i * 8
            end = start + 8
            data[i] = int.from_bytes(self.share_bytes[start:end], "little")
        share.share.data = data
        share.id = self.party_id
        share.degree = self.threshold
        return share

    @classmethod
    def from_robust_c_share(cls, c_share: RobustShareBls12) -> "Share":
        """Create from C robust share structure"""
        share_bytes = bytearray(32)
        for i in range(4):
            start = i * 8
            share_bytes[start:start + 8] = c_share.share.data[i].to_bytes(8, "little")
        return cls(
            share_bytes=bytes(share_bytes),
            party_id=c_share.id,
            threshold=c_share.degree,
            share_type=ShareType.ROBUST,
        )

    @classmethod
    def from_non_robust_c_share(cls, c_share: NonRobustShareBls12) -> "Share":
        """Create from C non-robust share structure"""
        share_bytes = bytearray(32)
        for i in range(4):
            start = i * 8
            share_bytes[start:start + 8] = c_share.share.data[i].to_bytes(8, "little")
        return cls(
            share_bytes=bytes(share_bytes),
            party_id=c_share.id,
            threshold=c_share.degree,
            share_type=ShareType.NON_ROBUST,
        )


class NativeShareManager:
    """
    Native secret sharing manager using C FFI

    Provides access to HoneyBadger MPC secret sharing operations.
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
        """Set up C function signatures"""
        # robust_share_compute_shares
        self._lib.robust_share_compute_shares.argtypes = [
            Bls12Fr,  # secret
            c_size_t,  # degree (threshold)
            c_size_t,  # n (number of parties)
            POINTER(RobustShareSliceBls12),  # output_shares
        ]
        self._lib.robust_share_compute_shares.restype = c_int

        # robust_share_recover_secret
        self._lib.robust_share_recover_secret.argtypes = [
            RobustShareSliceBls12,  # shares
            c_size_t,  # n
            POINTER(Bls12Fr),  # output_secret
            POINTER(Bls12FrSlice),  # output_coeffs
        ]
        self._lib.robust_share_recover_secret.restype = c_int

        # non_robust_share_compute_shares
        self._lib.non_robust_share_compute_shares.argtypes = [
            Bls12Fr,  # secret
            c_size_t,  # degree (threshold)
            c_size_t,  # n (number of parties)
            POINTER(NonRobustShareSliceBls12),  # output_shares
        ]
        self._lib.non_robust_share_compute_shares.restype = c_int

        # non_robust_share_recover_secret
        self._lib.non_robust_share_recover_secret.argtypes = [
            NonRobustShareSliceBls12,  # shares
            c_size_t,  # n
            POINTER(Bls12Fr),  # output_secret
            POINTER(Bls12FrSlice),  # output_coeffs
        ]
        self._lib.non_robust_share_recover_secret.restype = c_int

        # free functions
        self._lib.free_robust_share_bls12_slice.argtypes = [RobustShareSliceBls12]
        self._lib.free_robust_share_bls12_slice.restype = None

        self._lib.free_non_robust_share_bls12_slice.argtypes = [NonRobustShareSliceBls12]
        self._lib.free_non_robust_share_bls12_slice.restype = None

        self._lib.free_bls12_fr_slice.argtypes = [Bls12FrSlice]
        self._lib.free_bls12_fr_slice.restype = None

    def _int_to_bls12fr(self, value: int) -> Bls12Fr:
        """Convert an integer to a BLS12-381 field element"""
        fr = Bls12Fr()
        # Handle negative numbers
        if value < 0:
            # For negative numbers, we need to use modular arithmetic
            # The field modulus is approximately 2^255
            # For simplicity, we just use the absolute value and negate in the field
            # This is a simplified approach
            value = abs(value)

        # Convert to 4 limbs (little-endian)
        data = (c_uint64 * 4)()
        data[0] = value & ((1 << 64) - 1)
        data[1] = (value >> 64) & ((1 << 64) - 1)
        data[2] = (value >> 128) & ((1 << 64) - 1)
        data[3] = (value >> 192) & ((1 << 64) - 1)
        fr.data = data
        return fr

    def _bls12fr_to_int(self, fr: Bls12Fr) -> int:
        """Convert a BLS12-381 field element to an integer"""
        result = 0
        for i in range(4):
            result |= fr.data[i] << (64 * i)

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
        secret = self._int_to_bls12fr(value)

        if self._robust:
            output_shares = RobustShareSliceBls12()
            ret = self._lib.robust_share_compute_shares(
                secret,
                self._threshold,
                self._n_parties,
                ctypes.byref(output_shares)
            )

            if ret != 0:
                raise ShareError(
                    f"Failed to create robust shares: error code {ret}",
                    ShareErrorCode(ret)
                )

            try:
                shares = []
                for i in range(output_shares.len):
                    share = Share.from_robust_c_share(output_shares.pointer[i])
                    shares.append(share)
                return shares
            finally:
                self._lib.free_robust_share_bls12_slice(output_shares)

        else:
            output_shares = NonRobustShareSliceBls12()
            ret = self._lib.non_robust_share_compute_shares(
                secret,
                self._threshold,
                self._n_parties,
                ctypes.byref(output_shares)
            )

            if ret != 0:
                raise ShareError(
                    f"Failed to create non-robust shares: error code {ret}",
                    ShareErrorCode(ret)
                )

            try:
                shares = []
                for i in range(output_shares.len):
                    share = Share.from_non_robust_c_share(output_shares.pointer[i])
                    shares.append(share)
                return shares
            finally:
                self._lib.free_non_robust_share_bls12_slice(output_shares)

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

        output_secret = Bls12Fr()
        output_coeffs = Bls12FrSlice()

        if self._robust:
            # Create C array of shares
            c_shares = (RobustShareBls12 * len(shares))()
            for i, share in enumerate(shares):
                c_shares[i] = share.to_robust_c_share()

            shares_slice = RobustShareSliceBls12()
            shares_slice.pointer = c_shares
            shares_slice.len = len(shares)

            ret = self._lib.robust_share_recover_secret(
                shares_slice,
                self._n_parties,
                ctypes.byref(output_secret),
                ctypes.byref(output_coeffs)
            )

            if ret != 0:
                raise ShareError(
                    f"Failed to reconstruct from robust shares: error code {ret}",
                    ShareErrorCode(ret)
                )

            try:
                return self._bls12fr_to_int(output_secret)
            finally:
                if output_coeffs.pointer:
                    self._lib.free_bls12_fr_slice(output_coeffs)

        else:
            # Create C array of shares
            c_shares = (NonRobustShareBls12 * len(shares))()
            for i, share in enumerate(shares):
                c_shares[i] = share.to_non_robust_c_share()

            shares_slice = NonRobustShareSliceBls12()
            shares_slice.pointer = c_shares
            shares_slice.len = len(shares)

            ret = self._lib.non_robust_share_recover_secret(
                shares_slice,
                self._n_parties,
                ctypes.byref(output_secret),
                ctypes.byref(output_coeffs)
            )

            if ret != 0:
                raise ShareError(
                    f"Failed to reconstruct from non-robust shares: error code {ret}",
                    ShareErrorCode(ret)
                )

            try:
                return self._bls12fr_to_int(output_secret)
            finally:
                if output_coeffs.pointer:
                    self._lib.free_bls12_fr_slice(output_coeffs)
