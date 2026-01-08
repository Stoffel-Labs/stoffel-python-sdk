"""
Stoffel MPC Server

Provides the server API for running Stoffel MPC compute nodes.
Matches the Rust SDK's StoffelServer API.

IMPLEMENTATION STATUS
=====================

This server uses HoneyBadgerMpcEngine FFI bindings for real MPC operations
when the native library is available. If the native library is not found,
it falls back to simulated MPC for testing.

**Resolved:** Linear issue STO-356
    "[StoffelVM] Add HoneyBadgerMpcEngine C FFI Exports for SDK Language Bindings"

**What Works (with native library):**
- QUIC networking (connection, send/receive)
- Protocol message serialization/deserialization
- Client connection handling
- Message routing between clients and servers
- HoneyBadger preprocessing (Beaver triple generation)
- MPC secure computation infrastructure
- Client output share retrieval
- VM-MPC integration (bytecode execution with MPC callbacks)
- Secure multiplication via engine.multiply()
- Output reconstruction via engine.open()

**Requirements:**
- Build stoffel-vm with: `cargo build --release` in external/stoffel-vm
- The native library (libstoffel_vm.dylib/.so) must be in library path

**Fallback Mode:**
When the native library is unavailable, MPC operations are simulated
with placeholder delays for testing purposes.

Example:
    # Create and start server
    server = Stoffel.server(party_id=0) \\
        .bind("0.0.0.0:19200") \\
        .with_peers([(1, "127.0.0.1:19201"), (2, "127.0.0.1:19202")]) \\
        .with_program(program) \\
        .with_preprocessing(3, 8) \\
        .with_instance_id(12345) \\
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
from ..native.hb_engine_ffi import (
    HoneyBadgerMpcEngine,
    HBEngineError,
    ShareTypeKind,
    is_hb_engine_available,
)

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

        # HoneyBadger MPC engine (created in start())
        self._engine: Optional[HoneyBadgerMpcEngine] = None

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

        # Initialize network with party_id for proper MPC connection mapping
        self._network = QUICNetwork(party_id=self._party_id)
        await self._network.init()

        # Start listening
        await self._network.listen(self._bind_address)
        logger.info(f"Server {self._party_id} listening on {self._bind_address}")

        # Connect to higher-ID peers (to avoid duplicate connections)
        self._state = ServerState.CONNECTING_PEERS
        await self._connect_to_peers()

        # Create HoneyBadger MPC engine if available
        # The network.get_hb_network() method extracts a StoffelVM-compatible
        # Arc<QuicNetworkManager> pointer from the mpc-protocols NetworkOpaque.
        if is_hb_engine_available():
            try:
                # Convert QUIC network to HoneyBadger-compatible network handle
                if self._network:
                    network_handle = self._network.get_hb_network()
                else:
                    network_handle = None

                if network_handle is None:
                    raise RuntimeError("Network handle required for HoneyBadger engine")

                self._engine = HoneyBadgerMpcEngine(
                    instance_id=self._instance_id,
                    party_id=self._party_id,
                    n_parties=self._n_parties,
                    threshold=self._threshold,
                    n_triples=self._n_triples,
                    n_random=self._n_random_shares,
                    network_ptr=network_handle,
                )
                logger.info(f"HoneyBadger engine created for party {self._party_id}")
            except HBEngineError as e:
                logger.warning(f"Failed to create HoneyBadger engine: {e}")
                logger.warning("Falling back to simulated MPC")
            except RuntimeError as e:
                logger.warning(f"Failed to create HoneyBadger engine: {e}")
                logger.warning("Falling back to simulated MPC")
        else:
            logger.info("Using simulated MPC (HoneyBadger engine not available)")

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
        """Run HoneyBadger preprocessing (Beaver triple generation)

        Uses HoneyBadgerMpcEngine FFI when available, falls back to simulation.
        """
        logger.info(f"Running preprocessing: {self._n_triples} triples, {self._n_random_shares} random shares")

        if self._engine is not None:
            # Use real HoneyBadger engine for preprocessing
            try:
                logger.info("Starting HoneyBadger preprocessing via FFI...")
                self._engine.start_preprocessing()
                self._preprocessing_done = True
                logger.info("HoneyBadger preprocessing complete")
            except HBEngineError as e:
                logger.error(f"Preprocessing failed: {e}")
                raise RuntimeError(f"Preprocessing failed: {e}")
        else:
            # Fallback: Simulated preprocessing (for testing without native library)
            logger.warning("STUB: Preprocessing is simulated, no real cryptographic material generated")
            await asyncio.sleep(2)  # Shorter delay for testing
            self._preprocessing_done = True
            logger.info("Simulated preprocessing complete")

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
            # Note: HoneyBadger protocol messages are typically server-to-server
            # Client-sent payloads are forwarded input shares
            if self._engine is not None and msg.data:
                # Store as client input shares for later initialization
                if not hasattr(handler, 'input_shares'):
                    handler.input_shares = b''
                handler.input_shares = msg.data
                logger.debug(f"Stored input shares from client {handler.client_id}")

        else:
            logger.warning(f"Unexpected message from client: {type(msg).__name__}")

    async def _maybe_start_computation(self) -> None:
        """Check if we can start computation and trigger if ready

        Uses HoneyBadgerMpcEngine FFI when available for real MPC operations.
        """
        if not self._preprocessing_done:
            return

        # Check if all expected clients are ready
        ready_clients = [h for h in self._clients.values() if h.ready]

        if not ready_clients:
            return

        self._state = ServerState.COMPUTING
        logger.info(f"Starting computation with {len(ready_clients)} clients")

        try:
            if self._engine is not None:
                # Real MPC computation using HoneyBadger engine
                await self._run_mpc_computation(ready_clients)
            else:
                # Fallback: Simulated computation
                logger.warning("STUB: Computation is simulated, no real secure multiparty computation")
                await asyncio.sleep(1)

            # Send ComputationComplete to all clients
            for handler in ready_clients:
                try:
                    # Get output shares for this client if engine available
                    output_shares = None
                    if self._engine is not None:
                        try:
                            output_shares = self._engine.get_client_shares(handler.client_id)
                        except HBEngineError as e:
                            logger.warning(f"Could not get shares for client {handler.client_id}: {e}")

                    complete = ComputationComplete(
                        session_id=self._instance_id,
                        output_shares=output_shares,
                    )
                    await handler.connection.send(serialize_message(complete))
                    logger.debug(f"Sent ComputationComplete to client {handler.client_id}")
                except Exception as e:
                    logger.error(f"Failed to send ComputationComplete to client {handler.client_id}: {e}")

            self._state = ServerState.READY
            logger.info("Computation complete")

        except HBEngineError as e:
            logger.error(f"MPC computation failed: {e}")
            # Send error to clients
            for handler in ready_clients:
                try:
                    error = ErrorMessage(code=ErrorCode.INTERNAL_ERROR, message=str(e))
                    await handler.connection.send(serialize_message(error))
                except Exception:
                    pass
            self._state = ServerState.READY

    async def _run_mpc_computation(self, ready_clients: List[ClientHandler]) -> None:
        """Execute the actual MPC computation using HoneyBadger engine

        This method:
        1. Creates a VM with MPC foreign function callbacks
        2. Loads the program bytecode
        3. Initializes client inputs in the engine
        4. Executes the program with MPC semantics (multiply/output via engine)
        5. Sends output shares to clients
        """
        if self._engine is None:
            raise RuntimeError("Engine not initialized")

        logger.info("Running HoneyBadger MPC computation...")

        # Import here to avoid circular imports
        from .mpc_vm import VMWithMPC, is_mpc_vm_available

        # Check if MPC VM execution is available
        if not is_mpc_vm_available():
            logger.warning(
                "MPC VM execution not available (missing native libraries). "
                "Falling back to simulated computation."
            )
            # Fallback: just verify engine is ready
            if self._engine.is_ready():
                logger.info("HoneyBadger engine ready (simulation mode)")
            return

        # Get bytecode from program
        bytecode = self._get_program_bytecode()
        if bytecode is None:
            logger.warning("No program bytecode available, skipping computation")
            return

        # Create MPC-aware VM
        mpc_vm = VMWithMPC(self._engine)

        try:
            # Setup VM with bytecode and register MPC foreign functions
            mpc_vm.setup(bytecode)

            # Initialize client inputs
            for handler in ready_clients:
                if hasattr(handler, 'input_shares') and handler.input_shares:
                    # Parse input shares - assume they're concatenated bytes
                    # Each share is 8 bytes (64-bit)
                    share_size = 8
                    shares_data = handler.input_shares
                    shares = [
                        shares_data[i:i+share_size]
                        for i in range(0, len(shares_data), share_size)
                        if i + share_size <= len(shares_data)
                    ]
                    if shares:
                        mpc_vm.set_client_inputs(handler.client_id, shares)
                        logger.debug(
                            f"Initialized {len(shares)} inputs for client {handler.client_id}"
                        )

            # Execute with MPC semantics
            logger.info("Executing program with MPC operations...")
            result = mpc_vm.execute("main")
            logger.info(f"MPC computation result: {result}")

            # Send output shares to clients
            for handler in ready_clients:
                try:
                    output_shares = self._engine.get_client_shares(handler.client_id)
                    complete = ComputationComplete(
                        session_id=self._instance_id,
                        output_shares=output_shares,
                    )
                    await handler.connection.send(serialize_message(complete))
                    logger.debug(f"Sent output shares to client {handler.client_id}")
                except HBEngineError as e:
                    logger.warning(f"Failed to get shares for client {handler.client_id}: {e}")

        except Exception as e:
            logger.error(f"MPC computation failed: {e}")
            # Send error to clients
            for handler in ready_clients:
                error_msg = ErrorMessage(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Computation failed: {str(e)}",
                )
                await handler.connection.send(serialize_message(error_msg))
            raise

        logger.info("MPC computation phase complete")

    def _get_program_bytecode(self) -> Optional[bytes]:
        """Get bytecode from the program (handles both bytes and program objects)"""
        if self._program is None:
            return None
        if isinstance(self._program, bytes):
            return self._program
        if hasattr(self._program, 'bytecode'):
            bc = self._program.bytecode
            return bc() if callable(bc) else bc
        return None

    async def shutdown(self) -> None:
        """Gracefully shutdown the server"""
        self._running = False
        self._state = ServerState.SHUTTING_DOWN
        logger.info(f"Server {self._party_id} shutting down...")

        # Free HoneyBadger engine resources
        if self._engine is not None:
            logger.debug("Freeing HoneyBadger engine resources")
            del self._engine
            self._engine = None

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
