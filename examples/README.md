# Stoffel Python SDK Examples

This directory contains examples demonstrating the Stoffel Python SDK.

## Examples

### `simple_api_demo.py` - Quick Start
**Recommended for most users**

```bash
python examples/simple_api_demo.py
```

Demonstrates:
- Basic builder pattern (`Stoffel.compile(...).parties(...).build()`)
- Creating MPC participants (clients, servers)
- Clean API design principles
- Exception hierarchy

### `correct_flow.py` - Complete MPC Workflow
**Comprehensive example showing full MPC workflows**

```bash
python examples/correct_flow.py
```

Demonstrates:
- Client-server MPC architecture
- Peer-to-peer MPC architecture using MPCNode
- Network topology configuration with NetworkBuilder
- TOML config file usage
- Architecture overview

### `vm_example.py` - Advanced VM Operations
**For advanced users needing low-level VM control**

```bash
python examples/vm_example.py
```

Note: Requires the Stoffel VM shared library to be installed.

## Quick Start

```python
from stoffel import Stoffel

# Compile and configure MPC
runtime = (Stoffel.compile("main main() -> int64: return 42")
    .parties(5)
    .threshold(1)
    .build())

# Create participants
client = runtime.client(100).with_inputs([42]).build()
server = runtime.server(0).build()
```

## Architecture Overview

```
Stoffel.compile()/load()
    |
    v
StoffelBuilder (configure MPC params)
    |
    v
StoffelRuntime (holds Program + config)
    |
    v
MPCClient / MPCServer / MPCNode (participants)
```

## MPC Participant Types

| Type | Role | Use Case |
|------|------|----------|
| `MPCClient` | Input provider | Send secret-shared inputs, receive results |
| `MPCServer` | Compute node | Run secure computation on shares |
| `MPCNode` | Both | Peer-to-peer MPC where all parties have inputs |

## Configuration

MPC parameters are configured via the builder pattern:

```python
runtime = (Stoffel.compile(source)
    .parties(5)              # Number of parties
    .threshold(1)            # Fault tolerance (n >= 3t+1)
    .instance_id(42)         # Computation instance ID
    .protocol(ProtocolType.HONEYBADGER)  # MPC protocol
    .share_type(ShareType.ROBUST)        # Secret sharing scheme
    .build())
```

Or load from a TOML file:

```python
runtime = (Stoffel.compile(source)
    .network_config_file("stoffel.toml")
    .build())
```

## Advanced Module

For lower-level control, use the advanced module:

```python
from stoffel.advanced import ShareManager, NetworkBuilder

# Manual secret sharing
manager = ShareManager(n_parties=5, threshold=1)
shares = manager.create_shares(42)

# Custom network topology
topology = (NetworkBuilder(n_parties=5)
    .localhost(base_port=19200)
    .full_mesh()
    .build())
```

## Note

Actual MPC execution requires PyO3 bindings to the Rust core, which are coming soon.
Currently, the API structure is implemented with placeholder implementations.
