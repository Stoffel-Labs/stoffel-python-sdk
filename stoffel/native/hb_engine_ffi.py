"""
HoneyBadgerMpcEngine FFI bindings using ctypes

Provides direct access to the HoneyBadger MPC engine via C FFI.
This enables server-side MPC operations including:
- Preprocessing (Beaver triple generation)
- Secure multiplication
- Share reconstruction (output)
"""

import ctypes
from ctypes import (
    Structure, POINTER, CFUNCTYPE,
    c_int, c_int64, c_uint8, c_uint64, c_size_t, c_void_p, c_char_p, c_double
)
from enum import IntEnum
from typing import Optional, Tuple, List
import os
import platform


class HBEngineErrorCode(IntEnum):
    """Error codes for HoneyBadgerMpcEngine operations"""
    SUCCESS = 0
    NULL_POINTER = 1
    NOT_READY = 2
    NETWORK_ERROR = 3
    PREPROCESSING_FAILED = 4
    MULTIPLY_FAILED = 5
    OPEN_SHARE_FAILED = 6
    SERIALIZATION_ERROR = 7
    INVALID_SHARE_TYPE = 8
    CLIENT_INPUT_FAILED = 9
    GET_CLIENT_SHARES_FAILED = 10
    RUNTIME_ERROR = 11
    INVALID_CONFIG = 12


class HBEngineError(Exception):
    """Exception raised for HoneyBadger engine errors"""
    def __init__(self, code: HBEngineErrorCode, message: str = ""):
        self.code = code
        self.message = message or self._default_message(code)
        super().__init__(f"{self.code.name}: {self.message}")

    @staticmethod
    def _default_message(code: HBEngineErrorCode) -> str:
        messages = {
            HBEngineErrorCode.SUCCESS: "Success",
            HBEngineErrorCode.NULL_POINTER: "Null pointer provided",
            HBEngineErrorCode.NOT_READY: "Engine not ready (preprocessing not complete)",
            HBEngineErrorCode.NETWORK_ERROR: "Network error during MPC operation",
            HBEngineErrorCode.PREPROCESSING_FAILED: "Preprocessing failed",
            HBEngineErrorCode.MULTIPLY_FAILED: "Multiplication operation failed",
            HBEngineErrorCode.OPEN_SHARE_FAILED: "Share opening/reconstruction failed",
            HBEngineErrorCode.SERIALIZATION_ERROR: "Serialization/deserialization error",
            HBEngineErrorCode.INVALID_SHARE_TYPE: "Invalid share type provided",
            HBEngineErrorCode.CLIENT_INPUT_FAILED: "Client input initialization failed",
            HBEngineErrorCode.GET_CLIENT_SHARES_FAILED: "Client shares retrieval failed",
            HBEngineErrorCode.RUNTIME_ERROR: "Tokio runtime creation failed",
            HBEngineErrorCode.INVALID_CONFIG: "Invalid configuration parameters",
        }
        return messages.get(code, "Unknown error")


class StoffelValueType(IntEnum):
    """Value types in StoffelVM"""
    UNIT = 0
    INT = 1
    FLOAT = 2
    BOOL = 3
    STRING = 4
    OBJECT = 5
    ARRAY = 6
    FOREIGN = 7
    CLOSURE = 8


class StoffelValueData(ctypes.Union):
    """Union to hold value data"""
    _fields_ = [
        ("int_val", c_int64),
        ("float_val", c_double),
        ("bool_val", c_int),
        ("string_val", c_char_p),
        ("object_id", c_size_t),
        ("array_id", c_size_t),
        ("foreign_id", c_size_t),
        ("closure_id", c_size_t),
    ]


class CStoffelValue(Structure):
    """C-compatible StoffelVM value"""
    _fields_ = [
        ("value_type", c_int),
        ("data", StoffelValueData),
    ]


class CShareType(Structure):
    """C-compatible ShareType representation

    kind: 0=Int, 1=Bool, 2=Float
    width: bit width for Int, or 0/1 for Bool
    """
    _fields_ = [
        ("kind", c_uint8),
        ("width", c_int64),
    ]


class ShareTypeKind(IntEnum):
    """Share type kinds"""
    INT = 0
    BOOL = 1
    FLOAT = 2


def _load_library() -> ctypes.CDLL:
    """Load the StoffelVM library"""
    system = platform.system()
    if system == "Darwin":
        lib_names = ["libstoffel_vm.dylib"]
    elif system == "Windows":
        lib_names = ["stoffel_vm.dll", "libstoffel_vm.dll"]
    else:
        lib_names = ["libstoffel_vm.so"]

    search_paths = [
        ".",
        "./target/release",
        "./target/debug",
        "./external/stoffel-vm/target/release",
        "./external/stoffel-vm/target/debug",
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

    for lib_name in lib_names:
        try:
            return ctypes.CDLL(lib_name)
        except OSError:
            continue

    raise RuntimeError(
        "Could not find StoffelVM library. "
        "Build with 'cargo build --release' in external/stoffel-vm"
    )


class HBEngineFFI:
    """Low-level FFI interface to HoneyBadgerMpcEngine"""

    def __init__(self, library_path: Optional[str] = None):
        if library_path:
            self._lib = ctypes.CDLL(library_path)
        else:
            self._lib = _load_library()

        self._setup_functions()

    def _setup_functions(self):
        """Set up C function signatures"""
        # hb_engine_new
        self._lib.hb_engine_new.argtypes = [
            c_uint64,      # instance_id
            c_size_t,      # party_id
            c_size_t,      # n
            c_size_t,      # t
            c_size_t,      # n_triples
            c_size_t,      # n_random
            c_void_p,      # network_ptr
        ]
        self._lib.hb_engine_new.restype = c_void_p

        # hb_engine_free
        self._lib.hb_engine_free.argtypes = [c_void_p]
        self._lib.hb_engine_free.restype = None

        # hb_engine_start_async
        self._lib.hb_engine_start_async.argtypes = [c_void_p]
        self._lib.hb_engine_start_async.restype = c_int

        # hb_engine_is_ready
        self._lib.hb_engine_is_ready.argtypes = [c_void_p]
        self._lib.hb_engine_is_ready.restype = c_int

        # hb_engine_multiply_share_async
        self._lib.hb_engine_multiply_share_async.argtypes = [
            c_void_p,              # engine_ptr
            CShareType,            # share_type
            POINTER(c_uint8),      # left_ptr
            c_size_t,              # left_len
            POINTER(c_uint8),      # right_ptr
            c_size_t,              # right_len
            POINTER(POINTER(c_uint8)),  # result_ptr
            POINTER(c_size_t),     # result_len_ptr
        ]
        self._lib.hb_engine_multiply_share_async.restype = c_int

        # hb_engine_open_share
        self._lib.hb_engine_open_share.argtypes = [
            c_void_p,              # engine_ptr
            CShareType,            # share_type
            POINTER(c_uint8),      # share_ptr
            c_size_t,              # share_len
            POINTER(CStoffelValue),  # result_ptr
        ]
        self._lib.hb_engine_open_share.restype = c_int

        # hb_engine_init_client_input
        self._lib.hb_engine_init_client_input.argtypes = [
            c_void_p,              # engine_ptr
            c_uint64,              # client_id
            POINTER(c_uint8),      # shares_data
            c_size_t,              # shares_len
        ]
        self._lib.hb_engine_init_client_input.restype = c_int

        # hb_engine_get_client_shares
        self._lib.hb_engine_get_client_shares.argtypes = [
            c_void_p,              # engine_ptr
            c_uint64,              # client_id
            POINTER(POINTER(c_uint8)),  # result_ptr
            POINTER(c_size_t),     # result_len_ptr
        ]
        self._lib.hb_engine_get_client_shares.restype = c_int

        # hb_engine_party_id
        self._lib.hb_engine_party_id.argtypes = [c_void_p]
        self._lib.hb_engine_party_id.restype = c_size_t

        # hb_engine_instance_id
        self._lib.hb_engine_instance_id.argtypes = [c_void_p]
        self._lib.hb_engine_instance_id.restype = c_uint64

        # hb_engine_protocol_name
        self._lib.hb_engine_protocol_name.argtypes = [c_void_p]
        self._lib.hb_engine_protocol_name.restype = c_char_p

        # hb_engine_get_network
        self._lib.hb_engine_get_network.argtypes = [c_void_p]
        self._lib.hb_engine_get_network.restype = c_void_p

        # hb_network_free
        self._lib.hb_network_free.argtypes = [c_void_p]
        self._lib.hb_network_free.restype = None

        # hb_free_bytes
        self._lib.hb_free_bytes.argtypes = [POINTER(c_uint8), c_size_t]
        self._lib.hb_free_bytes.restype = None


# Global FFI instance
_ffi: Optional[HBEngineFFI] = None


def get_hb_engine_ffi() -> HBEngineFFI:
    """Get or create the global HBEngineFFI instance"""
    global _ffi
    if _ffi is None:
        _ffi = HBEngineFFI()
    return _ffi


def is_hb_engine_available() -> bool:
    """Check if HoneyBadger engine FFI is available"""
    try:
        get_hb_engine_ffi()
        return True
    except (RuntimeError, OSError):
        return False


class HoneyBadgerMpcEngine:
    """
    High-level Python wrapper for HoneyBadgerMpcEngine

    Provides secure multiparty computation operations:
    - Preprocessing: Generate Beaver triples and random shares
    - Multiplication: Secure multiplication of secret-shared values
    - Output: Reconstruct (open) secret-shared values

    Usage:
        from stoffel.native.hb_engine_ffi import HoneyBadgerMpcEngine

        # Create engine with network
        engine = HoneyBadgerMpcEngine(
            instance_id=1,
            party_id=0,
            n_parties=4,
            threshold=1,
            n_triples=100,
            n_random=50,
            network_ptr=network_handle
        )

        # Run preprocessing
        engine.start_preprocessing()

        # Perform secure multiplication
        result = engine.multiply(left_share, right_share, share_type)

        # Reconstruct a value
        value = engine.open(share, share_type)
    """

    def __init__(
        self,
        instance_id: int,
        party_id: int,
        n_parties: int,
        threshold: int,
        n_triples: int = 100,
        n_random: int = 50,
        network_ptr: Optional[int] = None,
    ):
        """
        Create a new HoneyBadger MPC engine

        Args:
            instance_id: Unique identifier for this MPC instance
            party_id: This party's ID (0 to n-1)
            n_parties: Total number of parties
            threshold: Corruption tolerance threshold
            n_triples: Number of Beaver triples to generate
            n_random: Number of random shares to generate
            network_ptr: Pointer to QuicNetworkManager (optional)
        """
        self._ffi = get_hb_engine_ffi()

        # Validate parameters
        if n_parties < 4:
            raise ValueError(f"Need at least 4 parties, got {n_parties}")
        if n_parties < 3 * threshold + 1:
            raise ValueError(
                f"Invalid: n={n_parties} must be >= 3t+1={3*threshold+1}"
            )
        if party_id >= n_parties:
            raise ValueError(f"party_id {party_id} >= n_parties {n_parties}")

        # Create the engine
        # Handle network pointer - can be ctypes pointer or integer
        if network_ptr is None:
            network = None
        elif hasattr(network_ptr, 'contents'):
            # It's a ctypes pointer - cast to void pointer
            network = ctypes.cast(network_ptr, c_void_p)
        else:
            # Assume it's an integer address
            network = c_void_p(network_ptr)

        self._handle = self._ffi._lib.hb_engine_new(
            instance_id,
            party_id,
            n_parties,
            threshold,
            n_triples,
            n_random,
            network
        )

        if not self._handle:
            raise HBEngineError(
                HBEngineErrorCode.INVALID_CONFIG,
                "Failed to create HoneyBadger engine"
            )

        self._instance_id = instance_id
        self._party_id = party_id
        self._n_parties = n_parties
        self._threshold = threshold

    def __del__(self):
        """Free the engine resources"""
        if hasattr(self, "_handle") and self._handle:
            self._ffi._lib.hb_engine_free(self._handle)
            self._handle = None

    @property
    def instance_id(self) -> int:
        """Get the instance ID"""
        return self._instance_id

    @property
    def party_id(self) -> int:
        """Get this party's ID"""
        return self._party_id

    @property
    def n_parties(self) -> int:
        """Get the total number of parties"""
        return self._n_parties

    @property
    def threshold(self) -> int:
        """Get the corruption tolerance threshold"""
        return self._threshold

    @property
    def protocol_name(self) -> str:
        """Get the protocol name"""
        name = self._ffi._lib.hb_engine_protocol_name(self._handle)
        return name.decode("utf-8") if name else "HoneyBadger"

    def is_ready(self) -> bool:
        """Check if preprocessing is complete"""
        return bool(self._ffi._lib.hb_engine_is_ready(self._handle))

    def start_preprocessing(self) -> None:
        """
        Run the preprocessing phase (blocking)

        Generates Beaver triples and random shares needed for computation.
        Must be called before any multiply or open operations.

        Raises:
            HBEngineError: If preprocessing fails
        """
        result = self._ffi._lib.hb_engine_start_async(self._handle)
        if result != 0:
            raise HBEngineError(HBEngineErrorCode(result))

    def multiply(
        self,
        left: bytes,
        right: bytes,
        kind: ShareTypeKind = ShareTypeKind.INT,
        width: int = 64,
    ) -> bytes:
        """
        Perform secure multiplication on two shares

        Args:
            left: Left operand share bytes
            right: Right operand share bytes
            kind: Type of the shares (INT, BOOL, FLOAT)
            width: Bit width for integer types

        Returns:
            Result share as bytes

        Raises:
            HBEngineError: If not ready or multiplication fails
        """
        if not self.is_ready():
            raise HBEngineError(HBEngineErrorCode.NOT_READY)

        share_type = CShareType(kind=kind, width=width)

        left_arr = (c_uint8 * len(left)).from_buffer_copy(left)
        right_arr = (c_uint8 * len(right)).from_buffer_copy(right)

        result_ptr = POINTER(c_uint8)()
        result_len = c_size_t()

        ret = self._ffi._lib.hb_engine_multiply_share_async(
            self._handle,
            share_type,
            left_arr,
            len(left),
            right_arr,
            len(right),
            ctypes.byref(result_ptr),
            ctypes.byref(result_len),
        )

        if ret != 0:
            raise HBEngineError(HBEngineErrorCode(ret))

        try:
            result = bytes(result_ptr[:result_len.value])
            return result
        finally:
            self._ffi._lib.hb_free_bytes(result_ptr, result_len.value)

    def open(
        self,
        share: bytes,
        kind: ShareTypeKind = ShareTypeKind.INT,
        width: int = 64,
    ) -> int:
        """
        Reconstruct (open) a secret-shared value

        Args:
            share: Share bytes to reconstruct
            kind: Type of the share
            width: Bit width for integer types

        Returns:
            Reconstructed integer value

        Raises:
            HBEngineError: If reconstruction fails
        """
        if not self.is_ready():
            raise HBEngineError(HBEngineErrorCode.NOT_READY)

        share_type = CShareType(kind=kind, width=width)
        share_arr = (c_uint8 * len(share)).from_buffer_copy(share)

        result = CStoffelValue()

        ret = self._ffi._lib.hb_engine_open_share(
            self._handle,
            share_type,
            share_arr,
            len(share),
            ctypes.byref(result),
        )

        if ret != 0:
            raise HBEngineError(HBEngineErrorCode(ret))

        # Convert CStoffelValue to Python value
        if result.value_type == StoffelValueType.INT:
            return result.data.int_val
        elif result.value_type == StoffelValueType.BOOL:
            return result.data.bool_val
        elif result.value_type == StoffelValueType.FLOAT:
            return result.data.float_val
        else:
            return result.data.int_val

    def init_client_input(self, client_id: int, shares_data: bytes) -> None:
        """
        Initialize input shares from a client

        Args:
            client_id: Client identifier
            shares_data: Serialized shares (bincode format)

        Raises:
            HBEngineError: If initialization fails
        """
        data_arr = (c_uint8 * len(shares_data)).from_buffer_copy(shares_data)

        ret = self._ffi._lib.hb_engine_init_client_input(
            self._handle,
            client_id,
            data_arr,
            len(shares_data),
        )

        if ret != 0:
            raise HBEngineError(HBEngineErrorCode(ret))

    def get_client_shares(self, client_id: int) -> bytes:
        """
        Get shares for a specific client

        Args:
            client_id: Client identifier

        Returns:
            Serialized shares (bincode format)

        Raises:
            HBEngineError: If retrieval fails
        """
        result_ptr = POINTER(c_uint8)()
        result_len = c_size_t()

        ret = self._ffi._lib.hb_engine_get_client_shares(
            self._handle,
            client_id,
            ctypes.byref(result_ptr),
            ctypes.byref(result_len),
        )

        if ret != 0:
            raise HBEngineError(HBEngineErrorCode(ret))

        try:
            return bytes(result_ptr[:result_len.value])
        finally:
            self._ffi._lib.hb_free_bytes(result_ptr, result_len.value)

    def get_network(self) -> Optional[int]:
        """
        Get a cloned network handle

        Returns:
            Network handle pointer, or None if not available

        Note:
            Caller is responsible for freeing with hb_network_free
        """
        ptr = self._ffi._lib.hb_engine_get_network(self._handle)
        return ptr if ptr else None

    def free_network(self, network_ptr: int) -> None:
        """Free a network handle obtained from get_network"""
        if network_ptr:
            self._ffi._lib.hb_network_free(c_void_p(network_ptr))


__all__ = [
    "HBEngineErrorCode",
    "HBEngineError",
    "ShareTypeKind",
    "CShareType",
    "StoffelValueType",
    "CStoffelValue",
    "HBEngineFFI",
    "get_hb_engine_ffi",
    "is_hb_engine_available",
    "HoneyBadgerMpcEngine",
]
