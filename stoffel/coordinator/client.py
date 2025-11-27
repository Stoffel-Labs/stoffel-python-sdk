"""
MPC Coordinator Client

Client interface for interacting with the MPC coordinator and nodes.

The coordinator orchestrates the computation phases, but clients send their
input shares DIRECTLY to the MPC nodes (not through the coordinator).

Flow:
1. Client connects to coordinator to get session info and node addresses
2. Coordinator signals nodes to start accepting inputs
3. Client sends input shares directly to each node
4. Coordinator signals nodes to compute
5. Nodes send output shares directly to client
6. Client reconstructs the output
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .mock_coordinator import MockMPCCoordinator, ComputationResult
    from ..stoffel import StoffelRuntime
    from ..mpc.server import MPCServer

logger = logging.getLogger(__name__)


class CoordinatorClient:
    """
    Client interface to MPC coordinator and nodes

    This class provides the client-side interface for MPC computation:
    1. Register with coordinator to join a session
    2. Get node addresses from coordinator
    3. Send input shares directly to nodes
    4. Receive output shares directly from nodes
    5. Reconstruct the final output

    Example::

        from stoffel import Stoffel
        from stoffel.coordinator import CoordinatorClient, MockMPCCoordinator

        # Create coordinator and session
        coordinator = MockMPCCoordinator()
        runtime = Stoffel.load(b"bytecode").parties(4).threshold(1).build()
        session_id = await coordinator.create_session(runtime, expected_clients=[100])

        # Create client
        client = CoordinatorClient(client_id=100)
        client.connect_to_coordinator(coordinator)

        # Get nodes from coordinator
        nodes = client.get_nodes(session_id)

        # Send inputs directly to nodes (secret shared)
        await client.send_inputs_to_nodes(session_id, inputs=[42, 17])

        # Coordinator orchestrates the computation phases...

        # Receive output shares from nodes
        output = await client.receive_outputs_from_nodes(session_id)
    """

    def __init__(self, client_id: int):
        """
        Initialize coordinator client

        Args:
            client_id: Unique identifier for this client
        """
        self._client_id = client_id
        self._coordinator: Optional["MockMPCCoordinator"] = None
        self._current_session: Optional[int] = None

    @property
    def client_id(self) -> int:
        """Get this client's ID"""
        return self._client_id

    @property
    def connected(self) -> bool:
        """Check if connected to a coordinator"""
        return self._coordinator is not None

    def connect_to_coordinator(self, coordinator: "MockMPCCoordinator") -> None:
        """
        Connect to a local mock coordinator

        Args:
            coordinator: MockMPCCoordinator instance
        """
        self._coordinator = coordinator
        logger.info(f"Client {self._client_id} connected to coordinator")

    def connect(self, url: str, api_key: Optional[str] = None) -> None:
        """
        Connect to a production coordinator service

        Args:
            url: Coordinator service URL
            api_key: Optional API key for authentication

        Note:
            This is a placeholder for future production implementation.
        """
        raise NotImplementedError(
            "Production coordinator connection not yet implemented. "
            "Use connect_to_coordinator() with MockMPCCoordinator for testing."
        )

    def get_nodes(self, session_id: int) -> Dict[int, "MPCServer"]:
        """
        Get the MPC nodes for a session

        In production, this would return node addresses/connections.
        For mock testing, returns the actual MPCServer instances.

        Args:
            session_id: Session to get nodes for

        Returns:
            Dict mapping party_id to node
        """
        if self._coordinator is None:
            raise RuntimeError("Not connected to coordinator")

        return self._coordinator.get_nodes(session_id)

    async def send_inputs_to_nodes(
        self,
        session_id: int,
        inputs: List[int],
    ) -> None:
        """
        Send input shares directly to MPC nodes

        This secret-shares the inputs and sends each share to the
        corresponding node.

        Args:
            session_id: Session to send inputs for
            inputs: List of integer inputs to secret share
        """
        if self._coordinator is None:
            raise RuntimeError("Not connected to coordinator")

        nodes = self.get_nodes(session_id)

        logger.info(
            f"Client {self._client_id}: Sending {len(inputs)} inputs to "
            f"{len(nodes)} nodes"
        )

        # In a real implementation, we would:
        # 1. Secret share each input value
        # 2. Send share[i] to node[i]
        # For now, we just notify the coordinator that inputs were sent
        await self._coordinator.notify_inputs_received(session_id, self._client_id)

    async def receive_outputs_from_nodes(
        self,
        session_id: int,
        timeout: float = 60.0,
    ) -> List[int]:
        """
        Receive output shares from nodes and reconstruct

        Each node sends its output share. The client collects enough
        shares and reconstructs the final output.

        Args:
            session_id: Session to receive outputs from
            timeout: Timeout waiting for outputs

        Returns:
            List of reconstructed output values
        """
        if self._coordinator is None:
            raise RuntimeError("Not connected to coordinator")

        logger.info(f"Client {self._client_id}: Waiting for outputs from nodes")

        # In a real implementation, we would:
        # 1. Receive output shares from each node
        # 2. Reconstruct the output using Lagrange interpolation
        # For now, return empty (actual outputs handled by nodes)
        return []

    async def create_session(
        self,
        runtime: "StoffelRuntime",
        other_clients: Optional[List[int]] = None,
    ) -> int:
        """
        Create a new computation session via coordinator

        Args:
            runtime: Configured StoffelRuntime with program
            other_clients: List of other client IDs (not including self)

        Returns:
            Session ID
        """
        if self._coordinator is None:
            raise RuntimeError("Not connected to coordinator")

        expected_clients = [self._client_id]
        if other_clients:
            expected_clients.extend(other_clients)

        session_id = await self._coordinator.create_session(
            runtime,
            expected_clients=expected_clients,
        )

        self._current_session = session_id
        return session_id

    async def join_session(self, session_id: int) -> None:
        """
        Join an existing computation session

        Args:
            session_id: Session to join
        """
        self._current_session = session_id
        logger.info(f"Client {self._client_id}: Joined session {session_id}")

    async def close(self) -> None:
        """Disconnect from the current session"""
        self._current_session = None
