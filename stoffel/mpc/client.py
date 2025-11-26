"""
MPC Client and Builder

This module provides MPCClient for input providers in client-server MPC architectures.
Clients secret-share their inputs and receive reconstructed outputs, but don't participate
in the computation itself.
"""

from typing import Any, Dict, List, Optional
from enum import Enum


class MPCClientBuilder:
    """
    Builder for creating MPC clients

    This builder is returned by ``StoffelRuntime.client()`` and automatically
    receives the MPC configuration from the runtime.

    Example::

        runtime = Stoffel.compile("...").parties(5).threshold(1).build()
        client = runtime.client(100).with_inputs([10, 20]).build()
    """

    def __init__(
        self,
        client_id: int,
        n_parties: int,
        threshold: int,
        instance_id: int,
        protocol_type: "ProtocolType",
        share_type: "ShareType",
    ):
        self._client_id = client_id
        self._n_parties = n_parties
        self._threshold = threshold
        self._instance_id = instance_id
        self._protocol_type = protocol_type
        self._share_type = share_type
        self._inputs: List[int] = []

    def with_inputs(self, inputs: List[int]) -> "MPCClientBuilder":
        """
        Set the private inputs this client will contribute

        Args:
            inputs: List of integer inputs to secret-share

        Returns:
            Self for method chaining
        """
        self._inputs = inputs
        return self

    def build(self) -> "MPCClient":
        """
        Build the MPC client

        Returns:
            MPCClient instance
        """
        return MPCClient(
            client_id=self._client_id,
            n_parties=self._n_parties,
            threshold=self._threshold,
            instance_id=self._instance_id,
            protocol_type=self._protocol_type,
            share_type=self._share_type,
            inputs=self._inputs,
        )


class MPCClient:
    """
    MPC Client for input providers

    MPCClient handles the client side of client-server MPC architectures:

    - Secret shares inputs and sends to MPC network
    - Reconstructs outputs locally from shares received from servers
    - Does NOT participate in the actual computation

    The client uses the configured protocol and share type from the runtime.

    Example::

        runtime = Stoffel.compile("...").parties(5).threshold(1).build()
        client = runtime.client(100).with_inputs([10, 20]).build()

        # Generate shares for distribution to servers
        shares = client.generate_input_shares_robust()

        # Receive output shares and reconstruct
        result = await client.receive_outputs()
    """

    def __init__(
        self,
        client_id: int,
        n_parties: int,
        threshold: int,
        instance_id: int,
        protocol_type: "ProtocolType",
        share_type: "ShareType",
        inputs: List[int],
    ):
        self._client_id = client_id
        self._n_parties = n_parties
        self._threshold = threshold
        self._instance_id = instance_id
        self._protocol_type = protocol_type
        self._share_type = share_type
        self._inputs = inputs
        self._servers: Dict[int, str] = {}  # server_id -> address

    @property
    def client_id(self) -> int:
        """Get this client's ID"""
        return self._client_id

    @property
    def inputs(self) -> List[int]:
        """Get the inputs"""
        return self._inputs

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

    def add_server(self, server_id: int, address: str) -> None:
        """
        Add a server to connect to

        Args:
            server_id: Server's party ID
            address: Server's network address (e.g., "127.0.0.1:19200")
        """
        self._servers[server_id] = address

    async def connect_to_servers(self) -> None:
        """
        Connect to all registered servers

        Raises:
            ConnectionError: If connection fails
        """
        # TODO: Implement when networking is available
        raise NotImplementedError(
            "Server connection requires networking bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def send_inputs(self) -> None:
        """
        Send secret-shared inputs to the MPC network

        This uses the interactive masking protocol to distribute
        secret shares to all servers.

        Raises:
            RuntimeError: If not connected to servers
        """
        # TODO: Implement when networking is available
        raise NotImplementedError(
            "Input sending requires networking bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def generate_input_shares(self) -> List[bytes]:
        """
        Generate secret shares for all inputs

        Returns:
            List of serialized share bytes
        """
        # Use the configured share type
        from ..stoffel import ShareType
        if self._share_type == ShareType.ROBUST:
            return self.generate_input_shares_robust()
        else:
            return self.generate_input_shares_non_robust()

    def generate_input_shares_robust(self) -> List[bytes]:
        """
        Generate robust secret shares with error correction

        Uses Reed-Solomon erasure coding for Byzantine fault tolerance.

        Returns:
            List of RobustShare bytes for each input
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Robust share generation requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def generate_input_shares_non_robust(self) -> List[bytes]:
        """
        Generate standard Shamir secret shares

        Faster but requires all parties to be honest.

        Returns:
            List of NonRobustShare bytes for each input
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Non-robust share generation requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def receive_outputs(self) -> List[int]:
        """
        Receive and reconstruct outputs from the MPC network

        Returns:
            List of reconstructed output values
        """
        # TODO: Implement when networking is available
        raise NotImplementedError(
            "Output receiving requires networking bindings. "
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
