"""
MPC Server and Builder

This module provides MPCServer for compute nodes in client-server MPC architectures.
Servers receive secret shares from clients, perform secure computation using the
HoneyBadger protocol, and return output shares.
"""

from typing import Any, Dict, List, Optional
from enum import Enum


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
    ):
        self._party_id = party_id
        self._n_parties = n_parties
        self._threshold = threshold
        self._instance_id = instance_id
        self._protocol_type = protocol_type
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

        # Start listening for connections
        await server.bind_and_listen("127.0.0.1:19200")

        # Run preprocessing phase
        await server.run_preprocessing()

        # Receive and process client inputs
        await server.receive_client_inputs(client_id=100, num_inputs=2)

        # Execute computation
        result = await server.compute(bytecode, "main")

        # Send outputs to client
        await server.send_outputs(client_id=100, session_id=42)
    """

    def __init__(
        self,
        party_id: int,
        n_parties: int,
        threshold: int,
        instance_id: int,
        protocol_type: "ProtocolType",
        n_triples: int,
        n_random_shares: int,
    ):
        self._party_id = party_id
        self._n_parties = n_parties
        self._threshold = threshold
        self._instance_id = instance_id
        self._protocol_type = protocol_type
        self._n_triples = n_triples
        self._n_random_shares = n_random_shares
        self._peers: Dict[int, str] = {}  # peer_id -> address
        self._bytecode: Optional[bytes] = None
        self._initialized = False

    @property
    def party_id(self) -> int:
        """Get this server's party ID"""
        return self._party_id

    @property
    def instance_id(self) -> int:
        """Get the instance ID"""
        return self._instance_id

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

    def initialize_node(self) -> None:
        """
        Initialize the MPC node before starting message processing

        This must be called before spawning the message processor.
        """
        # TODO: Implement when MPC protocol bindings are available
        self._initialized = True

    def add_peer(self, peer_id: int, address: str) -> None:
        """
        Add a peer server to connect to

        Args:
            peer_id: Peer's party ID
            address: Peer's network address (e.g., "127.0.0.1:19201")
        """
        self._peers[peer_id] = address

    async def bind_and_listen(self, address: str) -> None:
        """
        Bind to address and start listening for connections

        Args:
            address: Address to bind to (e.g., "127.0.0.1:19200")

        Returns:
            Message receiver for incoming messages
        """
        # TODO: Implement when networking is available
        raise NotImplementedError(
            "Server binding requires networking bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def connect_to_peers(self) -> None:
        """
        Connect to all registered peer servers

        Raises:
            ConnectionError: If connection fails
        """
        # TODO: Implement when networking is available
        raise NotImplementedError(
            "Peer connection requires networking bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def run_preprocessing(self) -> None:
        """
        Run the preprocessing phase to generate cryptographic material

        This generates beaver triples and random shares needed for
        secure multiplication operations.

        Raises:
            RuntimeError: If not connected to peers
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Preprocessing requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def receive_client_inputs(self, client_id: int, num_inputs: int) -> None:
        """
        Receive secret-shared inputs from a client

        Args:
            client_id: ID of the client sending inputs
            num_inputs: Number of inputs to receive

        Raises:
            RuntimeError: If not initialized
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Client input reception requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def compute(self, bytecode: bytes, function_name: str = "main") -> Any:
        """
        Execute secure computation on the secret-shared data

        Args:
            bytecode: Compiled Stoffel program bytecode
            function_name: Name of the function to execute

        Returns:
            Computation result (still secret-shared)

        Raises:
            RuntimeError: If preprocessing not complete
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Secure computation requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def send_outputs(self, client_id: int, session_id: int) -> None:
        """
        Send output shares to a client

        Args:
            client_id: ID of the client to send outputs to
            session_id: Session ID for this computation
        """
        # TODO: Implement when networking is available
        raise NotImplementedError(
            "Output sending requires networking bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def process_message(self, message: bytes) -> None:
        """
        Process a message from the network

        Args:
            message: Raw message bytes
        """
        # TODO: Implement when networking is available
        raise NotImplementedError(
            "Message processing requires networking bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def load_bytecode(self, bytecode: bytes) -> None:
        """
        Load compiled bytecode for execution

        Args:
            bytecode: Compiled Stoffel program bytecode
        """
        self._bytecode = bytecode

    def execute_function(self, function_name: str = "main") -> Any:
        """
        Execute a function from the loaded bytecode locally

        This is for local testing without MPC.

        Args:
            function_name: Name of the function to execute

        Returns:
            Execution result

        Raises:
            RuntimeError: If no bytecode loaded
        """
        if self._bytecode is None:
            raise RuntimeError("No bytecode loaded. Call load_bytecode() first.")

        # TODO: Implement via VM bindings
        raise NotImplementedError(
            "Local execution requires VM bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def receive_input_shares(self, shares: List[bytes]) -> None:
        """
        Receive pre-generated input shares

        This is an alternative to receive_client_inputs() for cases
        where shares are generated offline.

        Args:
            shares: List of serialized share bytes
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Share reception requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )
