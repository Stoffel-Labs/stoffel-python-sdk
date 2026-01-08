"""
Stoffel Networking FFI bindings using ctypes

Provides direct access to stoffel-networking (QUIC-based networking for MPC).
This enables:
- Runtime management (tokio async runtime)
- Network manager for peer connections
- Peer-to-peer message sending/receiving
"""

import ctypes
from ctypes import (
    Structure, POINTER, CFUNCTYPE,
    c_int32, c_uint8, c_uint64, c_size_t, c_void_p, c_char_p
)
from enum import IntEnum
from typing import Optional, Tuple, Callable
import os
import platform


class StoffelNetError(IntEnum):
    """Error codes for stoffel-networking operations"""
    OK = 0
    NULL_POINTER = -1
    INVALID_ADDRESS = -2
    CONNECTION = -3
    SEND = -4
    RECEIVE = -5
    TIMEOUT = -6
    PARTY_NOT_FOUND = -7
    RUNTIME = -8
    INVALID_UTF8 = -9
    CANCELLED = -10


class ConnectionState(IntEnum):
    """Connection state constants"""
    CONNECTED = 0
    CLOSING = 1
    CLOSED = 2
    DISCONNECTED = 3


class NetworkError(Exception):
    """Exception raised for networking errors"""
    def __init__(self, code: StoffelNetError, message: str = ""):
        self.code = code
        self.message = message or self._default_message(code)
        super().__init__(f"{self.code.name}: {self.message}")

    @staticmethod
    def _default_message(code: StoffelNetError) -> str:
        messages = {
            StoffelNetError.OK: "Success",
            StoffelNetError.NULL_POINTER: "Null pointer provided",
            StoffelNetError.INVALID_ADDRESS: "Invalid network address format",
            StoffelNetError.CONNECTION: "Connection establishment failed",
            StoffelNetError.SEND: "Send operation failed",
            StoffelNetError.RECEIVE: "Receive operation failed",
            StoffelNetError.TIMEOUT: "Operation timed out",
            StoffelNetError.PARTY_NOT_FOUND: "Party not found in network",
            StoffelNetError.RUNTIME: "Runtime error occurred",
            StoffelNetError.INVALID_UTF8: "Invalid UTF-8 string",
            StoffelNetError.CANCELLED: "Operation cancelled",
        }
        return messages.get(code, "Unknown error")


# Callback types
ConnectCallback = CFUNCTYPE(None, c_int32, c_void_p)
ReceiveCallback = CFUNCTYPE(None, c_int32, POINTER(c_uint8), c_size_t, c_void_p)
SendCallback = CFUNCTYPE(None, c_int32, c_void_p)


def _load_library() -> ctypes.CDLL:
    """Load the stoffel-networking library"""
    system = platform.system()
    if system == "Darwin":
        lib_names = ["libstoffelnet.dylib", "libstoffel_networking.dylib"]
    elif system == "Windows":
        lib_names = ["stoffelnet.dll", "libstoffelnet.dll"]
    else:
        lib_names = ["libstoffelnet.so", "libstoffel_networking.so"]

    search_paths = [
        ".",
        "./target/release",
        "./target/debug",
        "./external/stoffel-networking/target/release",
        "./external/stoffel-networking/target/debug",
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
        "Could not find stoffel-networking library. "
        "Build with 'cargo build --release' in external/stoffel-networking"
    )


class NetworkFFI:
    """Low-level FFI interface to stoffel-networking"""

    def __init__(self, library_path: Optional[str] = None):
        if library_path:
            self._lib = ctypes.CDLL(library_path)
        else:
            self._lib = _load_library()

        self._setup_functions()

    def _setup_functions(self):
        """Set up C function signatures"""
        # Error handling
        self._lib.stoffelnet_last_error.argtypes = []
        self._lib.stoffelnet_last_error.restype = c_char_p

        self._lib.stoffelnet_clear_error.argtypes = []
        self._lib.stoffelnet_clear_error.restype = None

        # Runtime management
        self._lib.stoffelnet_runtime_new.argtypes = []
        self._lib.stoffelnet_runtime_new.restype = c_void_p

        self._lib.stoffelnet_runtime_destroy.argtypes = [c_void_p]
        self._lib.stoffelnet_runtime_destroy.restype = None

        # Node management
        self._lib.stoffelnet_node_new.argtypes = [c_char_p, c_uint64]
        self._lib.stoffelnet_node_new.restype = c_void_p

        self._lib.stoffelnet_node_new_random_id.argtypes = [c_char_p]
        self._lib.stoffelnet_node_new_random_id.restype = c_void_p

        self._lib.stoffelnet_node_destroy.argtypes = [c_void_p]
        self._lib.stoffelnet_node_destroy.restype = None

        self._lib.stoffelnet_node_address.argtypes = [c_void_p]
        self._lib.stoffelnet_node_address.restype = c_char_p

        self._lib.stoffelnet_node_party_id.argtypes = [c_void_p]
        self._lib.stoffelnet_node_party_id.restype = c_uint64

        # Network manager
        self._lib.stoffelnet_manager_new.argtypes = [
            c_void_p,   # runtime
            c_char_p,   # bind_address
            c_uint64,   # party_id
        ]
        self._lib.stoffelnet_manager_new.restype = c_void_p

        self._lib.stoffelnet_manager_destroy.argtypes = [c_void_p]
        self._lib.stoffelnet_manager_destroy.restype = None

        self._lib.stoffelnet_manager_add_node.argtypes = [
            c_void_p,   # manager
            c_char_p,   # address
            c_uint64,   # party_id
        ]
        self._lib.stoffelnet_manager_add_node.restype = c_int32

        self._lib.stoffelnet_manager_connect_to_party.argtypes = [
            c_void_p,   # manager
            c_uint64,   # party_id
        ]
        self._lib.stoffelnet_manager_connect_to_party.restype = c_int32

        self._lib.stoffelnet_manager_connect_to_party_async.argtypes = [
            c_void_p,         # manager
            c_uint64,         # party_id
            ConnectCallback,  # callback
            c_void_p,         # user_data
        ]
        self._lib.stoffelnet_manager_connect_to_party_async.restype = c_void_p

        self._lib.stoffelnet_manager_accept_connection.argtypes = [
            c_void_p,           # manager
            POINTER(c_uint64),  # out_party_id
        ]
        self._lib.stoffelnet_manager_accept_connection.restype = c_int32

        self._lib.stoffelnet_manager_get_connection.argtypes = [
            c_void_p,   # manager
            c_uint64,   # party_id
        ]
        self._lib.stoffelnet_manager_get_connection.restype = c_void_p

        self._lib.stoffelnet_manager_is_party_connected.argtypes = [
            c_void_p,   # manager
            c_uint64,   # party_id
        ]
        self._lib.stoffelnet_manager_is_party_connected.restype = c_int32

        # Peer connection
        self._lib.stoffelnet_connection_send.argtypes = [
            c_void_p,           # conn
            c_void_p,           # runtime
            POINTER(c_uint8),   # data
            c_size_t,           # data_len
        ]
        self._lib.stoffelnet_connection_send.restype = c_int32

        self._lib.stoffelnet_connection_receive.argtypes = [
            c_void_p,                   # conn
            c_void_p,                   # runtime
            POINTER(POINTER(c_uint8)),  # out_data
            POINTER(c_size_t),          # out_len
        ]
        self._lib.stoffelnet_connection_receive.restype = c_int32

        self._lib.stoffelnet_connection_send_async.argtypes = [
            c_void_p,           # conn
            c_void_p,           # runtime
            POINTER(c_uint8),   # data
            c_size_t,           # data_len
            SendCallback,       # callback
            c_void_p,           # user_data
        ]
        self._lib.stoffelnet_connection_send_async.restype = c_void_p

        self._lib.stoffelnet_connection_receive_async.argtypes = [
            c_void_p,         # conn
            c_void_p,         # runtime
            ReceiveCallback,  # callback
            c_void_p,         # user_data
        ]
        self._lib.stoffelnet_connection_receive_async.restype = c_void_p

        self._lib.stoffelnet_async_cancel.argtypes = [c_void_p]
        self._lib.stoffelnet_async_cancel.restype = c_int32

        self._lib.stoffelnet_connection_state.argtypes = [c_void_p, c_void_p]
        self._lib.stoffelnet_connection_state.restype = c_int32

        self._lib.stoffelnet_connection_is_connected.argtypes = [c_void_p, c_void_p]
        self._lib.stoffelnet_connection_is_connected.restype = c_int32

        self._lib.stoffelnet_connection_close.argtypes = [c_void_p, c_void_p]
        self._lib.stoffelnet_connection_close.restype = None

        self._lib.stoffelnet_connection_destroy.argtypes = [c_void_p]
        self._lib.stoffelnet_connection_destroy.restype = None

        # Memory management
        self._lib.stoffelnet_free_bytes.argtypes = [POINTER(c_uint8), c_size_t]
        self._lib.stoffelnet_free_bytes.restype = None

        self._lib.stoffelnet_free_string.argtypes = [c_char_p]
        self._lib.stoffelnet_free_string.restype = None


# Global FFI instance
_ffi: Optional[NetworkFFI] = None


def get_network_ffi() -> NetworkFFI:
    """Get or create the global NetworkFFI instance"""
    global _ffi
    if _ffi is None:
        _ffi = NetworkFFI()
    return _ffi


def is_network_available() -> bool:
    """Check if network FFI is available"""
    try:
        get_network_ffi()
        return True
    except (RuntimeError, OSError):
        return False


class TokioRuntime:
    """Tokio async runtime wrapper"""

    def __init__(self):
        """Create a new tokio runtime"""
        self._ffi = get_network_ffi()
        self._handle = self._ffi._lib.stoffelnet_runtime_new()

        if not self._handle:
            error = self._ffi._lib.stoffelnet_last_error()
            msg = error.decode("utf-8") if error else "Unknown error"
            raise NetworkError(StoffelNetError.RUNTIME, msg)

    def __del__(self):
        """Destroy the runtime"""
        if hasattr(self, "_handle") and self._handle:
            self._ffi._lib.stoffelnet_runtime_destroy(self._handle)
            self._handle = None

    @property
    def handle(self) -> int:
        """Get the raw handle pointer"""
        return self._handle


class NetworkNode:
    """Network node representation"""

    def __init__(self, address: str, party_id: Optional[int] = None):
        """
        Create a new node

        Args:
            address: Network address (e.g., "127.0.0.1:9000")
            party_id: Party ID, or None for random UUID-based ID
        """
        self._ffi = get_network_ffi()

        addr_bytes = address.encode("utf-8")
        if party_id is not None:
            self._handle = self._ffi._lib.stoffelnet_node_new(addr_bytes, party_id)
        else:
            self._handle = self._ffi._lib.stoffelnet_node_new_random_id(addr_bytes)

        if not self._handle:
            error = self._ffi._lib.stoffelnet_last_error()
            msg = error.decode("utf-8") if error else "Unknown error"
            raise NetworkError(StoffelNetError.INVALID_ADDRESS, msg)

    def __del__(self):
        """Destroy the node"""
        if hasattr(self, "_handle") and self._handle:
            self._ffi._lib.stoffelnet_node_destroy(self._handle)
            self._handle = None

    @property
    def address(self) -> str:
        """Get the node address"""
        addr = self._ffi._lib.stoffelnet_node_address(self._handle)
        if addr:
            result = addr.decode("utf-8")
            self._ffi._lib.stoffelnet_free_string(addr)
            return result
        return ""

    @property
    def party_id(self) -> int:
        """Get the party ID"""
        return self._ffi._lib.stoffelnet_node_party_id(self._handle)


class NetworkManager:
    """
    QUIC-based network manager for MPC communication

    Usage:
        runtime = TokioRuntime()
        manager = NetworkManager(runtime, "0.0.0.0:9000", party_id=0)

        # Add peers
        manager.add_node("192.168.1.2:9000", party_id=1)
        manager.add_node("192.168.1.3:9000", party_id=2)

        # Connect to peers
        manager.connect_to_party(1)
        manager.connect_to_party(2)

        # Send/receive messages
        conn = manager.get_connection(1)
        conn.send(b"hello")
        data = conn.receive()
    """

    def __init__(self, runtime: TokioRuntime, bind_address: str, party_id: int):
        """
        Create a new network manager

        Args:
            runtime: Tokio runtime for async operations
            bind_address: Address to bind for incoming connections
            party_id: This node's party ID
        """
        self._ffi = get_network_ffi()
        self._runtime = runtime

        addr_bytes = bind_address.encode("utf-8")
        self._handle = self._ffi._lib.stoffelnet_manager_new(
            runtime.handle,
            addr_bytes,
            party_id,
        )

        if not self._handle:
            error = self._ffi._lib.stoffelnet_last_error()
            msg = error.decode("utf-8") if error else "Unknown error"
            raise NetworkError(StoffelNetError.CONNECTION, msg)

        self._party_id = party_id

    def __del__(self):
        """Destroy the manager"""
        if hasattr(self, "_handle") and self._handle:
            self._ffi._lib.stoffelnet_manager_destroy(self._handle)
            self._handle = None

    @property
    def party_id(self) -> int:
        """Get this node's party ID"""
        return self._party_id

    def add_node(self, address: str, party_id: int) -> None:
        """
        Add a node to the network

        Args:
            address: Node's network address
            party_id: Node's party ID

        Raises:
            NetworkError: If adding fails
        """
        addr_bytes = address.encode("utf-8")
        result = self._ffi._lib.stoffelnet_manager_add_node(
            self._handle,
            addr_bytes,
            party_id,
        )

        if result != StoffelNetError.OK:
            raise NetworkError(StoffelNetError(result))

    def connect_to_party(self, party_id: int) -> None:
        """
        Connect to a party (blocking)

        Args:
            party_id: Party ID to connect to

        Raises:
            NetworkError: If connection fails
        """
        result = self._ffi._lib.stoffelnet_manager_connect_to_party(
            self._handle,
            party_id,
        )

        if result != StoffelNetError.OK:
            raise NetworkError(StoffelNetError(result))

    def accept_connection(self) -> int:
        """
        Accept an incoming connection (blocking)

        Returns:
            Party ID of the connected peer

        Raises:
            NetworkError: If accept fails
        """
        party_id = c_uint64()
        result = self._ffi._lib.stoffelnet_manager_accept_connection(
            self._handle,
            ctypes.byref(party_id),
        )

        if result != StoffelNetError.OK:
            raise NetworkError(StoffelNetError(result))

        return party_id.value

    def is_party_connected(self, party_id: int) -> bool:
        """Check if a party is connected"""
        return bool(self._ffi._lib.stoffelnet_manager_is_party_connected(
            self._handle,
            party_id,
        ))

    def get_connection(self, party_id: int) -> "PeerConnection":
        """
        Get a connection to a specific party

        Args:
            party_id: Party ID

        Returns:
            PeerConnection wrapper

        Raises:
            NetworkError: If party not connected
        """
        handle = self._ffi._lib.stoffelnet_manager_get_connection(
            self._handle,
            party_id,
        )

        if not handle:
            raise NetworkError(
                StoffelNetError.PARTY_NOT_FOUND,
                f"Party {party_id} not connected"
            )

        return PeerConnection(self._runtime, handle, owned=False)


class PeerConnection:
    """
    QUIC connection to a peer

    Supports blocking and async send/receive operations.
    """

    def __init__(
        self,
        runtime: TokioRuntime,
        handle: int,
        owned: bool = True,
    ):
        """
        Create a peer connection wrapper

        Args:
            runtime: Tokio runtime
            handle: Raw connection handle
            owned: Whether this wrapper owns (and should free) the handle
        """
        self._ffi = get_network_ffi()
        self._runtime = runtime
        self._handle = handle
        self._owned = owned
        self._callbacks = []  # Keep references to prevent GC

    def __del__(self):
        """Destroy the connection if owned"""
        if hasattr(self, "_owned") and self._owned and self._handle:
            self._ffi._lib.stoffelnet_connection_destroy(self._handle)
            self._handle = None

    @property
    def state(self) -> ConnectionState:
        """Get the connection state"""
        state = self._ffi._lib.stoffelnet_connection_state(
            self._handle,
            self._runtime.handle,
        )
        return ConnectionState(state) if state >= 0 else ConnectionState.DISCONNECTED

    @property
    def is_connected(self) -> bool:
        """Check if the connection is alive"""
        return bool(self._ffi._lib.stoffelnet_connection_is_connected(
            self._handle,
            self._runtime.handle,
        ))

    def send(self, data: bytes) -> None:
        """
        Send data (blocking)

        Args:
            data: Bytes to send

        Raises:
            NetworkError: If send fails
        """
        data_arr = (c_uint8 * len(data)).from_buffer_copy(data)
        result = self._ffi._lib.stoffelnet_connection_send(
            self._handle,
            self._runtime.handle,
            data_arr,
            len(data),
        )

        if result != StoffelNetError.OK:
            raise NetworkError(StoffelNetError(result))

    def receive(self) -> bytes:
        """
        Receive data (blocking)

        Returns:
            Received bytes

        Raises:
            NetworkError: If receive fails
        """
        data_ptr = POINTER(c_uint8)()
        data_len = c_size_t()

        result = self._ffi._lib.stoffelnet_connection_receive(
            self._handle,
            self._runtime.handle,
            ctypes.byref(data_ptr),
            ctypes.byref(data_len),
        )

        if result != StoffelNetError.OK:
            raise NetworkError(StoffelNetError(result))

        try:
            return bytes(data_ptr[:data_len.value])
        finally:
            self._ffi._lib.stoffelnet_free_bytes(data_ptr, data_len.value)

    def close(self) -> None:
        """Close the connection"""
        self._ffi._lib.stoffelnet_connection_close(
            self._handle,
            self._runtime.handle,
        )


__all__ = [
    "StoffelNetError",
    "ConnectionState",
    "NetworkError",
    "NetworkFFI",
    "get_network_ffi",
    "is_network_available",
    "TokioRuntime",
    "NetworkNode",
    "NetworkManager",
    "PeerConnection",
]
