"""
Mock MPC Coordinator

A local mock MPC coordinator for testing and demonstrations.
The coordinator's role is to ORCHESTRATE the MPC network - it tells nodes
what to do and when, but does not perform the computation itself.

Coordinator responsibilities:
1. Signal nodes to run preprocessing phase
2. Signal nodes to collect client input shares
3. Signal nodes to execute the computation
4. Signal nodes to send output shares back to clients

In production, this would be an external service. The mock version
creates and manages local MPC servers for testing.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..stoffel import StoffelRuntime
    from ..mpc.server import MPCServer

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """States of an MPC computation session"""
    CREATED = auto()           # Session created, waiting for nodes to join
    NODES_READY = auto()       # All nodes connected and ready
    PREPROCESSING = auto()     # Nodes running preprocessing phase
    AWAITING_INPUTS = auto()   # Nodes waiting for client input shares
    INPUTS_RECEIVED = auto()   # All client inputs received by nodes
    COMPUTING = auto()         # Nodes executing secure computation
    OUTPUTTING = auto()        # Nodes sending output shares to clients
    COMPLETED = auto()         # Computation finished successfully
    FAILED = auto()            # Computation failed


class CoordinatorCommand(Enum):
    """Commands sent from coordinator to nodes"""
    PREPARE = auto()           # Prepare for computation
    RUN_PREPROCESSING = auto() # Execute preprocessing phase
    AWAIT_INPUTS = auto()      # Start accepting client input shares
    COMPUTE = auto()           # Execute the MPC computation
    SEND_OUTPUTS = auto()      # Send output shares to clients
    SHUTDOWN = auto()          # Shutdown the node


@dataclass
class ComputationResult:
    """Result of an MPC computation"""
    session_id: int
    outputs: List[int]         # Reconstructed output values
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MPCSession:
    """
    Represents an MPC computation session

    Tracks the state and participants for a single MPC computation.
    """
    session_id: int
    runtime: "StoffelRuntime"
    n_parties: int
    threshold: int
    state: SessionState = SessionState.CREATED

    # Node management
    nodes: Dict[int, "MPCServer"] = field(default_factory=dict)
    node_ready: Dict[int, bool] = field(default_factory=dict)

    # Client tracking
    expected_clients: List[int] = field(default_factory=list)
    client_inputs_received: Dict[int, bool] = field(default_factory=dict)

    # Results (reconstructed outputs)
    results: Optional[ComputationResult] = None

    # Synchronization events
    _nodes_ready_event: asyncio.Event = field(default_factory=asyncio.Event)
    _preprocessing_done_event: asyncio.Event = field(default_factory=asyncio.Event)
    _inputs_received_event: asyncio.Event = field(default_factory=asyncio.Event)
    _computation_done_event: asyncio.Event = field(default_factory=asyncio.Event)

    def all_nodes_ready(self) -> bool:
        """Check if all nodes are ready"""
        return (
            len(self.node_ready) == self.n_parties and
            all(self.node_ready.values())
        )

    def all_inputs_received(self) -> bool:
        """Check if all expected client inputs have been received"""
        return (
            len(self.client_inputs_received) == len(self.expected_clients) and
            all(self.client_inputs_received.values())
        )


class MockMPCCoordinator:
    """
    Mock MPC Coordinator for local testing

    The coordinator orchestrates the MPC network by sending commands to nodes
    at the appropriate times. It does NOT perform computation - the nodes do.

    Coordination flow:
    1. Create session with runtime configuration
    2. Nodes register with the coordinator
    3. Coordinator signals: RUN_PREPROCESSING
    4. Coordinator signals: AWAIT_INPUTS
    5. Clients send input shares to nodes (not through coordinator)
    6. Coordinator signals: COMPUTE
    7. Coordinator signals: SEND_OUTPUTS
    8. Clients receive output shares from nodes

    For local testing, this mock coordinator also manages the lifecycle
    of local MPC server instances.

    Example::

        from stoffel import Stoffel
        from stoffel.coordinator import MockMPCCoordinator

        # Create coordinator
        coordinator = MockMPCCoordinator()

        # Compile program and configure MPC
        runtime = (Stoffel.compile("def add(a, b):\\n  return a + b")
            .parties(4)
            .threshold(1)
            .build())

        # Create session - coordinator will spawn local nodes
        session_id = await coordinator.create_session(
            runtime,
            expected_clients=[100, 101],
        )

        # Coordinator orchestrates the phases
        await coordinator.signal_preprocessing(session_id)
        await coordinator.signal_await_inputs(session_id)

        # Clients send inputs directly to nodes (not shown here)
        # ...

        await coordinator.signal_compute(session_id)
        await coordinator.signal_send_outputs(session_id)
    """

    def __init__(self, auto_start_nodes: bool = True):
        """
        Initialize the mock coordinator

        Args:
            auto_start_nodes: Automatically create and start local MPC nodes
        """
        self._sessions: Dict[int, MPCSession] = {}
        self._next_session_id = 1
        self._auto_start_nodes = auto_start_nodes
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        runtime: "StoffelRuntime",
        expected_clients: List[int],
    ) -> int:
        """
        Create a new MPC computation session

        Args:
            runtime: Configured StoffelRuntime with program and MPC config
            expected_clients: List of client IDs that will provide inputs

        Returns:
            Session ID for tracking this computation
        """
        async with self._lock:
            session_id = self._next_session_id
            self._next_session_id += 1

        config = runtime.mpc_config()
        if config is None:
            raise ValueError("Runtime must have MPC configuration")

        n_parties, threshold, instance_id = config

        session = MPCSession(
            session_id=session_id,
            runtime=runtime,
            n_parties=n_parties,
            threshold=threshold,
            expected_clients=list(expected_clients),
            state=SessionState.CREATED,
        )

        self._sessions[session_id] = session

        logger.info(
            f"Session {session_id} created: n={n_parties}, t={threshold}, "
            f"expected_clients={expected_clients}"
        )

        # Auto-start local nodes for testing
        if self._auto_start_nodes:
            await self._start_local_nodes(session)

        return session_id

    async def _start_local_nodes(self, session: MPCSession) -> None:
        """
        Start local MPC server nodes for testing

        In production, nodes would be external services that register
        with the coordinator.
        """
        logger.info(f"Session {session.session_id}: Starting {session.n_parties} local nodes")

        for party_id in range(session.n_parties):
            # Create server from runtime
            server = session.runtime.server(party_id).build()
            session.nodes[party_id] = server
            session.node_ready[party_id] = True

            logger.debug(f"Session {session.session_id}: Node {party_id} created")

        if session.all_nodes_ready():
            session.state = SessionState.NODES_READY
            session._nodes_ready_event.set()
            logger.info(f"Session {session.session_id}: All {session.n_parties} nodes ready")

    async def register_node(
        self,
        session_id: int,
        party_id: int,
        node: "MPCServer",
    ) -> None:
        """
        Register an external MPC node with the coordinator

        For production use where nodes are external services.

        Args:
            session_id: Session to register with
            party_id: Node's party ID
            node: The MPCServer instance
        """
        session = self._get_session(session_id)

        if party_id in session.nodes:
            raise ValueError(f"Node {party_id} already registered")

        if party_id < 0 or party_id >= session.n_parties:
            raise ValueError(f"Invalid party_id {party_id}, must be 0..{session.n_parties-1}")

        session.nodes[party_id] = node
        session.node_ready[party_id] = True

        logger.info(f"Session {session_id}: Node {party_id} registered")

        if session.all_nodes_ready():
            session.state = SessionState.NODES_READY
            session._nodes_ready_event.set()
            logger.info(f"Session {session_id}: All nodes ready")

    async def wait_for_nodes(
        self,
        session_id: int,
        timeout: float = 60.0,
    ) -> None:
        """
        Wait for all nodes to be ready

        Args:
            session_id: Session to wait for
            timeout: Timeout in seconds
        """
        session = self._get_session(session_id)

        try:
            await asyncio.wait_for(
                session._nodes_ready_event.wait(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            ready = sum(1 for r in session.node_ready.values() if r)
            raise TimeoutError(
                f"Timed out waiting for nodes: {ready}/{session.n_parties} ready"
            )

    async def signal_preprocessing(
        self,
        session_id: int,
        timeout: float = 60.0,
    ) -> None:
        """
        Signal all nodes to run preprocessing phase

        This tells nodes to generate/receive their preprocessing material
        (Beaver triples, random shares, etc.)

        Args:
            session_id: Session to preprocess
            timeout: Timeout for preprocessing to complete
        """
        session = self._get_session(session_id)

        if session.state != SessionState.NODES_READY:
            await self.wait_for_nodes(session_id, timeout)

        session.state = SessionState.PREPROCESSING
        logger.info(f"Session {session_id}: Signaling PREPROCESSING to all nodes")

        # Signal all nodes to run preprocessing
        preprocessing_tasks = []
        for party_id, node in session.nodes.items():
            task = asyncio.create_task(
                self._node_preprocessing(session, party_id, node)
            )
            preprocessing_tasks.append(task)

        # Wait for all nodes to complete preprocessing
        try:
            await asyncio.wait_for(
                asyncio.gather(*preprocessing_tasks),
                timeout=timeout,
            )
            session._preprocessing_done_event.set()
            logger.info(f"Session {session_id}: Preprocessing complete on all nodes")
        except asyncio.TimeoutError:
            session.state = SessionState.FAILED
            raise TimeoutError("Preprocessing timed out")

    async def _node_preprocessing(
        self,
        session: MPCSession,
        party_id: int,
        node: "MPCServer",
    ) -> None:
        """Run preprocessing on a single node"""
        logger.debug(f"Session {session.session_id}: Node {party_id} preprocessing")
        # In a real implementation, this would call node.run_preprocessing()
        # For now, nodes handle this internally or it's a no-op
        await asyncio.sleep(0)  # Yield to event loop

    async def signal_await_inputs(
        self,
        session_id: int,
    ) -> None:
        """
        Signal all nodes to start accepting client input shares

        After this signal, clients can send their input shares to nodes.

        Args:
            session_id: Session to signal
        """
        session = self._get_session(session_id)

        session.state = SessionState.AWAITING_INPUTS
        logger.info(f"Session {session_id}: Signaling AWAIT_INPUTS to all nodes")

        # Nodes are now ready to receive input shares from clients
        # The actual input handling is done by the nodes themselves

    async def notify_inputs_received(
        self,
        session_id: int,
        client_id: int,
    ) -> None:
        """
        Notify coordinator that a client's inputs have been received by nodes

        Called by nodes or clients to signal input delivery is complete.

        Args:
            session_id: Session ID
            client_id: Client whose inputs were received
        """
        session = self._get_session(session_id)

        if client_id not in session.expected_clients:
            raise ValueError(f"Unexpected client {client_id}")

        session.client_inputs_received[client_id] = True
        logger.info(f"Session {session_id}: Inputs from client {client_id} received")

        if session.all_inputs_received():
            session.state = SessionState.INPUTS_RECEIVED
            session._inputs_received_event.set()
            logger.info(f"Session {session_id}: All client inputs received")

    async def wait_for_inputs(
        self,
        session_id: int,
        timeout: float = 60.0,
    ) -> None:
        """
        Wait for all expected client inputs to be received

        Args:
            session_id: Session to wait for
            timeout: Timeout in seconds
        """
        session = self._get_session(session_id)

        try:
            await asyncio.wait_for(
                session._inputs_received_event.wait(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            received = sum(1 for r in session.client_inputs_received.values() if r)
            expected = len(session.expected_clients)
            raise TimeoutError(
                f"Timed out waiting for inputs: {received}/{expected} clients"
            )

    async def signal_compute(
        self,
        session_id: int,
        timeout: float = 60.0,
    ) -> None:
        """
        Signal all nodes to execute the MPC computation

        Nodes will execute the bytecode using their input shares and
        preprocessing material.

        Args:
            session_id: Session to compute
            timeout: Timeout for computation
        """
        session = self._get_session(session_id)

        if session.state != SessionState.INPUTS_RECEIVED:
            await self.wait_for_inputs(session_id, timeout)

        session.state = SessionState.COMPUTING
        logger.info(f"Session {session_id}: Signaling COMPUTE to all nodes")

        # Signal all nodes to compute
        compute_tasks = []
        for party_id, node in session.nodes.items():
            task = asyncio.create_task(
                self._node_compute(session, party_id, node)
            )
            compute_tasks.append(task)

        # Wait for computation to complete
        try:
            await asyncio.wait_for(
                asyncio.gather(*compute_tasks),
                timeout=timeout,
            )
            logger.info(f"Session {session_id}: Computation complete on all nodes")
        except asyncio.TimeoutError:
            session.state = SessionState.FAILED
            raise TimeoutError("Computation timed out")

    async def _node_compute(
        self,
        session: MPCSession,
        party_id: int,
        node: "MPCServer",
    ) -> None:
        """Run computation on a single node"""
        logger.debug(f"Session {session.session_id}: Node {party_id} computing")
        # In a real implementation, this would call node.compute()
        await asyncio.sleep(0)  # Yield to event loop

    async def signal_send_outputs(
        self,
        session_id: int,
        timeout: float = 60.0,
    ) -> None:
        """
        Signal all nodes to send output shares to clients

        Args:
            session_id: Session ID
            timeout: Timeout for output distribution
        """
        session = self._get_session(session_id)

        session.state = SessionState.OUTPUTTING
        logger.info(f"Session {session_id}: Signaling SEND_OUTPUTS to all nodes")

        # Signal nodes to send outputs
        output_tasks = []
        for party_id, node in session.nodes.items():
            task = asyncio.create_task(
                self._node_send_outputs(session, party_id, node)
            )
            output_tasks.append(task)

        try:
            await asyncio.wait_for(
                asyncio.gather(*output_tasks),
                timeout=timeout,
            )
            session.state = SessionState.COMPLETED
            session._computation_done_event.set()
            logger.info(f"Session {session_id}: Output distribution complete")
        except asyncio.TimeoutError:
            session.state = SessionState.FAILED
            raise TimeoutError("Output distribution timed out")

    async def _node_send_outputs(
        self,
        session: MPCSession,
        party_id: int,
        node: "MPCServer",
    ) -> None:
        """Send outputs from a single node"""
        logger.debug(f"Session {session.session_id}: Node {party_id} sending outputs")
        # In a real implementation, this would call node.send_outputs()
        await asyncio.sleep(0)  # Yield to event loop

    async def run_computation(
        self,
        session_id: int,
        timeout: float = 60.0,
    ) -> ComputationResult:
        """
        Convenience method to run the full computation pipeline

        This orchestrates all phases in sequence:
        1. Wait for nodes
        2. Preprocessing
        3. Await inputs (must be provided externally)
        4. Compute
        5. Send outputs

        Note: This method assumes inputs will be provided by clients
        connecting directly to nodes. For testing without real clients,
        use submit_mock_inputs() before calling this.

        Args:
            session_id: Session to run
            timeout: Overall timeout

        Returns:
            ComputationResult
        """
        session = self._get_session(session_id)

        try:
            # Phase 1: Ensure nodes are ready
            await self.wait_for_nodes(session_id, timeout)

            # Phase 2: Preprocessing
            await self.signal_preprocessing(session_id, timeout)

            # Phase 3: Await inputs
            await self.signal_await_inputs(session_id)

            # Phase 4: Wait for inputs and compute
            await self.wait_for_inputs(session_id, timeout)
            await self.signal_compute(session_id, timeout)

            # Phase 5: Distribute outputs
            await self.signal_send_outputs(session_id, timeout)

            # Return success result
            session.results = ComputationResult(
                session_id=session_id,
                outputs=[],  # Actual outputs are sent to clients by nodes
                success=True,
                metadata={
                    "n_parties": session.n_parties,
                    "n_clients": len(session.expected_clients),
                },
            )
            return session.results

        except Exception as e:
            logger.error(f"Session {session_id}: Failed - {e}")
            session.state = SessionState.FAILED
            session.results = ComputationResult(
                session_id=session_id,
                outputs=[],
                success=False,
                error=str(e),
            )
            return session.results

    async def submit_mock_inputs(
        self,
        session_id: int,
        client_id: int,
        inputs: List[int],
    ) -> None:
        """
        Submit mock inputs for testing (bypasses real client-node communication)

        This is a testing convenience that simulates a client sending inputs
        to all nodes. In production, clients would connect to nodes directly.

        Args:
            session_id: Session ID
            client_id: Client providing inputs
            inputs: The input values
        """
        session = self._get_session(session_id)

        if client_id not in session.expected_clients:
            raise ValueError(f"Client {client_id} not expected in session")

        logger.info(
            f"Session {session_id}: Mock inputs from client {client_id}: {inputs}"
        )

        # Mark inputs as received
        await self.notify_inputs_received(session_id, client_id)

    def get_session_state(self, session_id: int) -> SessionState:
        """Get the current state of a session"""
        return self._get_session(session_id).state

    def get_nodes(self, session_id: int) -> Dict[int, "MPCServer"]:
        """Get the nodes for a session (for testing/direct access)"""
        return self._get_session(session_id).nodes

    def list_sessions(self) -> List[int]:
        """List all session IDs"""
        return list(self._sessions.keys())

    async def close_session(self, session_id: int) -> None:
        """Close and cleanup a session"""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            # Cleanup nodes if we created them
            session.nodes.clear()
            del self._sessions[session_id]
            logger.info(f"Session {session_id} closed")

    def _get_session(self, session_id: int) -> MPCSession:
        """Get a session by ID"""
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")
        return self._sessions[session_id]
