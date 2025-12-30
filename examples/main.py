#!/usr/bin/env python3
"""
Stoffel SDK Example - MPC Computation with Coordinator

This example demonstrates the complete workflow for running secure multiparty
computation (MPC) using the Stoffel SDK with a coordinator.

Architecture Overview:
- Coordinator: Orchestrates computation phases (preprocessing, input, compute, output)
- Servers (Nodes): Execute the actual MPC protocol
- Clients: Provide secret-shared inputs and receive outputs

The coordinator tells nodes WHEN to execute each phase, but the nodes
perform the actual cryptographic computation.

Usage:
    python examples/main.py

Requirements:
    - Python 3.8+
    - No native bindings required for this example (uses mock mode)
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stoffel import (
    Stoffel,
    ProtocolType,
    ShareType,
)
from stoffel.coordinator import (
    MockMPCCoordinator,
    CoordinatorClient,
    SessionState,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# MPC Network Configuration
N_PARTIES = 4           # Number of MPC servers (nodes)
THRESHOLD = 1           # Byzantine fault tolerance (can tolerate t faults)
BASE_PORT = 19200       # Starting port for localhost networking

# Client Configuration
CLIENT_IDS = [100, 101]  # Two clients providing inputs
CLIENT_INPUTS = {
    100: [42, 10],       # Client 100's private inputs
    101: [17, 5],        # Client 101's private inputs
}


# =============================================================================
# Main Example
# =============================================================================

async def run_mpc_example():
    """
    Run a complete MPC computation example.

    This demonstrates:
    1. Setting up the coordinator
    2. Compiling/loading a Stoffel program
    3. Configuring MPC parameters
    4. Creating a computation session
    5. Clients connecting and providing inputs
    6. Coordinator orchestrating computation phases
    7. Clients receiving outputs
    """
    print("=" * 70)
    print("STOFFEL SDK - MPC Computation Example")
    print("=" * 70)
    print()

    # =========================================================================
    # Step 1: Create the Coordinator
    # =========================================================================
    print("Step 1: Creating MPC Coordinator")
    print("-" * 40)

    # In production, you would connect to an external coordinator service.
    # For local development and testing, use MockMPCCoordinator.
    coordinator = MockMPCCoordinator(auto_start_nodes=True)
    print(f"  Created mock coordinator (auto_start_nodes=True)")
    print()

    # =========================================================================
    # Step 2: Compile/Load Stoffel Program
    # =========================================================================
    print("Step 2: Loading Stoffel Program")
    print("-" * 40)

    # Option A: Compile from source (requires native compiler bindings)
    # runtime = (Stoffel.compile("""
    #     def add(a: int64, b: int64) -> int64:
    #       return a + b
    #
    #     main main() -> int64:
    #       return add(input(0), input(1))
    # """)

    # Option B: Load pre-compiled bytecode
    # runtime = Stoffel.load(bytecode_from_file)

    # Option C: For testing without native bindings, use mock bytecode
    # The coordinator will handle computation orchestration
    runtime = (
        Stoffel.load(b"mock_bytecode")
        .parties(N_PARTIES)
        .threshold(THRESHOLD)
        .instance_id(1)
        .protocol(ProtocolType.HONEYBADGER)
        .share_type(ShareType.ROBUST)
        .build()
    )

    n, t, instance = runtime.mpc_config()
    print(f"  Program loaded with MPC configuration:")
    print(f"    - Parties (n): {n}")
    print(f"    - Threshold (t): {t}")
    print(f"    - Protocol: {runtime.protocol_type().value}")
    print(f"    - Share Type: {runtime.share_type().value}")
    print(f"    - Instance ID: {instance}")
    print()

    # =========================================================================
    # Step 3: Create Computation Session
    # =========================================================================
    print("Step 3: Creating Computation Session")
    print("-" * 40)

    session_id = await coordinator.create_session(
        runtime,
        expected_clients=CLIENT_IDS,
    )

    print(f"  Session {session_id} created")
    print(f"  State: {coordinator.get_session_state(session_id).name}")
    print(f"  Expected clients: {CLIENT_IDS}")

    # Get node information
    nodes = coordinator.get_nodes(session_id)
    print(f"  Nodes spawned: {len(nodes)}")
    for party_id in sorted(nodes.keys()):
        # In production, nodes would have network addresses
        port = BASE_PORT + party_id
        print(f"    - Node {party_id}: localhost:{port}")
    print()

    # =========================================================================
    # Step 4: Create Clients and Connect to Coordinator
    # =========================================================================
    print("Step 4: Creating and Connecting Clients")
    print("-" * 40)

    clients = {}
    for client_id in CLIENT_IDS:
        client = CoordinatorClient(client_id=client_id)
        client.connect_to_coordinator(coordinator)
        clients[client_id] = client
        print(f"  Client {client_id} connected to coordinator")
    print()

    # =========================================================================
    # Step 5: Coordinator Orchestrates Computation Phases
    # =========================================================================
    print("Step 5: Coordinator Orchestrating Computation")
    print("-" * 40)

    # Phase 1: Preprocessing
    print("\n  Phase 1: PREPROCESSING")
    print("    Signaling nodes to generate preprocessing material...")
    await coordinator.signal_preprocessing(session_id)
    print(f"    State: {coordinator.get_session_state(session_id).name}")
    print("    Nodes generated Beaver triples and random shares")

    # Phase 2: Accept Inputs
    print("\n  Phase 2: AWAIT_INPUTS")
    print("    Signaling nodes to accept client inputs...")
    await coordinator.signal_await_inputs(session_id)
    print(f"    State: {coordinator.get_session_state(session_id).name}")

    # Clients send inputs to nodes
    print("\n    Clients sending inputs to nodes:")
    for client_id, inputs in CLIENT_INPUTS.items():
        # In production, clients would:
        # 1. Get node addresses from coordinator
        # 2. Secret-share inputs
        # 3. Send shares directly to nodes
        # For mock mode, we simulate this:
        await clients[client_id].send_inputs_to_nodes(session_id, inputs)
        print(f"      Client {client_id}: sent inputs {inputs}")

    print(f"    State: {coordinator.get_session_state(session_id).name}")

    # Phase 3: Compute
    print("\n  Phase 3: COMPUTE")
    print("    Signaling nodes to execute MPC computation...")
    await coordinator.signal_compute(session_id)
    print(f"    State: {coordinator.get_session_state(session_id).name}")
    print("    Nodes executed secure computation on secret shares")

    # Phase 4: Output Distribution
    print("\n  Phase 4: SEND_OUTPUTS")
    print("    Signaling nodes to send output shares to clients...")
    await coordinator.signal_send_outputs(session_id)
    print(f"    State: {coordinator.get_session_state(session_id).name}")

    # Clients receive outputs
    print("\n    Clients receiving output shares:")
    for client_id, client in clients.items():
        # In production, clients would:
        # 1. Receive output shares from nodes
        # 2. Reconstruct the output using Lagrange interpolation
        outputs = await client.receive_outputs_from_nodes(session_id)
        print(f"      Client {client_id}: received outputs {outputs}")
    print()

    # =========================================================================
    # Step 6: Cleanup
    # =========================================================================
    print("Step 6: Cleanup")
    print("-" * 40)

    await coordinator.close_session(session_id)
    print(f"  Session {session_id} closed")
    print()

    # =========================================================================
    # Summary
    # =========================================================================
    print("=" * 70)
    print("COMPUTATION COMPLETE")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Coordinator orchestrated {N_PARTIES} MPC nodes")
    print(f"  - {len(CLIENT_IDS)} clients provided inputs")
    print(f"  - Computation phases: PREPROCESSING → INPUTS → COMPUTE → OUTPUTS")
    print(f"  - Protocol: HoneyBadger MPC with Robust secret sharing")
    print()


async def run_simple_example():
    """
    Simplified example using the convenience method.

    For quick testing, you can use run_computation() which
    handles all phases automatically.
    """
    print("=" * 70)
    print("STOFFEL SDK - Simple Example (Convenience API)")
    print("=" * 70)
    print()

    # Create coordinator
    coordinator = MockMPCCoordinator()

    # Load program with MPC config
    runtime = (
        Stoffel.load(b"mock")
        .parties(4)
        .threshold(1)
        .instance_id(1)
        .build()
    )

    # Create session
    session_id = await coordinator.create_session(
        runtime,
        expected_clients=[100, 101],
    )
    print(f"Session {session_id} created")

    # Submit mock inputs (simulating clients)
    await coordinator.submit_mock_inputs(session_id, client_id=100, inputs=[42, 10])
    await coordinator.submit_mock_inputs(session_id, client_id=101, inputs=[17, 5])
    print("Inputs submitted")

    # Run all phases automatically
    result = await coordinator.run_computation(session_id)

    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Metadata: {result.metadata}")

    await coordinator.close_session(session_id)
    print("\nDone!")


def print_architecture():
    """Print the SDK architecture overview."""
    print()
    print("=" * 70)
    print("STOFFEL SDK ARCHITECTURE")
    print("=" * 70)
    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                         COORDINATOR                                  │
│  Orchestrates computation phases (does NOT compute)                 │
│                                                                      │
│  • signal_preprocessing()  - Tell nodes to generate triples         │
│  • signal_await_inputs()   - Tell nodes to accept client shares     │
│  • signal_compute()        - Tell nodes to execute computation      │
│  • signal_send_outputs()   - Tell nodes to send results to clients  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌───────────┐  ┌───────────┐  ┌───────────┐
            │  Node 0   │  │  Node 1   │  │  Node 2   │  ...
            │           │  │           │  │           │
            │ • Preproc │  │ • Preproc │  │ • Preproc │
            │ • Compute │  │ • Compute │  │ • Compute │
            └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
                  │              │              │
                  └──────────────┼──────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
            ┌───────────────┐        ┌───────────────┐
            │   Client A    │        │   Client B    │
            │               │        │               │
            │ Inputs: [42]  │        │ Inputs: [17]  │
            │               │        │               │
            │ 1. Secret     │        │ 1. Secret     │
            │    share      │        │    share      │
            │ 2. Send to    │        │ 2. Send to    │
            │    nodes      │        │    nodes      │
            │ 3. Receive    │        │ 3. Receive    │
            │    outputs    │        │    outputs    │
            └───────────────┘        └───────────────┘

FLOW:
1. Clients send input shares DIRECTLY to nodes (not through coordinator)
2. Nodes perform MPC computation (HoneyBadger protocol)
3. Nodes send output shares DIRECTLY to clients
4. Clients reconstruct outputs locally
""")


async def main():
    """Main entry point."""
    print()
    print_architecture()
    print()

    # Run the detailed example
    await run_mpc_example()

    print()
    print("-" * 70)
    print()

    # Run the simple example
    await run_simple_example()


if __name__ == "__main__":
    asyncio.run(main())
