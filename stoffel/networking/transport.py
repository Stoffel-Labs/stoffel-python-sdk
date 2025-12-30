"""
Transport layer for MPC networking

Provides async TCP transport for MPC communication.
Uses asyncio streams for reliable, ordered message delivery.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from .messages import MPCMessage, serialize_message, deserialize_message


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection lifecycle states"""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    HANDSHAKING = auto()
    READY = auto()
    CLOSING = auto()
    CLOSED = auto()
    ERROR = auto()


@dataclass
class MPCConnection:
    """
    Represents a connection to an MPC peer

    Attributes:
        peer_id: The party ID of the connected peer
        address: Network address (host:port)
        state: Current connection state
        reader: Async stream reader
        writer: Async stream writer
    """
    peer_id: int
    address: str
    state: ConnectionState = ConnectionState.DISCONNECTED
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    _recv_buffer: bytes = field(default_factory=bytes)
    _recv_task: Optional[asyncio.Task] = None

    async def send(self, message: MPCMessage) -> None:
        """
        Send a message to this peer

        Args:
            message: The MPC message to send

        Raises:
            ConnectionError: If not connected
        """
        allowed_states = (
            ConnectionState.READY,
            ConnectionState.CONNECTED,
            ConnectionState.HANDSHAKING,
        )
        if self.state not in allowed_states:
            raise ConnectionError(
                f"Cannot send to peer {self.peer_id}: state is {self.state.name}"
            )

        if self.writer is None:
            raise ConnectionError(f"No writer for peer {self.peer_id}")

        data = serialize_message(message)
        self.writer.write(data)
        await self.writer.drain()

    async def recv(self) -> MPCMessage:
        """
        Receive a message from this peer

        Returns:
            The received MPC message

        Raises:
            ConnectionError: If not connected or connection closed
        """
        if self.reader is None:
            raise ConnectionError(f"No reader for peer {self.peer_id}")

        # Read until we have a complete message
        while True:
            # Try to parse from buffer first
            if len(self._recv_buffer) >= 4:
                try:
                    msg, consumed = deserialize_message(self._recv_buffer)
                    self._recv_buffer = self._recv_buffer[consumed:]
                    return msg
                except ValueError:
                    # Not enough data yet
                    pass

            # Read more data
            chunk = await self.reader.read(4096)
            if not chunk:
                raise ConnectionError(f"Connection to peer {self.peer_id} closed")

            self._recv_buffer += chunk

    async def close(self) -> None:
        """Close the connection"""
        self.state = ConnectionState.CLOSING

        if self._recv_task is not None:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass

        if self.writer is not None:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass

        self.state = ConnectionState.CLOSED
        self.reader = None
        self.writer = None


class MPCTransport(ABC):
    """
    Abstract base class for MPC transport

    Subclasses implement specific transport protocols (TCP, QUIC, etc.)
    """

    @abstractmethod
    async def connect(self, address: str, peer_id: int) -> MPCConnection:
        """
        Connect to a peer

        Args:
            address: Network address (host:port)
            peer_id: The party ID of the peer

        Returns:
            MPCConnection instance
        """
        pass

    @abstractmethod
    async def listen(
        self,
        address: str,
        on_connection: Callable[[MPCConnection], Coroutine[Any, Any, None]]
    ) -> None:
        """
        Start listening for incoming connections

        Args:
            address: Address to bind to (host:port)
            on_connection: Callback for new connections
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport and all connections"""
        pass


class TCPTransport(MPCTransport):
    """
    TCP transport for MPC communication

    Uses asyncio streams for reliable, ordered message delivery.
    Suitable for local networks and testing. For production use
    over the internet, consider QUIC transport for better security
    and performance.
    """

    def __init__(
        self,
        local_id: int,
        connect_timeout: float = 10.0,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize TCP transport

        Args:
            local_id: This party's ID
            connect_timeout: Connection timeout in seconds
            retry_count: Number of connection retries
            retry_delay: Delay between retries in seconds
        """
        self._local_id = local_id
        self._connect_timeout = connect_timeout
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        self._connections: Dict[int, MPCConnection] = {}
        self._server: Optional[asyncio.Server] = None
        self._running = False

    async def connect(
        self,
        address: str,
        peer_id: int,
    ) -> MPCConnection:
        """
        Connect to a peer with retry logic

        Args:
            address: Network address (host:port)
            peer_id: The party ID of the peer

        Returns:
            MPCConnection instance

        Raises:
            ConnectionError: If connection fails after retries
        """
        # Check if already connected
        if peer_id in self._connections:
            conn = self._connections[peer_id]
            if conn.state == ConnectionState.READY:
                return conn

        # Parse address
        if ":" in address:
            host, port_str = address.rsplit(":", 1)
            port = int(port_str)
        else:
            raise ValueError(f"Invalid address format: {address}")

        # Create connection object
        conn = MPCConnection(peer_id=peer_id, address=address)
        conn.state = ConnectionState.CONNECTING

        # Try to connect with retries
        last_error = None
        for attempt in range(self._retry_count):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=self._connect_timeout,
                )

                conn.reader = reader
                conn.writer = writer
                conn.state = ConnectionState.CONNECTED

                self._connections[peer_id] = conn
                logger.info(f"Connected to peer {peer_id} at {address}")
                return conn

            except asyncio.TimeoutError:
                last_error = f"Connection to {address} timed out"
                logger.warning(f"Attempt {attempt + 1}/{self._retry_count}: {last_error}")
            except OSError as e:
                last_error = f"Connection to {address} failed: {e}"
                logger.warning(f"Attempt {attempt + 1}/{self._retry_count}: {last_error}")

            if attempt < self._retry_count - 1:
                await asyncio.sleep(self._retry_delay)

        conn.state = ConnectionState.ERROR
        raise ConnectionError(last_error)

    async def listen(
        self,
        address: str,
        on_connection: Callable[[MPCConnection], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Start listening for incoming connections

        Args:
            address: Address to bind to (host:port)
            on_connection: Async callback for new connections
        """
        # Parse address
        if ":" in address:
            host, port_str = address.rsplit(":", 1)
            port = int(port_str)
        else:
            host = "0.0.0.0"
            port = int(address)

        async def handle_client(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
        ):
            # Get peer address
            peer_addr = writer.get_extra_info("peername")
            logger.info(f"Incoming connection from {peer_addr}")

            # Create connection (peer_id will be set during handshake)
            conn = MPCConnection(
                peer_id=-1,  # Unknown until handshake
                address=f"{peer_addr[0]}:{peer_addr[1]}",
                state=ConnectionState.CONNECTED,
                reader=reader,
                writer=writer,
            )

            try:
                await on_connection(conn)
            except Exception as e:
                logger.error(f"Error handling connection from {peer_addr}: {e}")
                await conn.close()

        self._server = await asyncio.start_server(
            handle_client,
            host,
            port,
            reuse_address=True,
        )

        self._running = True
        logger.info(f"Listening on {host}:{port}")

        async with self._server:
            await self._server.serve_forever()

    async def close(self) -> None:
        """Close the transport and all connections"""
        self._running = False

        # Close server
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

        # Close all connections
        for conn in self._connections.values():
            await conn.close()

        self._connections.clear()

    def get_connection(self, peer_id: int) -> Optional[MPCConnection]:
        """Get an existing connection by peer ID"""
        return self._connections.get(peer_id)

    def add_connection(self, peer_id: int, conn: MPCConnection) -> None:
        """Register a connection (e.g., from incoming connection after handshake)"""
        conn.peer_id = peer_id
        self._connections[peer_id] = conn
