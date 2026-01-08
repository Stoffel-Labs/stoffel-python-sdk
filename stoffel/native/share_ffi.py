"""
Secret Sharing FFI bindings

Raw ctypes bindings for secret sharing functions from mpc-protocols.
Based on: mpc-protocols/mpc/src/ffi/c_bindings/share/mod.rs

Supports three secret sharing schemes:
- Shamir: Standard Shamir secret sharing
- Robust: Reed-Solomon error correction (used by HoneyBadger)
- NonRobust: Faster, requires honest parties
"""

import ctypes
from ctypes import POINTER, c_int, c_size_t, c_bool
from typing import Optional, List, Tuple

from ._lib_loader import get_mpc_library, LibraryLoadError
from .types import (
    U256,
    U256Slice,
    UsizeSlice,
    ByteSlice,
    ShamirShare,
    ShamirShareSlice,
    RobustShare,
    RobustShareSlice,
    NonRobustShare,
    NonRobustShareSlice,
    FieldKind,
)
from .errors import (
    ShareErrorCode,
    ShareError,
    check_share_error,
)


class ShareFunctions:
    """
    Raw secret sharing FFI function bindings

    This class provides direct access to the C FFI functions for
    secret sharing operations. Functions are lazily initialized on first use.
    """

    _instance: Optional["ShareFunctions"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self._lib = get_mpc_library()
            self._setup_functions()
            self._initialized = True
        except LibraryLoadError:
            self._lib = None
            self._initialized = True

    @property
    def available(self) -> bool:
        """Check if secret sharing FFI functions are available"""
        return self._lib is not None

    def _setup_functions(self):
        """Set up C function signatures"""
        lib = self._lib

        # ======================================================================
        # Shamir Secret Sharing
        # ======================================================================

        # shamir_share_new - Create a new Shamir share
        lib.shamir_share_new.argtypes = [
            U256,           # secret
            c_size_t,       # id
            c_size_t,       # degree
            c_int,          # field_kind
        ]
        lib.shamir_share_new.restype = ShamirShare

        # shamir_share_compute_shares - Compute shares for a secret
        lib.shamir_share_compute_shares.argtypes = [
            U256,                           # secret
            c_size_t,                       # degree
            POINTER(UsizeSlice),            # ids (optional)
            c_int,                          # field_kind
            POINTER(ShamirShareSlice),      # output_shares
        ]
        lib.shamir_share_compute_shares.restype = c_int  # ShareErrorCode

        # shamir_share_recover_secret - Recover secret from shares
        lib.shamir_share_recover_secret.argtypes = [
            ShamirShareSlice,       # shares
            POINTER(U256),          # output_secret
            POINTER(U256Slice),     # output_coeffs
            c_int,                  # field_kind
        ]
        lib.shamir_share_recover_secret.restype = c_int  # ShareErrorCode

        # free_shamir_share_slice
        lib.free_shamir_share_slice.argtypes = [ShamirShareSlice]
        lib.free_shamir_share_slice.restype = None

        # ======================================================================
        # Robust Secret Sharing (Reed-Solomon)
        # ======================================================================

        # robust_share_new - Create a new Robust share
        lib.robust_share_new.argtypes = [
            U256,           # secret
            c_size_t,       # id
            c_size_t,       # degree
            c_int,          # field_kind
        ]
        lib.robust_share_new.restype = RobustShare

        # robust_share_compute_shares - Compute robust shares
        lib.robust_share_compute_shares.argtypes = [
            U256,                           # secret
            c_size_t,                       # degree
            c_size_t,                       # n (number of shares)
            POINTER(RobustShareSlice),      # output_shares
            c_int,                          # field_kind
        ]
        lib.robust_share_compute_shares.restype = c_int  # ShareErrorCode

        # robust_share_recover_secret - Recover secret from robust shares
        lib.robust_share_recover_secret.argtypes = [
            RobustShareSlice,       # shares
            c_size_t,               # degree
            POINTER(U256),          # output_secret
            c_int,                  # field_kind
        ]
        lib.robust_share_recover_secret.restype = c_int  # ShareErrorCode

        # free_robust_share_slice
        lib.free_robust_share_slice.argtypes = [RobustShareSlice]
        lib.free_robust_share_slice.restype = None

        # ======================================================================
        # Non-Robust Secret Sharing
        # ======================================================================

        # non_robust_share_new - Create a new NonRobust share
        lib.non_robust_share_new.argtypes = [
            U256,           # secret
            c_size_t,       # id
            c_size_t,       # degree
            c_int,          # field_kind
        ]
        lib.non_robust_share_new.restype = NonRobustShare

        # non_robust_share_compute_shares - Compute non-robust shares
        lib.non_robust_share_compute_shares.argtypes = [
            U256,                               # secret
            c_size_t,                           # degree
            c_size_t,                           # n (number of shares)
            POINTER(NonRobustShareSlice),       # output_shares
            c_int,                              # field_kind
        ]
        lib.non_robust_share_compute_shares.restype = c_int  # ShareErrorCode

        # non_robust_share_recover_secret - Recover secret from non-robust shares
        lib.non_robust_share_recover_secret.argtypes = [
            NonRobustShareSlice,    # shares
            c_size_t,               # degree
            POINTER(U256),          # output_secret
            c_int,                  # field_kind
        ]
        lib.non_robust_share_recover_secret.restype = c_int  # ShareErrorCode

        # free_non_robust_share_slice
        lib.free_non_robust_share_slice.argtypes = [NonRobustShareSlice]
        lib.free_non_robust_share_slice.restype = None

        # ======================================================================
        # Utility Functions
        # ======================================================================

        # field_ptr_to_bytes - Convert field element to bytes
        lib.field_ptr_to_bytes.argtypes = [
            ctypes.c_void_p,    # field pointer
            c_bool,             # big-endian if true
        ]
        lib.field_ptr_to_bytes.restype = ByteSlice

    # ==========================================================================
    # Shamir Secret Sharing Methods
    # ==========================================================================

    def shamir_share_new(
        self,
        secret: int,
        id: int,
        degree: int,
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> ShamirShare:
        """
        Create a new Shamir share

        Args:
            secret: The secret value
            id: Share ID (party index)
            degree: Polynomial degree (threshold - 1)
            field_kind: Field type (default: BLS12-381)

        Returns:
            ShamirShare structure
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        secret_u256 = U256.from_int(secret)
        return self._lib.shamir_share_new(
            secret_u256, id, degree, field_kind.value
        )

    def shamir_compute_shares(
        self,
        secret: int,
        degree: int,
        ids: Optional[List[int]] = None,
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> List[ShamirShare]:
        """
        Compute Shamir shares for a secret

        Args:
            secret: The secret to share
            degree: Polynomial degree (t-1 for threshold t)
            ids: Optional list of party IDs (defaults to 1..n)
            field_kind: Field type

        Returns:
            List of ShamirShare structures

        Raises:
            ShareError: If share computation fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        secret_u256 = U256.from_int(secret)
        output_shares = ShamirShareSlice()

        if ids is not None:
            ids_array = (c_size_t * len(ids))(*ids)
            ids_slice = UsizeSlice(
                pointer=ctypes.cast(ids_array, POINTER(c_size_t)),
                len=len(ids)
            )
            ids_ptr = ctypes.byref(ids_slice)
        else:
            ids_ptr = None

        result = self._lib.shamir_share_compute_shares(
            secret_u256,
            degree,
            ids_ptr,
            field_kind.value,
            ctypes.byref(output_shares)
        )
        check_share_error(result, "shamir_share_compute_shares")

        # Convert to list
        shares = []
        for i in range(output_shares.len):
            shares.append(output_shares.pointer[i])

        return shares

    def shamir_recover_secret(
        self,
        shares: List[ShamirShare],
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> Tuple[int, List[int]]:
        """
        Recover secret from Shamir shares

        Args:
            shares: List of shares (need degree+1 shares)
            field_kind: Field type

        Returns:
            Tuple of (secret, coefficients)

        Raises:
            ShareError: If recovery fails (insufficient shares, etc.)
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        # Create share slice
        shares_array = (ShamirShare * len(shares))(*shares)
        shares_slice = ShamirShareSlice(
            pointer=ctypes.cast(shares_array, POINTER(ShamirShare)),
            len=len(shares)
        )

        output_secret = U256()
        output_coeffs = U256Slice()

        result = self._lib.shamir_share_recover_secret(
            shares_slice,
            ctypes.byref(output_secret),
            ctypes.byref(output_coeffs),
            field_kind.value
        )
        check_share_error(result, "shamir_share_recover_secret")

        secret = output_secret.to_int()

        # Extract coefficients
        coeffs = []
        for i in range(output_coeffs.len):
            coeffs.append(output_coeffs.pointer[i].to_int())

        return secret, coeffs

    # ==========================================================================
    # Robust Secret Sharing Methods
    # ==========================================================================

    def robust_share_new(
        self,
        secret: int,
        id: int,
        degree: int,
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> RobustShare:
        """
        Create a new Robust share

        Args:
            secret: The secret value
            id: Share ID (party index)
            degree: Polynomial degree
            field_kind: Field type

        Returns:
            RobustShare structure
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        secret_u256 = U256.from_int(secret)
        return self._lib.robust_share_new(
            secret_u256, id, degree, field_kind.value
        )

    def robust_compute_shares(
        self,
        secret: int,
        n: int,
        degree: int,
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> List[RobustShare]:
        """
        Compute Robust shares for a secret

        Uses Reed-Solomon encoding for error correction.

        Args:
            secret: The secret to share
            n: Number of shares to generate
            degree: Polynomial degree
            field_kind: Field type

        Returns:
            List of RobustShare structures

        Raises:
            ShareError: If share computation fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        secret_u256 = U256.from_int(secret)
        output_shares = RobustShareSlice()

        result = self._lib.robust_share_compute_shares(
            secret_u256,
            degree,
            n,
            ctypes.byref(output_shares),
            field_kind.value
        )
        check_share_error(result, "robust_share_compute_shares")

        # Convert to list
        shares = []
        for i in range(output_shares.len):
            shares.append(output_shares.pointer[i])

        return shares

    def robust_recover_secret(
        self,
        shares: List[RobustShare],
        degree: int,
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> int:
        """
        Recover secret from Robust shares

        Uses robust interpolation with error correction.

        Args:
            shares: List of shares
            degree: Polynomial degree used in sharing
            field_kind: Field type

        Returns:
            The recovered secret

        Raises:
            ShareError: If recovery fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        # Create share slice
        shares_array = (RobustShare * len(shares))(*shares)
        shares_slice = RobustShareSlice(
            pointer=ctypes.cast(shares_array, POINTER(RobustShare)),
            len=len(shares)
        )

        output_secret = U256()

        result = self._lib.robust_share_recover_secret(
            shares_slice,
            degree,
            ctypes.byref(output_secret),
            field_kind.value
        )
        check_share_error(result, "robust_share_recover_secret")

        return output_secret.to_int()

    # ==========================================================================
    # Non-Robust Secret Sharing Methods
    # ==========================================================================

    def non_robust_share_new(
        self,
        secret: int,
        id: int,
        degree: int,
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> NonRobustShare:
        """
        Create a new Non-Robust share

        Args:
            secret: The secret value
            id: Share ID (party index)
            degree: Polynomial degree
            field_kind: Field type

        Returns:
            NonRobustShare structure
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        secret_u256 = U256.from_int(secret)
        return self._lib.non_robust_share_new(
            secret_u256, id, degree, field_kind.value
        )

    def non_robust_compute_shares(
        self,
        secret: int,
        n: int,
        degree: int,
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> List[NonRobustShare]:
        """
        Compute Non-Robust shares for a secret

        Faster than robust shares but assumes honest parties.

        Args:
            secret: The secret to share
            n: Number of shares to generate
            degree: Polynomial degree
            field_kind: Field type

        Returns:
            List of NonRobustShare structures

        Raises:
            ShareError: If share computation fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        secret_u256 = U256.from_int(secret)
        output_shares = NonRobustShareSlice()

        result = self._lib.non_robust_share_compute_shares(
            secret_u256,
            degree,
            n,
            ctypes.byref(output_shares),
            field_kind.value
        )
        check_share_error(result, "non_robust_share_compute_shares")

        # Convert to list
        shares = []
        for i in range(output_shares.len):
            shares.append(output_shares.pointer[i])

        return shares

    def non_robust_recover_secret(
        self,
        shares: List[NonRobustShare],
        degree: int,
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> int:
        """
        Recover secret from Non-Robust shares

        Args:
            shares: List of shares
            degree: Polynomial degree used in sharing
            field_kind: Field type

        Returns:
            The recovered secret

        Raises:
            ShareError: If recovery fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        # Create share slice
        shares_array = (NonRobustShare * len(shares))(*shares)
        shares_slice = NonRobustShareSlice(
            pointer=ctypes.cast(shares_array, POINTER(NonRobustShare)),
            len=len(shares)
        )

        output_secret = U256()

        result = self._lib.non_robust_share_recover_secret(
            shares_slice,
            degree,
            ctypes.byref(output_secret),
            field_kind.value
        )
        check_share_error(result, "non_robust_share_recover_secret")

        return output_secret.to_int()

    # ==========================================================================
    # Memory Management
    # ==========================================================================

    def free_shamir_shares(self, shares: ShamirShareSlice) -> None:
        """Free Shamir share slice memory"""
        if self.available:
            self._lib.free_shamir_share_slice(shares)

    def free_robust_shares(self, shares: RobustShareSlice) -> None:
        """Free Robust share slice memory"""
        if self.available:
            self._lib.free_robust_share_slice(shares)

    def free_non_robust_shares(self, shares: NonRobustShareSlice) -> None:
        """Free Non-Robust share slice memory"""
        if self.available:
            self._lib.free_non_robust_share_slice(shares)


# Global singleton instance
_share_ffi: Optional[ShareFunctions] = None


def get_share_ffi() -> ShareFunctions:
    """Get the secret sharing FFI singleton"""
    global _share_ffi
    if _share_ffi is None:
        _share_ffi = ShareFunctions()
    return _share_ffi


def is_share_available() -> bool:
    """Check if secret sharing FFI is available"""
    return get_share_ffi().available
