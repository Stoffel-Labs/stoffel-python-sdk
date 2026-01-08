"""
FFI error handling for Stoffel native bindings

Maps C error codes to Python exceptions with rich context.
Based on: mpc-protocols/mpc/src/ffi/honey_badger_bindings.h
"""

from enum import IntEnum
from typing import Optional


# ==============================================================================
# Error Code Enums
# ==============================================================================

class HoneyBadgerErrorCode(IntEnum):
    """Error codes for HoneyBadger MPC operations"""
    SUCCESS = 0
    NETWORK_ERROR = 1
    RANSHA_ERROR = 2
    INPUT_ERROR = 3
    DOUSHA_ERROR = 4
    RANDOUSHA_ERROR = 5
    NOT_ENOUGH_PREPROCESSING = 6
    TRIPLE_GEN_ERROR = 7
    RBC_ERROR = 8
    MUL_ERROR = 9
    OUTPUT_ERROR = 10
    BATCH_RECON_ERROR = 11
    BINCODE_SERIALIZATION_ERROR = 12
    JOIN_ERROR = 13
    CHANNEL_CLOSED = 14
    OUTPUT_NOT_READY = 15


class NetworkErrorCode(IntEnum):
    """Error codes for network operations"""
    SUCCESS = 0
    INCORRECT_NETWORK_TYPE = 1
    INCORRECT_SOCK_ADDR = 2
    CONNECT_ERROR = 3
    NETWORK_ALREADY_IN_USE = 4
    RECV_ERROR = 5
    SEND_ERROR = 6
    TIMEOUT = 7
    PARTY_NOT_FOUND = 8
    CLIENT_NOT_FOUND = 9


class ShareErrorCode(IntEnum):
    """Error codes for secret sharing operations"""
    SUCCESS = 0
    INSUFFICIENT_SHARES = 1
    DEGREE_MISMATCH = 2
    ID_MISMATCH = 3
    INVALID_INPUT = 4
    TYPE_MISMATCH = 5
    NO_SUITABLE_DOMAIN = 6
    POLYNOMIAL_OPERATION_ERROR = 7
    DECODING_ERROR = 8


class RbcErrorCode(IntEnum):
    """Error codes for Reliable Broadcast operations"""
    SUCCESS = 0
    INVALID_THRESHOLD = 1
    SESSION_ENDED = 2
    UNKNOWN_MSG_TYPE = 3
    SEND_FAILED = 4
    INTERNAL = 5
    NETWORK_SEND_ERROR = 6
    NETWORK_TIMEOUT = 7
    NETWORK_PARTY_NOT_FOUND = 8
    NETWORK_CLIENT_NOT_FOUND = 9
    SERIALIZATION_ERROR = 10
    SHARD_ERROR = 11
    SESSION_NOT_FOUND = 12


# ==============================================================================
# Exception Classes
# ==============================================================================

class FFIError(Exception):
    """Base class for FFI errors"""

    def __init__(self, message: str, code: int = -1):
        super().__init__(message)
        self.code = code


class NetworkError(FFIError):
    """Network-related FFI errors"""

    def __init__(self, message: str, code: NetworkErrorCode):
        super().__init__(message, code)
        self.error_code = code


class HoneyBadgerError(FFIError):
    """HoneyBadger MPC protocol errors"""

    def __init__(self, message: str, code: HoneyBadgerErrorCode):
        super().__init__(message, code)
        self.error_code = code


class ShareError(FFIError):
    """Secret sharing operation errors"""

    def __init__(self, message: str, code: ShareErrorCode):
        super().__init__(message, code)
        self.error_code = code


class RbcError(FFIError):
    """Reliable Broadcast operation errors"""

    def __init__(self, message: str, code: RbcErrorCode):
        super().__init__(message, code)
        self.error_code = code


# ==============================================================================
# Error Messages
# ==============================================================================

HONEYBADGER_ERROR_MESSAGES = {
    HoneyBadgerErrorCode.SUCCESS: "Success",
    HoneyBadgerErrorCode.NETWORK_ERROR: "Network error during MPC operation",
    HoneyBadgerErrorCode.RANSHA_ERROR: "Random share generation error",
    HoneyBadgerErrorCode.INPUT_ERROR: "Invalid input to MPC protocol",
    HoneyBadgerErrorCode.DOUSHA_ERROR: "Double share error",
    HoneyBadgerErrorCode.RANDOUSHA_ERROR: "Random double share error",
    HoneyBadgerErrorCode.NOT_ENOUGH_PREPROCESSING: "Insufficient preprocessing material (Beaver triples)",
    HoneyBadgerErrorCode.TRIPLE_GEN_ERROR: "Beaver triple generation failed",
    HoneyBadgerErrorCode.RBC_ERROR: "Reliable broadcast error",
    HoneyBadgerErrorCode.MUL_ERROR: "Secure multiplication error",
    HoneyBadgerErrorCode.OUTPUT_ERROR: "Output reconstruction error",
    HoneyBadgerErrorCode.BATCH_RECON_ERROR: "Batch reconstruction error",
    HoneyBadgerErrorCode.BINCODE_SERIALIZATION_ERROR: "Message serialization failed",
    HoneyBadgerErrorCode.JOIN_ERROR: "Task join error",
    HoneyBadgerErrorCode.CHANNEL_CLOSED: "Communication channel closed unexpectedly",
    HoneyBadgerErrorCode.OUTPUT_NOT_READY: "Output shares not yet available",
}

NETWORK_ERROR_MESSAGES = {
    NetworkErrorCode.SUCCESS: "Success",
    NetworkErrorCode.INCORRECT_NETWORK_TYPE: "Wrong network type",
    NetworkErrorCode.INCORRECT_SOCK_ADDR: "Invalid socket address",
    NetworkErrorCode.CONNECT_ERROR: "Connection failed",
    NetworkErrorCode.NETWORK_ALREADY_IN_USE: "Network port already in use",
    NetworkErrorCode.RECV_ERROR: "Failed to receive data",
    NetworkErrorCode.SEND_ERROR: "Failed to send data",
    NetworkErrorCode.TIMEOUT: "Network operation timed out",
    NetworkErrorCode.PARTY_NOT_FOUND: "MPC party not found in network",
    NetworkErrorCode.CLIENT_NOT_FOUND: "Client not found in network",
}

SHARE_ERROR_MESSAGES = {
    ShareErrorCode.SUCCESS: "Success",
    ShareErrorCode.INSUFFICIENT_SHARES: "Not enough shares for reconstruction",
    ShareErrorCode.DEGREE_MISMATCH: "Share polynomial degrees don't match",
    ShareErrorCode.ID_MISMATCH: "Share party IDs don't match",
    ShareErrorCode.INVALID_INPUT: "Invalid input to share operation",
    ShareErrorCode.TYPE_MISMATCH: "Share types don't match",
    ShareErrorCode.NO_SUITABLE_DOMAIN: "No suitable evaluation domain found",
    ShareErrorCode.POLYNOMIAL_OPERATION_ERROR: "Polynomial operation failed",
    ShareErrorCode.DECODING_ERROR: "Failed to decode share data",
}

RBC_ERROR_MESSAGES = {
    RbcErrorCode.SUCCESS: "Success",
    RbcErrorCode.INVALID_THRESHOLD: "Invalid threshold for RBC",
    RbcErrorCode.SESSION_ENDED: "RBC session has ended",
    RbcErrorCode.UNKNOWN_MSG_TYPE: "Unknown RBC message type",
    RbcErrorCode.SEND_FAILED: "Failed to send RBC message",
    RbcErrorCode.INTERNAL: "Internal RBC error",
    RbcErrorCode.NETWORK_SEND_ERROR: "Network send error in RBC",
    RbcErrorCode.NETWORK_TIMEOUT: "RBC network timeout",
    RbcErrorCode.NETWORK_PARTY_NOT_FOUND: "Party not found in RBC network",
    RbcErrorCode.NETWORK_CLIENT_NOT_FOUND: "Client not found in RBC network",
    RbcErrorCode.SERIALIZATION_ERROR: "RBC message serialization error",
    RbcErrorCode.SHARD_ERROR: "RBC shard error",
    RbcErrorCode.SESSION_NOT_FOUND: "RBC session not found",
}


# ==============================================================================
# Error Checking Functions
# ==============================================================================

def check_hb_error(code: int, context: str = "") -> None:
    """
    Check HoneyBadger error code and raise exception if not success

    Args:
        code: Error code from FFI function
        context: Additional context for error message

    Raises:
        HoneyBadgerError: If code is not SUCCESS
    """
    if code == HoneyBadgerErrorCode.SUCCESS:
        return

    try:
        error_code = HoneyBadgerErrorCode(code)
    except ValueError:
        raise HoneyBadgerError(
            f"{context}: Unknown HoneyBadger error code {code}",
            HoneyBadgerErrorCode.NETWORK_ERROR
        )

    message = HONEYBADGER_ERROR_MESSAGES.get(error_code, f"Unknown error {code}")
    if context:
        message = f"{context}: {message}"

    raise HoneyBadgerError(message, error_code)


def check_network_error(code: int, context: str = "") -> None:
    """
    Check network error code and raise exception if not success

    Args:
        code: Error code from FFI function
        context: Additional context for error message

    Raises:
        NetworkError: If code is not SUCCESS
    """
    if code == NetworkErrorCode.SUCCESS:
        return

    try:
        error_code = NetworkErrorCode(code)
    except ValueError:
        raise NetworkError(
            f"{context}: Unknown network error code {code}",
            NetworkErrorCode.CONNECT_ERROR
        )

    message = NETWORK_ERROR_MESSAGES.get(error_code, f"Unknown error {code}")
    if context:
        message = f"{context}: {message}"

    raise NetworkError(message, error_code)


def check_share_error(code: int, context: str = "") -> None:
    """
    Check share error code and raise exception if not success

    Args:
        code: Error code from FFI function
        context: Additional context for error message

    Raises:
        ShareError: If code is not SUCCESS
    """
    if code == ShareErrorCode.SUCCESS:
        return

    try:
        error_code = ShareErrorCode(code)
    except ValueError:
        raise ShareError(
            f"{context}: Unknown share error code {code}",
            ShareErrorCode.INVALID_INPUT
        )

    message = SHARE_ERROR_MESSAGES.get(error_code, f"Unknown error {code}")
    if context:
        message = f"{context}: {message}"

    raise ShareError(message, error_code)


def check_rbc_error(code: int, context: str = "") -> None:
    """
    Check RBC error code and raise exception if not success

    Args:
        code: Error code from FFI function
        context: Additional context for error message

    Raises:
        RbcError: If code is not SUCCESS
    """
    if code == RbcErrorCode.SUCCESS:
        return

    try:
        error_code = RbcErrorCode(code)
    except ValueError:
        raise RbcError(
            f"{context}: Unknown RBC error code {code}",
            RbcErrorCode.INTERNAL
        )

    message = RBC_ERROR_MESSAGES.get(error_code, f"Unknown error {code}")
    if context:
        message = f"{context}: {message}"

    raise RbcError(message, error_code)
