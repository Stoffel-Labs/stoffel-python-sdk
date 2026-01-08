"""
Async QUIC Network wrapper

Provides asyncio-compatible wrapper around the QUIC FFI bindings.
Uses ThreadPoolExecutor to run blocking FFI calls without blocking
the event loop.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from ctypes import POINTER, c_void_p
from typing import Optional, Set, Dict, Union
import logging

from .quic_ffi import get_quic_ffi, is_quic_available
from .types import QuicNetworkOpaque, QuicPeerConnectionsOpaque, NetworkOpaque
from .errors import NetworkError

logger = logging.getLogger(__name__)


class QUICConnection:
    """
    Represents a connection to a peer

    This is a lightweight wrapper that tracks connection state
    and provides send/receive methods.
    """

    def __init__(self, network: "QUICNetwork", address: str):
        """
        Create connection wrapper

        Args:
            network: Parent QUICNetwork instance
            address: Remote peer address
        """
        self._network = network
        self._address = address
        self._connected = True

    @property
    def address(self) -> str:
        """Remote peer address"""
        return self._address

    @property
    def connected(self) -> bool:
        """Whether connection is active"""
        return self._connected and not self._network._closed

    async def send(self, data: bytes) -> None:
        """
        Send data to this peer

        Args:
            data: Data to send

        Raises:
            NetworkError: If send fails
        """
        await self._network.send(self._address, data)

    async def receive(self) -> bytes:
        """
        Receive data from this peer (blocking)

        Returns:
            Received data

        Raises:
            NetworkError: If receive fails
        """
        return await self._network.receive(self._address)

    def close(self) -> None:
        """Mark connection as closed"""
        self._connected = False


class QUICNetwork:
    """
    Async QUIC network manager

    Provides asyncio-compatible interface for QUIC networking.
    Uses a thread pool to run blocking FFI calls without blocking
    the event loop.

    Example:
        async def main():
            # For MPC, use party_id to ensure proper connection mapping
            network = QUICNetwork(party_id=0)
            await network.init()

            # Connect to peer
            conn = await network.connect("127.0.0.1:19200")

            # Send data
            await conn.send(b"hello")

            # Receive response
            data = await conn.receive()

            network.close()
    """

    def __init__(self, party_id: Optional[int] = None, max_workers: int = 4):
        """
        Create QUIC network manager

        Args:
            party_id: Party ID for MPC operations. If provided, ensures
                     consistent ID mapping for HoneyBadger preprocessing.
                     This is REQUIRED when using the network for MPC.
            max_workers: Max thread pool workers for concurrent FFI calls
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._ffi = get_quic_ffi()
        self._party_id = party_id

        self._network_ptr: Optional[POINTER(QuicNetworkOpaque)] = None
        self._connections_ptr: Optional[POINTER(QuicPeerConnectionsOpaque)] = None
        self._hb_network_ptr: Optional[POINTER(NetworkOpaque)] = None
        self._stoffelvm_network_ptr: Optional[c_void_p] = None

        self._connections: Dict[str, QUICConnection] = {}
        self._initialized = False
        self._listening = False
        self._closed = False

    @property
    def available(self) -> bool:
        """Check if QUIC is available"""
        return self._ffi.available

    @property
    def initialized(self) -> bool:
        """Check if network is initialized"""
        return self._initialized

    @property
    def listening(self) -> bool:
        """Check if network is listening for connections"""
        return self._listening

    async def init(self) -> None:
        """
        Initialize QUIC network

        Must be called before any other operations.
        Initializes TLS and creates network handles.
        """
        if self._initialized:
            return

        if not self.available:
            raise RuntimeError("QUIC FFI not available - native library not loaded")

        loop = asyncio.get_event_loop()

        # Initialize TLS (blocking, run in executor)
        await loop.run_in_executor(self._executor, self._ffi.init_tls)

        # Create network and connections (blocking, run in executor)
        # Use party_id version for MPC operations to ensure proper ID mapping
        if self._party_id is not None:
            def _create_network():
                return self._ffi.new_quic_network_with_party_id(self._party_id)
            logger.debug(f"Creating QUIC network with party_id={self._party_id}")
        else:
            def _create_network():
                return self._ffi.new_quic_network()

        self._network_ptr, self._connections_ptr = await loop.run_in_executor(
            self._executor, _create_network
        )

        self._initialized = True
        logger.debug("QUIC network initialized")

    async def listen(self, bind_address: str) -> None:
        """
        Start listening for incoming connections

        Args:
            bind_address: Local address to bind to (e.g., "0.0.0.0:19200")

        Raises:
            RuntimeError: If not initialized
            NetworkError: If listen fails
        """
        if not self._initialized:
            raise RuntimeError("Network not initialized - call init() first")

        loop = asyncio.get_event_loop()

        def _listen():
            self._ffi.quic_listen(self._network_ptr, bind_address)

        await loop.run_in_executor(self._executor, _listen)
        self._listening = True
        logger.info(f"QUIC network listening on {bind_address}")

    async def connect(self, address: str) -> QUICConnection:
        """
        Connect to a peer

        Args:
            address: Peer address (e.g., "127.0.0.1:19200")

        Returns:
            Connection wrapper for the peer

        Raises:
            RuntimeError: If not initialized
            NetworkError: If connection fails
        """
        if not self._initialized:
            raise RuntimeError("Network not initialized - call init() first")

        loop = asyncio.get_event_loop()

        def _connect():
            self._ffi.quic_connect(
                self._network_ptr,
                self._connections_ptr,
                address
            )

        await loop.run_in_executor(self._executor, _connect)

        conn = QUICConnection(self, address)
        self._connections[address] = conn
        logger.debug(f"Connected to {address}")

        return conn

    async def accept(self) -> QUICConnection:
        """
        Accept an incoming connection (blocking)

        Must call listen() first.

        Returns:
            Connection wrapper for the accepted peer

        Raises:
            RuntimeError: If not listening
            NetworkError: If accept fails
        """
        if not self._listening:
            raise RuntimeError("Not listening - call listen() first")

        loop = asyncio.get_event_loop()

        def _accept():
            return self._ffi.quic_accept(
                self._network_ptr,
                self._connections_ptr
            )

        address = await loop.run_in_executor(self._executor, _accept)

        conn = QUICConnection(self, address)
        self._connections[address] = conn
        logger.debug(f"Accepted connection from {address}")

        return conn

    async def send(self, address: str, data: bytes) -> None:
        """
        Send data to a peer

        Args:
            address: Peer address
            data: Data to send

        Raises:
            RuntimeError: If not initialized
            NetworkError: If send fails
        """
        if not self._initialized:
            raise RuntimeError("Network not initialized - call init() first")

        loop = asyncio.get_event_loop()

        def _send():
            self._ffi.quic_send(self._connections_ptr, address, data)

        await loop.run_in_executor(self._executor, _send)
        logger.debug(f"Sent {len(data)} bytes to {address}")

    async def receive(self, address: str) -> bytes:
        """
        Receive data from a peer (blocking)

        Args:
            address: Peer address to receive from

        Returns:
            Received data

        Raises:
            RuntimeError: If not initialized
            NetworkError: If receive fails
        """
        if not self._initialized:
            raise RuntimeError("Network not initialized - call init() first")

        loop = asyncio.get_event_loop()

        def _receive():
            return self._ffi.quic_receive_from_sync(self._connections_ptr, address)

        data = await loop.run_in_executor(self._executor, _receive)
        logger.debug(f"Received {len(data)} bytes from {address}")

        return data

    def get_hb_network(self) -> Optional[c_void_p]:
        """
        Get StoffelVM-compatible network handle for HoneyBadger MPC

        Converts the QUIC network to a raw pointer format that matches
        what StoffelVM's hb_engine_new() expects.

        Note: This consumes the QUIC network. After calling this,
        you should not use the connect/listen/send/receive methods
        directly - the network is now managed by HoneyBadger.

        Returns:
            Raw c_void_p pointer for StoffelVM's HoneyBadger engine,
            or None if extraction fails

        Raises:
            RuntimeError: If not initialized
        """
        # Return cached pointer if already extracted
        if self._stoffelvm_network_ptr is not None:
            return self._stoffelvm_network_ptr

        if not self._initialized:
            raise RuntimeError("Network not initialized - call init() first")

        # First convert QUIC to NetworkOpaque if not done yet
        if self._hb_network_ptr is None:
            self._hb_network_ptr = self._ffi.quic_into_hb_network(self._network_ptr)
            self._network_ptr = None  # Consumed
            logger.debug("Converted to HoneyBadger network")

        # Extract raw Arc<QuicNetworkManager> for StoffelVM
        self._stoffelvm_network_ptr = self._ffi.extract_quic_network(self._hb_network_ptr)
        logger.debug("Extracted StoffelVM-compatible network pointer")

        return self._stoffelvm_network_ptr

    def close(self) -> None:
        """
        Close network and free resources

        Safe to call multiple times.
        """
        if self._closed:
            return

        # Close all connections
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()

        # Free native resources
        # First free the extracted StoffelVM pointer if allocated
        if self._stoffelvm_network_ptr is not None:
            self._ffi.free_raw_quic_network(self._stoffelvm_network_ptr)
            self._stoffelvm_network_ptr = None

        if self._hb_network_ptr is not None:
            # HB network owns the resources now, don't free QUIC handles
            # The HB network will be freed when the MPC client/server is freed
            pass
        else:
            if self._network_ptr is not None:
                self._ffi.free_quic_network(self._network_ptr)
                self._network_ptr = None

            if self._connections_ptr is not None:
                self._ffi.free_quic_peer_connections(self._connections_ptr)
                self._connections_ptr = None

        self._executor.shutdown(wait=False)
        self._closed = True
        self._initialized = False
        self._listening = False

        logger.debug("QUIC network closed")

    def __del__(self):
        """Cleanup on garbage collection"""
        try:
            self.close()
        except Exception:
            pass

    async def __aenter__(self) -> "QUICNetwork":
        """Async context manager entry"""
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        self.close()
