"""
Stoffel MPC Server

Provides the server API for running Stoffel MPC compute nodes.
Matches the Rust SDK's StoffelServer API.

Example:
    # Create and start server
    server = Stoffel.server(party_id=0) \
        .bind("0.0.0.0:19200") \
        .with_peers([(1, "127.0.0.1:19201"), (2, "127.0.0.1:19202")]) \
        .with_program(program) \
        .with_preprocessing(3, 8) \
        .with_instance_id(12345) \
        .build()

    await server.start()
    await server.run_forever()
"""

import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Dict, Tuple, Any
import logging
import time

from .protocol import (
    serialize_message,
    deserialize_message,
    MessageBuffer,
    ServerInfo,
    ClientReady,
    ComputationComplete,
    ComputationTrigger,
    HoneyBadgerPayload,
    ErrorMessage,
    ErrorCode,
    MPCaaSMessage,
)
from ..native.network import QUICNetwork, QUICConnection
from ..native.errors import NetworkError

logger = logging.getLogger(__name__)


class ServerState(Enum):
    """Server states"""
    INITIALIZED = auto()
    STARTING = auto()
    CONNECTING_PEERS = auto()
    PREPROCESSING = auto()
    READY = auto()
    COMPUTING = auto()
    SHUTTING_DOWN = auto()


@dataclass
class ClientHandler:
    """Handler for a connected client"""
    client_id: int
    connection: QUICConnection
    buffer: MessageBuffer
    num_inputs: int = 0
    ready: bool = False


class StoffelServerBuilder:
    """
    Builder for StoffelServer

    Provides fluent API for configuring MPC servers.

    Example:
        server = StoffelServer.builder(party_id=0) \
            .bind("0.0.0.0:19200") \
            .with_peers([(1, "127.0.0.1:19201"), (2, "127.0.0.1:19202")]) \
            .with_program(program) \
            .with_preprocessing(3, 8) \
            .with_instance_id(12345) \
            .build()
    """

    def __init__(self, party_id: int):
        self._party_id = party_id
        self._bind_address: Optional[str] = None
        self._peers: List[Tuple[int, str]] = []
        self._signaling_server: Optional[str] = None
        self._stun_server: Optional[str] = None
        self._program: Optional[bytes] = None
        self._n_triples: int = 10
        self._n_random_shares: int = 20
        self._instance_id: Optional[int] = None
        self._preprocessing_start_time: Optional[int] = None

    def bind(self, address: str) -> "StoffelServerBuilder":
        """
        Set bind address for QUIC listener

        Args:
            address: Address to bind to (e.g., "0.0.0.0:19200")

        Returns:
            Self for chaining
        """
        self._bind_address = address
        return self

    def with_peers(self, peers: List[Tuple[int, str]]) -> "StoffelServerBuilder":
        """
        Set peer server addresses

        Args:
            peers: List of (party_id, address) tuples

        Returns:
            Self for chaining
        """
        self._peers = list(peers)
        return self

    def with_signaling_server(self, address: str) -> "StoffelServerBuilder":
        """
        Set signaling server for dynamic peer discovery

        Args:
            address: Signaling server address

        Returns:
            Self for chaining
        """
        self._signaling_server = address
        return self

    def with_stun_server(self, address: str) -> "StoffelServerBuilder":
        """
        Set STUN server for NAT traversal

        Args:
            address: STUN server address

        Returns:
            Self for chaining
        """
        self._stun_server = address
        return self

    def with_program(self, program: Any) -> "StoffelServerBuilder":
        """
        Set Stoffel program to execute

        Args:
            program: Program instance or bytecode

        Returns:
            Self for chaining
        """
        if hasattr(program, 'bytecode'):
            self._program = program.bytecode()
        elif isinstance(program, bytes):
            self._program = program
        else:
            raise ValueError("program must be a Program instance or bytes")
        return self

    def with_preprocessing(
        self,
        n_triples: int,
        n_random_shares: int
    ) -> "StoffelServerBuilder":
        """
        Set preprocessing parameters

        Args:
            n_triples: Number of Beaver triples to generate
            n_random_shares: Number of random shares to generate

        Returns:
            Self for chaining
        """
        self._n_triples = n_triples
        self._n_random_shares = n_random_shares
        return self

    def with_instance_id(self, id: int) -> "StoffelServerBuilder":
        """
        Set computation instance ID

        CRITICAL: All servers in the same MPC network must use
        the same instance_id.

        Args:
            id: Instance ID

        Returns:
            Self for chaining
        """
        self._instance_id = id
        return self

    def with_preprocessing_start_time(self, epoch_secs: int) -> "StoffelServerBuilder":
        """
        Set synchronized preprocessing start time

        CRITICAL: All servers should use the same start time
        to coordinate preprocessing.

        Args:
            epoch_secs: Unix epoch timestamp when preprocessing should start

        Returns:
            Self for chaining
        """
        self._preprocessing_start_time = epoch_secs
        return self

    def build(self) -> "StoffelServer":
        """
        Build the server

        Returns:
            Configured StoffelServer

        Raises:
            ValueError: If required configuration is missing
        """
        if self._bind_address is None:
            raise ValueError("bind address is required - use .bind()")

        if self._instance_id is None:
            raise ValueError("instance_id is required - use .with_instance_id()")

        return StoffelServer(
            party_id=self._party_id,
            bind_address=self._bind_address,
            peers=self._peers,
            signaling_server=self._signaling_server,
            stun_server=self._stun_server,
            program=self._program,
            n_triples=self._n_triples,
            n_random_shares=self._n_random_shares,
            instance_id=self._instance_id,
            preprocessing_start_time=self._preprocessing_start_time,
        )


class StoffelServer:
    """
    MPC compute server

    Handles peer connections, preprocessing, client connections,
    and MPC computation execution.

    Use StoffelServer.builder() to create instances.

    Example:
        server = StoffelServer.builder(party_id=0) \
            .bind("0.0.0.0:19200") \
            .with_peers([(1, "127.0.0.1:19201")]) \
            .with_instance_id(12345) \
            .build()

        await server.start()
        await server.run_forever()
    """

    def __init__(
        self,
        party_id: int,
        bind_address: str,
        peers: List[Tuple[int, str]],
        signaling_server: Optional[str],
        stun_server: Optional[str],
        program: Optional[bytes],
        n_triples: int,
        n_random_shares: int,
        instance_id: int,
        preprocessing_start_time: Optional[int],
    ):
        """
        Initialize server (internal - use builder())
        """
        self._party_id = party_id
        self._bind_address = bind_address
        self._peers = peers
        self._signaling_server = signaling_server
        self._stun_server = stun_server
        self._program = program
        self._n_triples = n_triples
        self._n_random_shares = n_random_shares
        self._instance_id = instance_id
        self._preprocessing_start_time = preprocessing_start_time

        self._n_parties = len(peers) + 1  # peers + self
        self._threshold = 1  # Default threshold

        self._network: Optional[QUICNetwork] = None
        self._peer_connections: Dict[int, QUICConnection] = {}
        self._peer_buffers: Dict[int, MessageBuffer] = {}
        self._clients: Dict[int, ClientHandler] = {}

        self._state = ServerState.INITIALIZED
        self._running = False
        self._preprocessing_done = False

    @staticmethod
    def builder(party_id: int) -> StoffelServerBuilder:
        """Create a new server builder"""
        return StoffelServerBuilder(party_id)

    @property
    def party_id(self) -> int:
        """This server's party ID"""
        return self._party_id

    @property
    def state(self) -> ServerState:
        """Current server state"""
        return self._state

    @property
    def n_parties(self) -> int:
        """Total number of MPC parties"""
        return self._n_parties

    @property
    def threshold(self) -> int:
        """Byzantine fault tolerance threshold"""
        return self._threshold

    @property
    def instance_id(self) -> int:
        """Computation instance ID"""
        return self._instance_id

    async def start(self) -> None:
        """
        Start the server

        Initializes network, connects to peers, and starts preprocessing.
        """
        self._state = ServerState.STARTING
        logger.info(f"Server {self._party_id} starting on {self._bind_address}")

        # Initialize network
        self._network = QUICNetwork()
        await self._network.init()

        # Start listening
        await self._network.listen(self._bind_address)
        logger.info(f"Server {self._party_id} listening on {self._bind_address}")

        # Connect to higher-ID peers (to avoid duplicate connections)
        self._state = ServerState.CONNECTING_PEERS
        await self._connect_to_peers()

        # Wait for preprocessing start time if set
        if self._preprocessing_start_time:
            self._state = ServerState.PREPROCESSING
            await self._wait_for_preprocessing_start()
            await self._run_preprocessing()
        else:
            self._preprocessing_done = True

        self._state = ServerState.READY
        logger.info(f"Server {self._party_id} ready")

    async def _connect_to_peers(self) -> None:
        """Connect to peer servers with higher IDs"""
        for peer_id, peer_addr in self._peers:
            if peer_id > self._party_id:
                # Connect to peers with higher ID
                try:
                    conn = await self._network.connect(peer_addr)
                    self._peer_connections[peer_id] = conn
                    self._peer_buffers[peer_id] = MessageBuffer()
                    logger.debug(f"Connected to peer {peer_id} at {peer_addr}")
                except Exception as e:
                    logger.error(f"Failed to connect to peer {peer_id}: {e}")

        # Accept connections from peers with lower IDs
        for peer_id, peer_addr in self._peers:
            if peer_id < self._party_id:
                try:
                    conn = await self._network.accept()
                    self._peer_connections[peer_id] = conn
                    self._peer_buffers[peer_id] = MessageBuffer()
                    logger.debug(f"Accepted connection from peer {peer_id}")
                except Exception as e:
                    logger.error(f"Failed to accept peer connection: {e}")

        logger.info(f"Connected to {len(self._peer_connections)} peers")

    async def _wait_for_preprocessing_start(self) -> None:
        """Wait until preprocessing start time"""
        if not self._preprocessing_start_time:
            return

        now = int(time.time())
        wait_time = self._preprocessing_start_time - now

        if wait_time > 0:
            logger.info(f"Waiting {wait_time}s until preprocessing start...")
            await asyncio.sleep(wait_time)

    async def _run_preprocessing(self) -> None:
        """Run HoneyBadger preprocessing (Beaver triple generation)"""
        logger.info(f"Running preprocessing: {self._n_triples} triples, {self._n_random_shares} random shares")

        # TODO: Implement actual preprocessing via FFI
        # For now, simulate preprocessing time
        await asyncio.sleep(5)

        self._preprocessing_done = True
        logger.info("Preprocessing complete")

    async def run_forever(self) -> None:
        """
        Run the server main loop

        Accepts client connections and handles MPC computations.
        """
        self._running = True
        logger.info(f"Server {self._party_id} running...")

        while self._running:
            try:
                # Accept new client connections
                await self._accept_clients()

                # Process client messages
                await self._process_client_messages()

                # Small delay to prevent busy loop
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Server error: {e}")
                await asyncio.sleep(1)

    async def _accept_clients(self) -> None:
        """Accept new client connections"""
        try:
            # Non-blocking accept with timeout
            conn = await asyncio.wait_for(
                self._network.accept(),
                timeout=0.1
            )

            # Generate temporary client ID
            client_id = len(self._clients) + 1
            handler = ClientHandler(
                client_id=client_id,
                connection=conn,
                buffer=MessageBuffer(),
            )
            self._clients[client_id] = handler

            # Send ServerInfo to client
            server_info = ServerInfo(
                n_parties=self._n_parties,
                threshold=self._threshold,
                instance_id=self._instance_id,
                party_id=self._party_id,
            )
            await conn.send(serialize_message(server_info))
            logger.info(f"Client {client_id} connected, sent ServerInfo")

        except asyncio.TimeoutError:
            pass  # No client waiting

    async def _process_client_messages(self) -> None:
        """Process messages from connected clients"""
        for client_id, handler in list(self._clients.items()):
            try:
                # Non-blocking receive
                data = await asyncio.wait_for(
                    handler.connection.receive(),
                    timeout=0.05
                )
                handler.buffer.append(data)

                msg = handler.buffer.try_parse()
                while msg is not None:
                    await self._handle_client_message(handler, msg)
                    msg = handler.buffer.try_parse()

            except asyncio.TimeoutError:
                pass  # No data available
            except Exception as e:
                logger.error(f"Error processing client {client_id} message: {e}")

    async def _handle_client_message(
        self,
        handler: ClientHandler,
        msg: MPCaaSMessage
    ) -> None:
        """Handle a message from a client"""
        if isinstance(msg, ClientReady):
            handler.client_id = msg.client_id
            handler.num_inputs = msg.num_inputs
            handler.ready = True
            logger.info(f"Client {msg.client_id} ready with {msg.num_inputs} inputs")

            # Check if we can start computation
            await self._maybe_start_computation()

        elif isinstance(msg, HoneyBadgerPayload):
            # Process HoneyBadger protocol message
            logger.debug(f"Received HoneyBadger payload from client {handler.client_id}")
            # TODO: Process via FFI

        else:
            logger.warning(f"Unexpected message from client: {type(msg).__name__}")

    async def _maybe_start_computation(self) -> None:
        """Check if we can start computation and trigger if ready"""
        if not self._preprocessing_done:
            return

        # Check if all expected clients are ready
        ready_clients = [h for h in self._clients.values() if h.ready]

        if ready_clients:
            self._state = ServerState.COMPUTING
            logger.info(f"Starting computation with {len(ready_clients)} clients")

            # TODO: Run actual MPC computation via FFI

            # Simulate computation
            await asyncio.sleep(2)

            # Send ComputationComplete to all clients
            complete = ComputationComplete(session_id=self._instance_id)
            for handler in ready_clients:
                try:
                    await handler.connection.send(serialize_message(complete))
                    logger.debug(f"Sent ComputationComplete to client {handler.client_id}")
                except Exception as e:
                    logger.error(f"Failed to send ComputationComplete to client {handler.client_id}: {e}")

            self._state = ServerState.READY
            logger.info("Computation complete")

    async def shutdown(self) -> None:
        """Gracefully shutdown the server"""
        self._running = False
        self._state = ServerState.SHUTTING_DOWN
        logger.info(f"Server {self._party_id} shutting down...")

        # Close client connections
        for handler in self._clients.values():
            handler.connection.close()
        self._clients.clear()

        # Close peer connections
        for conn in self._peer_connections.values():
            conn.close()
        self._peer_connections.clear()

        # Close network
        if self._network:
            self._network.close()
            self._network = None

        logger.info(f"Server {self._party_id} stopped")

    async def __aenter__(self) -> "StoffelServer":
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.shutdown()
