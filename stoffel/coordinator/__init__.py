"""
MPC Coordinator Module

The coordinator orchestrates the MPC network - it tells nodes what to do and when,
but does NOT perform the computation itself. The nodes do the actual MPC.

Coordinator responsibilities:
1. Signal nodes to run preprocessing phase
2. Signal nodes to collect client input shares
3. Signal nodes to execute the computation
4. Signal nodes to send output shares back to clients

In production, this would be an external service. The mock version
creates and manages local MPC servers for testing.

Components:
- MockMPCCoordinator: Local coordinator for testing (orchestrates nodes)
- MPCSession: Represents a computation session
- SessionState: Session lifecycle states
- CoordinatorCommand: Commands sent to nodes
- CoordinatorClient: Client interface to coordinator service
"""

from .mock_coordinator import (
    MockMPCCoordinator,
    MPCSession,
    SessionState,
    CoordinatorCommand,
    ComputationResult,
)
from .client import CoordinatorClient

__all__ = [
    "MockMPCCoordinator",
    "MPCSession",
    "SessionState",
    "CoordinatorCommand",
    "ComputationResult",
    "CoordinatorClient",
]
