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

        # Add server addresses
        client.add_server(0, "127.0.0.1:19200")
        client.add_server(1, "127.0.0.1:19201")

        # Connect and send inputs
        await client.connect_to_servers()
        await client.send_inputs()

        # Receive outputs
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
        self._network_manager = None
        self._connected = False
        self._share_manager = None

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

    @property
    def connected(self) -> bool:
        """Check if connected to servers"""
        return self._connected

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

    def _get_share_manager(self):
        """Get or create the native share manager"""
        if self._share_manager is None:
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

    def _get_network_manager(self):
        """Get or create the network manager"""
        if self._network_manager is None:
            from ..networking import MPCNetworkManager

            self._network_manager = MPCNetworkManager(
                party_id=self._client_id,
                n_parties=self._n_parties,
                threshold=self._threshold,
                instance_id=self._instance_id,
                is_client=True,
            )
        return self._network_manager

    async def connect_to_servers(self) -> None:
        """
        Connect to all registered servers

        Establishes TCP connections to each server and performs
        the handshake protocol.

        Raises:
            ConnectionError: If connection fails
            ValueError: If no servers registered
        """
        if not self._servers:
            raise ValueError("No servers registered. Use add_server() first.")

        manager = self._get_network_manager()

        # Connect to all servers
        await manager.connect_to_peers(self._servers)

        self._connected = True

    async def send_inputs(self) -> None:
        """
        Send secret-shared inputs to the MPC network

        This creates secret shares of each input and distributes
        them to the appropriate servers.

        Raises:
            RuntimeError: If not connected to servers
            ValueError: If no inputs set
        """
        if not self._connected:
            raise RuntimeError("Not connected to servers. Call connect_to_servers() first.")

        if not self._inputs:
            raise ValueError("No inputs set. Use with_inputs() when building client.")

        # Get share manager
        share_manager = self._get_share_manager()
        network_manager = self._get_network_manager()

        # Import message type
        from ..networking.messages import ShareMessage
        from ..stoffel import ShareType

        # Create shares for each input
        shares_by_party: Dict[int, List[ShareMessage]] = {
            party_id: [] for party_id in self._servers.keys()
        }

        is_robust = self._share_type == ShareType.ROBUST

        for input_index, value in enumerate(self._inputs):
            # Create shares using native bindings
            shares = share_manager.create_shares(value)

            # Distribute to parties
            for share in shares:
                party_id = share.party_id
                if party_id in shares_by_party:
                    msg = ShareMessage(
                        input_index=input_index,
                        share_bytes=share.share_bytes,
                        party_id=party_id,
                        threshold=self._threshold,
                        is_robust=is_robust,
                    )
                    shares_by_party[party_id].append(msg)

        # Send all shares
        await network_manager.send_input_shares(shares_by_party)

    def generate_input_shares(self) -> Dict[int, List[bytes]]:
        """
        Generate secret shares for all inputs (without sending)

        Returns:
            Dict mapping party_id -> list of share bytes
        """
        share_manager = self._get_share_manager()

        shares_by_party: Dict[int, List[bytes]] = {
            party_id: [] for party_id in range(self._n_parties)
        }

        for value in self._inputs:
            shares = share_manager.create_shares(value)
            for share in shares:
                shares_by_party[share.party_id].append(share.share_bytes)

        return shares_by_party

    def generate_input_shares_robust(self) -> List[bytes]:
        """
        Generate robust secret shares with error correction

        Uses Reed-Solomon erasure coding for Byzantine fault tolerance.

        Returns:
            List of RobustShare bytes for each input
        """
        share_manager = self._get_share_manager()

        all_shares = []
        for value in self._inputs:
            shares = share_manager.create_shares(value)
            for share in shares:
                all_shares.append(share.share_bytes)

        return all_shares

    def generate_input_shares_non_robust(self) -> List[bytes]:
        """
        Generate standard Shamir secret shares

        Faster but requires all parties to be honest.

        Returns:
            List of NonRobustShare bytes for each input
        """
        # For non-robust, we need a different share manager
        try:
            from ..native.mpc import NativeShareManager

            manager = NativeShareManager(
                n_parties=self._n_parties,
                threshold=self._threshold,
                robust=False,
            )

            all_shares = []
            for value in self._inputs:
                shares = manager.create_shares(value)
                for share in shares:
                    all_shares.append(share.share_bytes)

            return all_shares
        except ImportError:
            raise RuntimeError(
                "Native MPC bindings not available. "
                "Build the MPC library with 'cargo build --release' in external/mpc-protocols"
            )

    async def receive_outputs(self, output_count: int = 1, timeout: float = 60.0) -> List[int]:
        """
        Receive and reconstruct outputs from the MPC network

        Args:
            output_count: Number of outputs to expect (default: 1)
            timeout: Timeout in seconds

        Returns:
            List of reconstructed output values
        """
        if not self._connected:
            raise RuntimeError("Not connected to servers")

        network_manager = self._get_network_manager()
        share_manager = self._get_share_manager()

        # Wait for output shares
        output_shares = await network_manager.wait_for_outputs(output_count, timeout)

        # Reconstruct each output
        from ..native.mpc import Share, ShareType as NativeShareType
        from ..stoffel import ShareType

        results = []
        is_robust = self._share_type == ShareType.ROBUST

        for i, shares_bytes in enumerate(output_shares):
            # Convert to Share objects
            shares = []
            for j, share_bytes in enumerate(shares_bytes):
                share = Share(
                    share_bytes=share_bytes,
                    party_id=j,
                    threshold=self._threshold,
                    share_type=NativeShareType.ROBUST if is_robust else NativeShareType.NON_ROBUST,
                )
                shares.append(share)

            # Reconstruct
            value = share_manager.reconstruct(shares)
            results.append(value)

        return results

    async def disconnect(self) -> None:
        """Disconnect from all servers"""
        if self._network_manager is not None:
            await self._network_manager.close()
        self._connected = False

    async def __aenter__(self) -> "MPCClient":
        """Async context manager entry"""
        await self.connect_to_servers()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.disconnect()
