"""
QUIC Network FFI bindings

Raw ctypes bindings for QUIC networking functions from mpc-protocols.
Based on: mpc-protocols/mpc/src/ffi/honey_badger_bindings.h

These are low-level FFI wrappers. For async operations, use the
network.py module which wraps these in asyncio-compatible APIs.
"""

import ctypes
from ctypes import POINTER, c_char_p, c_int, c_size_t, c_void_p
from typing import Optional, Tuple

from ._lib_loader import get_mpc_library, LibraryLoadError
from .types import (
    ByteSlice,
    QuicNetworkOpaque,
    QuicPeerConnectionsOpaque,
    NetworkOpaque,
)
from .errors import (
    NetworkErrorCode,
    NetworkError,
    check_network_error,
)


class QUICFunctions:
    """
    Raw QUIC FFI function bindings

    This class provides direct access to the C FFI functions for QUIC
    networking. Functions are lazily initialized on first use.
    """

    _instance: Optional["QUICFunctions"] = None
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
        """Check if QUIC FFI functions are available"""
        return self._lib is not None

    def _setup_functions(self):
        """Set up C function signatures"""
        lib = self._lib

        # init_tls - Must be called before using QUIC network
        lib.init_tls.argtypes = []
        lib.init_tls.restype = None

        # new_quic_network - Create QUIC network instance
        lib.new_quic_network.argtypes = [
            POINTER(POINTER(QuicPeerConnectionsOpaque)),  # returned_connections
        ]
        lib.new_quic_network.restype = POINTER(QuicNetworkOpaque)

        # quic_connect - Connect to a peer
        lib.quic_connect.argtypes = [
            POINTER(QuicNetworkOpaque),       # quic_network_ptr
            POINTER(QuicPeerConnectionsOpaque),  # peer_connections
            c_char_p,                          # addr
        ]
        lib.quic_connect.restype = c_int  # NetworkErrorCode

        # quic_accept - Accept incoming connection (blocking)
        lib.quic_accept.argtypes = [
            POINTER(QuicNetworkOpaque),       # quic_network_ptr
            POINTER(QuicPeerConnectionsOpaque),  # peer_connections
            POINTER(c_char_p),                # connected_addr (output)
        ]
        lib.quic_accept.restype = c_int  # NetworkErrorCode

        # quic_listen - Listen for incoming connections
        lib.quic_listen.argtypes = [
            POINTER(QuicNetworkOpaque),       # quic_network_ptr
            c_char_p,                          # bind_address
        ]
        lib.quic_listen.restype = c_int  # NetworkErrorCode

        # quic_into_hb_network - Convert QUIC network to HoneyBadger network
        lib.quic_into_hb_network.argtypes = [
            POINTER(POINTER(QuicNetworkOpaque)),  # quic_network_ptr (consumed)
        ]
        lib.quic_into_hb_network.restype = POINTER(NetworkOpaque)

        # quic_receive_from_sync - Receive message (blocking)
        lib.quic_receive_from_sync.argtypes = [
            POINTER(QuicPeerConnectionsOpaque),  # peer_connections
            c_char_p,                             # addr
            POINTER(ByteSlice),                   # msg (output)
        ]
        lib.quic_receive_from_sync.restype = c_int  # NetworkErrorCode

        # quic_send - Send message
        lib.quic_send.argtypes = [
            POINTER(QuicPeerConnectionsOpaque),  # peer_connections
            c_char_p,                             # recp
            ByteSlice,                            # msg
        ]
        lib.quic_send.restype = c_int  # NetworkErrorCode

        # free_quic_network
        lib.free_quic_network.argtypes = [POINTER(QuicNetworkOpaque)]
        lib.free_quic_network.restype = None

        # free_quic_peer_connections
        lib.free_quic_peer_connections.argtypes = [POINTER(QuicPeerConnectionsOpaque)]
        lib.free_quic_peer_connections.restype = None

        # free_c_string - Free C string allocated by Rust
        lib.free_c_string.argtypes = [c_char_p]
        lib.free_c_string.restype = None

        # free_bytes_slice
        lib.free_bytes_slice.argtypes = [ByteSlice]
        lib.free_bytes_slice.restype = None

    def init_tls(self) -> None:
        """
        Initialize TLS crypto provider for QUIC

        Must be called before creating any QUIC network.
        Safe to call multiple times - this wrapper ensures idempotency
        since the underlying Rust code panics if called twice.
        """
        # Guard against multiple calls - rustls only allows installing
        # the crypto provider once per process
        if getattr(self, '_tls_initialized', False):
            return  # Already initialized, skip

        if not self.available:
            raise LibraryLoadError("MPC library not available")

        self._lib.init_tls()
        self._tls_initialized = True

    def new_quic_network(self) -> Tuple[POINTER(QuicNetworkOpaque), POINTER(QuicPeerConnectionsOpaque)]:
        """
        Create a new QUIC network instance

        Returns:
            Tuple of (QuicNetwork pointer, PeerConnections pointer)
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        connections_ptr = POINTER(QuicPeerConnectionsOpaque)()
        network_ptr = self._lib.new_quic_network(ctypes.byref(connections_ptr))

        return network_ptr, connections_ptr

    def quic_connect(
        self,
        network_ptr: POINTER(QuicNetworkOpaque),
        connections_ptr: POINTER(QuicPeerConnectionsOpaque),
        address: str
    ) -> None:
        """
        Connect to a peer at the specified address

        Args:
            network_ptr: QUIC network handle
            connections_ptr: Peer connections map
            address: Peer address (e.g., "127.0.0.1:19200")

        Raises:
            NetworkError: If connection fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        addr_bytes = address.encode('utf-8')
        result = self._lib.quic_connect(network_ptr, connections_ptr, addr_bytes)
        check_network_error(result, f"quic_connect to {address}")

    def quic_accept(
        self,
        network_ptr: POINTER(QuicNetworkOpaque),
        connections_ptr: POINTER(QuicPeerConnectionsOpaque)
    ) -> str:
        """
        Accept an incoming connection (blocking)

        Args:
            network_ptr: QUIC network handle
            connections_ptr: Peer connections map

        Returns:
            Address of the connected peer

        Raises:
            NetworkError: If accept fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        connected_addr = c_char_p()
        result = self._lib.quic_accept(
            network_ptr,
            connections_ptr,
            ctypes.byref(connected_addr)
        )
        check_network_error(result, "quic_accept")

        # Extract address and free C string
        if connected_addr.value:
            addr = connected_addr.value.decode('utf-8')
            self._lib.free_c_string(connected_addr)
            return addr
        return ""

    def quic_listen(
        self,
        network_ptr: POINTER(QuicNetworkOpaque),
        bind_address: str
    ) -> None:
        """
        Start listening for incoming connections

        Args:
            network_ptr: QUIC network handle
            bind_address: Local address to bind to (e.g., "0.0.0.0:19200")

        Raises:
            NetworkError: If listen fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        addr_bytes = bind_address.encode('utf-8')
        result = self._lib.quic_listen(network_ptr, addr_bytes)
        check_network_error(result, f"quic_listen on {bind_address}")

    def quic_into_hb_network(
        self,
        network_ptr: POINTER(QuicNetworkOpaque)
    ) -> POINTER(NetworkOpaque):
        """
        Convert QUIC network to HoneyBadger network

        Note: This consumes the QUIC network pointer. Do not use
        the original pointer after calling this.

        Args:
            network_ptr: QUIC network handle (will be consumed)

        Returns:
            Generic network handle for HoneyBadger MPC
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        # Create pointer to pointer for consumption
        ptr_holder = ctypes.pointer(network_ptr)
        return self._lib.quic_into_hb_network(ptr_holder)

    def quic_send(
        self,
        connections_ptr: POINTER(QuicPeerConnectionsOpaque),
        recipient: str,
        data: bytes
    ) -> None:
        """
        Send data to a peer

        Args:
            connections_ptr: Peer connections map
            recipient: Recipient address
            data: Data to send

        Raises:
            NetworkError: If send fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        msg = ByteSlice.from_bytes(data)
        addr_bytes = recipient.encode('utf-8')

        result = self._lib.quic_send(connections_ptr, addr_bytes, msg)
        check_network_error(result, f"quic_send to {recipient}")

    def quic_receive_from_sync(
        self,
        connections_ptr: POINTER(QuicPeerConnectionsOpaque),
        sender: str
    ) -> bytes:
        """
        Receive data from a peer (blocking)

        Args:
            connections_ptr: Peer connections map
            sender: Sender address to receive from

        Returns:
            Received data

        Raises:
            NetworkError: If receive fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        msg = ByteSlice()
        addr_bytes = sender.encode('utf-8')

        result = self._lib.quic_receive_from_sync(
            connections_ptr,
            addr_bytes,
            ctypes.byref(msg)
        )
        check_network_error(result, f"quic_receive_from_sync from {sender}")

        # Copy bytes before freeing
        data = msg.to_bytes()
        if msg.pointer:
            self._lib.free_bytes_slice(msg)

        return data

    def free_quic_network(self, network_ptr: POINTER(QuicNetworkOpaque)) -> None:
        """Free QUIC network handle"""
        if self.available and network_ptr:
            self._lib.free_quic_network(network_ptr)

    def free_quic_peer_connections(
        self,
        connections_ptr: POINTER(QuicPeerConnectionsOpaque)
    ) -> None:
        """Free peer connections map"""
        if self.available and connections_ptr:
            self._lib.free_quic_peer_connections(connections_ptr)


# Global singleton instance
_quic_ffi: Optional[QUICFunctions] = None


def get_quic_ffi() -> QUICFunctions:
    """Get the QUIC FFI singleton"""
    global _quic_ffi
    if _quic_ffi is None:
        _quic_ffi = QUICFunctions()
    return _quic_ffi


def is_quic_available() -> bool:
    """Check if QUIC FFI is available"""
    return get_quic_ffi().available
