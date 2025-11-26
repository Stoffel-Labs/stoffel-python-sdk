"""
MPC Node and Builder

This module provides MPCNode for peer-to-peer MPC scenarios where all parties
both provide inputs AND participate in computation. This combines the functionality
of both MPCClient and MPCServer.
"""

from typing import Any, Dict, List, Optional
from enum import Enum


class MPCNodeBuilder:
    """
    Builder for creating MPC nodes

    This builder is returned by ``StoffelRuntime.node()`` and automatically
    receives the MPC configuration from the runtime.

    Nodes are for peer-to-peer scenarios where all parties both provide inputs
    AND participate in computation.

    Example::

        runtime = Stoffel.compile("...").parties(5).threshold(1).build()
        node = runtime.node(0).with_inputs([10, 20]).with_preprocessing(3, 8).build()
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
        self._inputs: List[int] = []
        self._n_triples: Optional[int] = None
        self._n_random_shares: Optional[int] = None

    def with_inputs(self, inputs: List[int]) -> "MPCNodeBuilder":
        """
        Set the private inputs this node will contribute

        Args:
            inputs: List of integer inputs to secret-share

        Returns:
            Self for method chaining
        """
        self._inputs = inputs
        return self

    def with_preprocessing(self, n_triples: int, n_random_shares: int) -> "MPCNodeBuilder":
        """
        Set preprocessing material requirements

        If not set, reasonable defaults will be calculated based on the MPC configuration.

        Args:
            n_triples: Number of beaver triples for multiplication
            n_random_shares: Number of random shares (typically inputs + 2*triples)

        Returns:
            Self for method chaining
        """
        self._n_triples = n_triples
        self._n_random_shares = n_random_shares
        return self

    def build(self) -> "MPCNode":
        """
        Build the MPC node

        Returns:
            MPCNode instance
        """
        # Use defaults if not set
        n_triples = self._n_triples if self._n_triples is not None else 2 * self._threshold + 1
        n_random_shares = self._n_random_shares if self._n_random_shares is not None else 2 + 2 * n_triples

        return MPCNode(
            party_id=self._party_id,
            n_parties=self._n_parties,
            threshold=self._threshold,
            instance_id=self._instance_id,
            protocol_type=self._protocol_type,
            inputs=self._inputs,
            n_triples=n_triples,
            n_random_shares=n_random_shares,
        )


class MPCNode:
    """
    MPC Node that acts as both client and server

    MPCNode combines the functionality of both MPCClient and MPCServer, allowing
    a single entity to both provide private inputs AND participate in the secure computation.
    This is useful in scenarios where all parties have data to contribute and want to
    jointly compute on their combined inputs.

    As an abstraction over the underlying MPC protocol, it handles:

    - Secret sharing own inputs: Shares this party's inputs with the network
    - Receiving peer inputs: Accepts secret shares from other parties
    - Preprocessing: Generates cryptographic material for computation
    - Secure computation: Collaboratively executes the program with other parties
    - Output reconstruction: Reconstructs the final result from output shares

    When to Use:
        Use MPCNode for collaborative scenarios where:

        - Multiple organizations each have private data to contribute
        - All parties want to participate in the computation
        - No single party should learn others' raw inputs

    Example::

        runtime = Stoffel.compile("...").parties(5).threshold(1).build()
        node = runtime.node(0).with_inputs([10, 20]).with_preprocessing(3, 8).build()

        # Configure networking
        node.network_mut().listen("127.0.0.1:19200")

        # Run complete MPC protocol
        result = await node.run(bytecode)
    """

    def __init__(
        self,
        party_id: int,
        n_parties: int,
        threshold: int,
        instance_id: int,
        protocol_type: "ProtocolType",
        inputs: List[int],
        n_triples: int,
        n_random_shares: int,
    ):
        self._party_id = party_id
        self._n_parties = n_parties
        self._threshold = threshold
        self._instance_id = instance_id
        self._protocol_type = protocol_type
        self._inputs = inputs
        self._n_triples = n_triples
        self._n_random_shares = n_random_shares
        self._network = None  # Will be initialized with network manager

    @property
    def party_id(self) -> int:
        """Get this node's party ID"""
        return self._party_id

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
        Get the full MPC configuration

        Returns:
            Dictionary with n_parties, threshold, instance_id, protocol_type
        """
        return {
            "n_parties": self._n_parties,
            "threshold": self._threshold,
            "instance_id": self._instance_id,
            "protocol_type": self._protocol_type.value,
        }

    def network(self) -> Any:
        """
        Get a reference to the network manager (read-only)

        Returns:
            Network manager instance
        """
        return self._network

    def network_mut(self) -> Any:
        """
        Get a mutable reference to the network manager for configuration

        This allows you to configure the underlying network before execution:
        - Call listen(address) to bind to a socket
        - Call add_node_with_party_id(id, address) to register peers
        - Call connect(address) to establish connections

        Returns:
            Mutable network manager instance
        """
        return self._network

    async def run(self, bytecode: bytes) -> List[int]:
        """
        Execute the full MPC protocol as both client and server

        This method runs the complete MPC workflow:
        1. Secret shares this party's inputs with other parties
        2. Receives secret shares from other parties
        3. Runs preprocessing to generate cryptographic material
        4. Executes the Stoffel program on the secret-shared data
        5. Reconstructs and returns the final output

        Args:
            bytecode: The compiled Stoffel program bytecode to execute

        Returns:
            The computation result as a list of integers

        Raises:
            RuntimeError: If any phase of the protocol fails

        Example:
            node = runtime.node(0).with_inputs([10, 20]).build()
            result = await node.run(bytecode)
            print(f"Result: {result}")
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Full MPC execution requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def mul(self, a: Any, b: Any) -> Any:
        """
        Perform secure multiplication on secret-shared values

        This is a lower-level primitive for secure computation. Most users should
        use the run() method instead which handles the complete protocol.

        Args:
            a: First secret-shared value (as field element)
            b: Second secret-shared value (as field element)

        Returns:
            A secret share of the product a * b

        Raises:
            RuntimeError: If preprocessing material is exhausted
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Secure multiplication requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    async def output(self, share: Any) -> int:
        """
        Reconstruct output from secret shares

        This method collects shares from all parties and reconstructs the final
        output value. This is typically called at the end of a computation.

        Args:
            share: This party's share of the output

        Returns:
            The reconstructed output value

        Raises:
            RuntimeError: If not enough shares received
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Output reconstruction requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )
