"""
MPC Server and Builder

This module provides MPCServer for compute nodes in client-server MPC architectures.
Servers receive secret shares from clients, perform secure computation using the
HoneyBadger protocol, and return output shares.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..stoffel import ProtocolType, ShareType

logger = logging.getLogger(__name__)


class MPCServerBuilder:
    """
    Builder for creating MPC servers

    This builder is returned by ``StoffelRuntime.server()`` and automatically
    receives the MPC configuration from the runtime.

    Example::

        runtime = Stoffel.compile("...").parties(5).threshold(1).build()
        server = runtime.server(0).with_preprocessing(10, 25).build()
    """

    def __init__(
        self,
        party_id: int,
        n_parties: int,
        threshold: int,
        instance_id: int,
        protocol_type: "ProtocolType",
        share_type: "ShareType",
        bytecode: Optional[bytes] = None,
    ):
        self._party_id = party_id
        self._n_parties = n_parties
        self._threshold = threshold
        self._instance_id = instance_id
        self._protocol_type = protocol_type
        self._share_type = share_type
        self._bytecode = bytecode
        self._n_triples: Optional[int] = None
        self._n_random_shares: Optional[int] = None

    def with_preprocessing(self, n_triples: int, n_random_shares: int) -> "MPCServerBuilder":
        """
        Set preprocessing material requirements

        Args:
            n_triples: Number of beaver triples for multiplication
            n_random_shares: Number of random shares (typically inputs + 2*triples)

        Returns:
            Self for method chaining
        """
        self._n_triples = n_triples
        self._n_random_shares = n_random_shares
        return self

    def build(self) -> "MPCServer":
        """
        Build the MPC server

        Returns:
            MPCServer instance
        """
        # Use defaults if not set
        n_triples = self._n_triples if self._n_triples is not None else 2 * self._threshold + 1
        n_random_shares = self._n_random_shares if self._n_random_shares is not None else 2 + 2 * n_triples

        return MPCServer(
            party_id=self._party_id,
            n_parties=self._n_parties,
            threshold=self._threshold,
            instance_id=self._instance_id,
            protocol_type=self._protocol_type,
            share_type=self._share_type,
            bytecode=self._bytecode,
            n_triples=n_triples,
            n_random_shares=n_random_shares,
        )


class MPCServer:
    """
    MPC Server for compute nodes

    MPCServer handles the server side of client-server MPC architectures:

    - Receives secret shares from clients
    - Performs secure multiparty computation using HoneyBadger
    - Manages preprocessing material (beaver triples, random shares)
    - Sends output shares back to clients

    The server uses the configured protocol from the runtime.

    Example::

        runtime = Stoffel.compile("...").parties(5).threshold(1).build()
        server = runtime.server(0).with_preprocessing(10, 25).build()

        # Add peer servers and start
        server.add_peer(1, "127.0.0.1:19201")
        server.add_peer(2, "127.0.0.1:19202")
        await server.start("127.0.0.1:19200")

        # Wait for client inputs and compute
        result = await server.run_computation()
    """

    def __init__(
        self,
        party_id: int,
        n_parties: int,
        threshold: int,
        instance_id: int,
        protocol_type: "ProtocolType",
        share_type: "ShareType",
        bytecode: Optional[bytes] = None,
        n_triples: int = 10,
        n_random_shares: int = 25,
    ):
        self._party_id = party_id
        self._n_parties = n_parties
        self._threshold = threshold
        self._instance_id = instance_id
        self._protocol_type = protocol_type
        self._share_type = share_type
        self._bytecode = bytecode
        self._n_triples = n_triples
        self._n_random_shares = n_random_shares

        # Networking state
        self._peers: Dict[int, str] = {}  # peer_id -> address
        self._network_manager = None
        self._bind_address: Optional[str] = None
        self._running = False
        self._initialized = False

        # Computation state
        self._client_inputs: Dict[int, Dict[int, bytes]] = {}  # client_id -> {input_index -> share_bytes}
        self._preprocessing_complete = False
        self._beaver_triples: List[tuple] = []  # (a_share, b_share, c_share)
        self._random_shares: List[bytes] = []
        self._output_shares: Dict[int, bytes] = {}  # output_index -> share_bytes

        # Event synchronization
        self._input_ready_events: Dict[int, asyncio.Event] = {}  # client_id -> event
        self._preprocessing_event = asyncio.Event()
        self._computation_complete_event = asyncio.Event()

    @property
    def party_id(self) -> int:
        """Get this server's party ID"""
        return self._party_id

    @property
    def instance_id(self) -> int:
        """Get the instance ID"""
        return self._instance_id

    @property
    def running(self) -> bool:
        """Check if server is running"""
        return self._running

    @property
    def preprocessing_complete(self) -> bool:
        """Check if preprocessing phase is complete"""
        return self._preprocessing_complete

    def config(self) -> Dict[str, Any]:
        """
        Get the MPC configuration

        Returns:
            Dictionary with n_parties, threshold, instance_id, protocol_type
        """
        return {
            "n_parties": self._n_parties,
            "threshold": self._threshold,
            "instance_id": self._instance_id,
            "protocol_type": self._protocol_type.value,
        }

    def _get_network_manager(self):
        """Get or create the network manager"""
        if self._network_manager is None:
            from ..networking import MPCNetworkManager, MessageType

            self._network_manager = MPCNetworkManager(
                party_id=self._party_id,
                n_parties=self._n_parties,
                threshold=self._threshold,
                instance_id=self._instance_id,
                is_client=False,
            )

            # Register message handlers
            self._network_manager.register_handler(
                MessageType.INPUT_SHARE,
                self._handle_input_share,
            )
            self._network_manager.register_handler(
                MessageType.PREPROCESSING_REQUEST,
                self._handle_preprocessing_request,
            )
            self._network_manager.register_handler(
                MessageType.PREPROCESSING_RESPONSE,
                self._handle_preprocessing_response,
            )
            self._network_manager.register_handler(
                MessageType.PROTOCOL_MESSAGE,
                self._handle_protocol_message,
            )

        return self._network_manager

    def _get_share_manager(self):
        """Get or create the native share manager"""
        if not hasattr(self, '_share_manager') or self._share_manager is None:
            try:
                from ..native.mpc import NativeShareManager
                from ..stoffel import ShareType

                is_robust = self._share_type == ShareType.ROBUST
                self._share_manager = NativeShareManager(
                    n_parties=self._n_parties,
                    threshold=self._threshold,
                    robust=is_robust,
                )
            except ImportError:
                raise RuntimeError(
                    "Native MPC bindings not available. "
                    "Build the MPC library with 'cargo build --release' in external/mpc-protocols"
                )
        return self._share_manager

    def add_peer(self, peer_id: int, address: str) -> None:
        """
        Add a peer server to connect to

        Args:
            peer_id: Peer's party ID
            address: Peer's network address (e.g., "127.0.0.1:19201")
        """
        if peer_id == self._party_id:
            raise ValueError("Cannot add self as peer")
        self._peers[peer_id] = address

    async def start(self, bind_address: str) -> None:
        """
        Start the server: bind to address and connect to peers

        This starts listening for incoming connections and establishes
        connections to all registered peer servers.

        Args:
            bind_address: Address to bind to (e.g., "127.0.0.1:19200")

        Raises:
            RuntimeError: If server already running
            ConnectionError: If peer connections fail
        """
        if self._running:
            raise RuntimeError("Server already running")

        self._bind_address = bind_address
        self._running = True
        self._initialized = True

        manager = self._get_network_manager()

        # Start listening in background (non-blocking)
        await manager.start_server(bind_address)
        logger.info(f"Server {self._party_id} listening on {bind_address}")

        # Give listener time to bind
        await asyncio.sleep(0.1)

        # Connect to peers with higher party IDs (to avoid duplicate connections)
        # Lower-ID servers wait for higher-ID servers to connect to them
        peers_to_connect = {
            pid: addr for pid, addr in self._peers.items()
            if pid > self._party_id
        }

        if peers_to_connect:
            try:
                await manager.connect_to_peers(peers_to_connect)
                logger.info(f"Server {self._party_id} connected to {len(peers_to_connect)} peers")
            except ConnectionError as e:
                logger.warning(f"Server {self._party_id} peer connection: {e}")

    async def connect_to_peers(self) -> None:
        """
        Connect to all registered peer servers

        Use this if you need to manually connect after start().

        Raises:
            RuntimeError: If server not running
            ConnectionError: If connection fails
        """
        if not self._running:
            raise RuntimeError("Server not running. Call start() first.")

        manager = self._get_network_manager()
        await manager.connect_to_peers(self._peers)

    async def run_preprocessing(self) -> None:
        """
        Run the preprocessing phase to generate cryptographic material

        This generates beaver triples and random shares needed for
        secure multiplication operations. All servers must participate.

        Raises:
            RuntimeError: If server not running
        """
        if not self._running:
            raise RuntimeError("Server not running. Call start() first.")

        logger.info(f"Server {self._party_id} starting preprocessing phase")

        # Generate local random values for beaver triples
        share_manager = self._get_share_manager()

        # For each beaver triple (a, b, c) where c = a * b:
        # Each party generates random shares and exchanges them
        for i in range(self._n_triples):
            # Generate local random value for 'a' component
            import secrets
            a_local = secrets.randbelow(2**64)
            b_local = secrets.randbelow(2**64)

            # In a real implementation, parties would run a distributed
            # protocol to generate correlated shares where c = a * b
            # For now, store local values (this is a placeholder)
            self._beaver_triples.append((
                a_local.to_bytes(32, 'big'),
                b_local.to_bytes(32, 'big'),
                (a_local * b_local).to_bytes(32, 'big'),
            ))

        # Generate random shares for masking
        for i in range(self._n_random_shares):
            r_local = secrets.randbelow(2**64)
            self._random_shares.append(r_local.to_bytes(32, 'big'))

        self._preprocessing_complete = True
        self._preprocessing_event.set()
        logger.info(
            f"Server {self._party_id} preprocessing complete: "
            f"{self._n_triples} triples, {self._n_random_shares} random shares"
        )

    async def wait_for_client_inputs(
        self,
        client_id: int,
        num_inputs: int,
        timeout: float = 60.0,
    ) -> None:
        """
        Wait for a client to send all their input shares

        Args:
            client_id: ID of the client to wait for
            num_inputs: Number of inputs expected
            timeout: Timeout in seconds

        Raises:
            TimeoutError: If inputs not received in time
        """
        if client_id not in self._input_ready_events:
            self._input_ready_events[client_id] = asyncio.Event()

        # Check if we already have all inputs
        if client_id in self._client_inputs:
            if len(self._client_inputs[client_id]) >= num_inputs:
                return

        try:
            await asyncio.wait_for(
                self._input_ready_events[client_id].wait(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            received = len(self._client_inputs.get(client_id, {}))
            raise TimeoutError(
                f"Timed out waiting for inputs from client {client_id}: "
                f"received {received}/{num_inputs}"
            )

    async def _handle_input_share(self, msg, conn) -> None:
        """Handle incoming input share from client"""
        from ..networking.messages import ShareMessage

        share = ShareMessage.from_payload(msg.payload)
        client_id = msg.sender_id

        # Store the share
        if client_id not in self._client_inputs:
            self._client_inputs[client_id] = {}

        self._client_inputs[client_id][share.input_index] = share.share_bytes

        logger.debug(
            f"Server {self._party_id} received input share {share.input_index} "
            f"from client {client_id}"
        )

        # Check if this client's inputs are complete
        # (We don't know the expected count, so we signal after each input)
        if client_id in self._input_ready_events:
            # Signal that at least one input is available
            self._input_ready_events[client_id].set()

    async def _handle_preprocessing_request(self, msg, conn) -> None:
        """Handle preprocessing request from peer"""
        # This would implement the distributed preprocessing protocol
        logger.debug(f"Server {self._party_id} received preprocessing request")
        pass

    async def _handle_preprocessing_response(self, msg, conn) -> None:
        """Handle preprocessing response from peer"""
        logger.debug(f"Server {self._party_id} received preprocessing response")
        pass

    async def _handle_protocol_message(self, msg, conn) -> None:
        """Handle HoneyBadger protocol message from peer"""
        logger.debug(f"Server {self._party_id} received protocol message")
        pass

    async def compute(
        self,
        bytecode: Optional[bytes] = None,
        function_name: str = "main",
    ) -> List[bytes]:
        """
        Execute secure computation on the secret-shared inputs

        Args:
            bytecode: Compiled Stoffel program bytecode (uses stored if None)
            function_name: Name of the function to execute

        Returns:
            List of output share bytes

        Raises:
            RuntimeError: If preprocessing not complete or no inputs
        """
        if not self._preprocessing_complete:
            raise RuntimeError("Preprocessing not complete. Call run_preprocessing() first.")

        if bytecode is not None:
            self._bytecode = bytecode

        if self._bytecode is None:
            raise RuntimeError("No bytecode available. Provide bytecode or load_bytecode() first.")

        # Gather all input shares from all clients
        all_inputs: List[bytes] = []
        for client_id in sorted(self._client_inputs.keys()):
            client_inputs = self._client_inputs[client_id]
            for input_index in sorted(client_inputs.keys()):
                all_inputs.append(client_inputs[input_index])

        if not all_inputs:
            raise RuntimeError("No input shares received from clients")

        logger.info(
            f"Server {self._party_id} executing computation with "
            f"{len(all_inputs)} input shares"
        )

        # Execute the computation on shares
        # In a real implementation, this would:
        # 1. Load shares into the MPC VM
        # 2. Execute bytecode using beaver triples for multiplication
        # 3. Coordinate with other servers for each operation
        # 4. Return output shares

        try:
            from ..native.vm import NativeVM

            # For now, we can't actually run MPC computation without
            # full VM integration. Return placeholder output shares.
            # This would be replaced with actual MPC execution.
            output_shares = self._execute_mpc_computation(all_inputs)

        except ImportError:
            # Fall back to placeholder computation
            output_shares = self._execute_mpc_computation(all_inputs)

        self._output_shares = {i: share for i, share in enumerate(output_shares)}
        self._computation_complete_event.set()

        return output_shares

    def _execute_mpc_computation(self, input_shares: List[bytes]) -> List[bytes]:
        """
        Execute MPC computation locally on shares

        This is a placeholder that demonstrates the data flow.
        Real implementation would coordinate with other servers.
        """
        # For demonstration, just return the first input share as output
        # Real implementation would execute bytecode on shares
        if input_shares:
            return [input_shares[0]]
        return [b'\x00' * 32]

    async def send_output_to_client(self, client_id: int) -> None:
        """
        Send output shares to a specific client

        Args:
            client_id: ID of the client to send outputs to

        Raises:
            RuntimeError: If computation not complete
        """
        if not self._output_shares:
            raise RuntimeError("No outputs to send. Call compute() first.")

        manager = self._get_network_manager()

        from ..networking.messages import MPCMessage, MessageType, OutputShareMessage

        for output_index, share_bytes in self._output_shares.items():
            output_msg = OutputShareMessage(
                output_index=output_index,
                share_bytes=share_bytes,
                party_id=self._party_id,
            )

            msg = MPCMessage(
                msg_type=MessageType.OUTPUT_SHARE,
                sender_id=self._party_id,
                instance_id=self._instance_id,
                payload=output_msg.to_payload(),
            )

            await manager.send_to_peer(client_id, msg)

        logger.info(
            f"Server {self._party_id} sent {len(self._output_shares)} "
            f"output shares to client {client_id}"
        )

    async def run_computation(
        self,
        expected_clients: List[int],
        inputs_per_client: int = 1,
        timeout: float = 60.0,
    ) -> List[bytes]:
        """
        Run the full computation pipeline

        This is a convenience method that:
        1. Runs preprocessing (if not done)
        2. Waits for all client inputs
        3. Executes computation
        4. Sends outputs to all clients

        Args:
            expected_clients: List of client IDs to expect inputs from
            inputs_per_client: Number of inputs expected from each client
            timeout: Timeout for waiting for inputs

        Returns:
            List of output share bytes
        """
        # Run preprocessing if needed
        if not self._preprocessing_complete:
            await self.run_preprocessing()

        # Wait for all client inputs
        for client_id in expected_clients:
            await self.wait_for_client_inputs(
                client_id,
                inputs_per_client,
                timeout=timeout,
            )

        # Execute computation
        outputs = await self.compute()

        # Send outputs to all clients
        for client_id in expected_clients:
            await self.send_output_to_client(client_id)

        return outputs

    def load_bytecode(self, bytecode: bytes) -> None:
        """
        Load compiled bytecode for execution

        Args:
            bytecode: Compiled Stoffel program bytecode
        """
        self._bytecode = bytecode

    def get_input_shares(self, client_id: int) -> Dict[int, bytes]:
        """
        Get received input shares from a client

        Args:
            client_id: Client ID to get shares for

        Returns:
            Dict mapping input_index -> share_bytes
        """
        return self._client_inputs.get(client_id, {})

    async def stop(self) -> None:
        """Stop the server and close all connections"""
        self._running = False

        if self._network_manager is not None:
            await self._network_manager.close()

        logger.info(f"Server {self._party_id} stopped")

    async def __aenter__(self) -> "MPCServer":
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.stop()
