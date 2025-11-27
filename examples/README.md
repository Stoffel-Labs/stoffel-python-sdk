# Stoffel SDK Examples

This directory contains examples demonstrating how to use the Stoffel Python SDK
for secure multiparty computation (MPC).

## Main Example

**`main.py`** - Complete MPC workflow with coordinator

```bash
python examples/main.py
```

This example demonstrates:

1. **Creating a Coordinator** - The coordinator orchestrates computation phases
2. **Loading a Program** - Compile or load pre-compiled Stoffel bytecode
3. **Configuring MPC** - Set parties, threshold, protocol, and share type
4. **Creating a Session** - Coordinator spawns MPC nodes
5. **Client Connection** - Clients connect to coordinator and nodes
6. **Computation Phases**:
   - PREPROCESSING: Nodes generate Beaver triples and random shares
   - AWAIT_INPUTS: Nodes accept secret-shared inputs from clients
   - COMPUTE: Nodes execute the MPC computation
   - SEND_OUTPUTS: Nodes send output shares to clients
7. **Output Reconstruction** - Clients reconstruct final outputs

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COORDINATOR                                  │
│  Orchestrates computation phases (does NOT compute)                 │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌───────────┐  ┌───────────┐  ┌───────────┐
            │  Node 0   │  │  Node 1   │  │  Node 2   │  ...
            │ (compute) │  │ (compute) │  │ (compute) │
            └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
                  │              │              │
                  └──────────────┼──────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            ┌───────────────┐        ┌───────────────┐
            │   Client A    │        │   Client B    │
            │  (inputs)     │        │  (inputs)     │
            └───────────────┘        └───────────────┘
```

**Key Points:**
- Coordinator orchestrates WHEN things happen, but doesn't compute
- Clients send inputs DIRECTLY to nodes (secret-shared)
- Nodes send outputs DIRECTLY to clients
- Clients reconstruct outputs locally

## Quick Start

```python
from stoffel import Stoffel
from stoffel.coordinator import MockMPCCoordinator, CoordinatorClient

# Create coordinator (for local testing)
coordinator = MockMPCCoordinator()

# Load program with MPC configuration
runtime = (
    Stoffel.load(bytecode)  # or Stoffel.compile(source)
    .parties(4)
    .threshold(1)
    .build()
)

# Create session
session_id = await coordinator.create_session(
    runtime,
    expected_clients=[100, 101],
)

# Create client and connect
client = CoordinatorClient(client_id=100)
client.connect_to_coordinator(coordinator)

# Coordinator orchestrates computation phases
await coordinator.signal_preprocessing(session_id)
await coordinator.signal_await_inputs(session_id)

# Client sends inputs to nodes
await client.send_inputs_to_nodes(session_id, inputs=[42, 17])

# Coordinator continues orchestration
await coordinator.signal_compute(session_id)
await coordinator.signal_send_outputs(session_id)

# Client receives outputs
outputs = await client.receive_outputs_from_nodes(session_id)
```

## Production vs Mock Mode

**Mock Mode (for development):**
- Uses `MockMPCCoordinator`
- Nodes are created locally in-process
- No actual cryptographic computation (simulated)

**Production Mode:**
- Connect to external coordinator service
- Nodes run as separate processes/services
- Real MPC protocol execution with networking
