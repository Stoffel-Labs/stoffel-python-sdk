"""
Stoffel SDK Enums

Type enumerations for MPC configuration matching the Rust SDK API.
"""

from enum import IntEnum


class ProtocolType(IntEnum):
    """MPC protocol selection

    Currently only HoneyBadger is supported. This enum exists for
    forward compatibility with future protocol implementations.
    """
    HONEYBADGER = 0  # Byzantine fault-tolerant (default)


class ShareType(IntEnum):
    """Secret sharing scheme selection

    Determines which secret sharing algorithm is used for MPC.
    """
    ROBUST = 0      # Reed-Solomon error correction (default, required for HoneyBadger)
    NON_ROBUST = 1  # Standard Shamir (faster, requires honest parties)


class OptimizationLevel(IntEnum):
    """Compiler optimization level

    Controls how aggressively the StoffelLang compiler optimizes code.
    """
    NONE = 0  # No optimization
    O1 = 1    # Basic optimization
    O2 = 2    # Standard optimization
    O3 = 3    # Aggressive optimization
