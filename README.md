# Stoffel Python SDK

[![CI](https://github.com/stoffel-labs/stoffel-python-sdk/workflows/CI/badge.svg)](https://github.com/stoffel-labs/stoffel-python-sdk/actions)
[![PyPI version](https://badge.fury.io/py/stoffel-python-sdk.svg)](https://badge.fury.io/py/stoffel-python-sdk)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A clean, high-level Python SDK for the Stoffel framework, providing easy access to Stoffel program compilation and secure multi-party computation (MPC) networks.

## Overview

The Stoffel Python SDK provides a simple, developer-friendly interface with proper separation of concerns:

- **Stoffel**: Entry point with builder pattern for compilation and configuration
- **StoffelRuntime**: Holds compiled program and MPC configuration
- **MPCClient/MPCServer/MPCNode**: MPC participants for different network architectures

This SDK enables developers to:
- Compile and execute Stoffel programs locally
- Connect to MPC networks for secure multi-party computation
- Manage private data with automatic secret sharing
- Reconstruct results from distributed computation
- Build privacy-preserving applications without understanding cryptographic details

## Installation

### Prerequisites

- Python 3.8 or higher
- Poetry (recommended) or pip
- Stoffel VM shared library (`libstoffel_vm.so` or `libstoffel_vm.dylib`)
- Stoffel compiler (for compiling `.stfl` programs)

### Install with Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/stoffel-labs/stoffel-python-sdk.git
cd stoffel-python-sdk

# Install with Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### Install with pip

```bash
# Clone and install
git clone https://github.com/stoffel-labs/stoffel-python-sdk.git
cd stoffel-python-sdk
pip install .

# Or install from PyPI (when published)
pip install stoffel-python-sdk
```

## Quick Start

### Simple MPC Computation

```python
from stoffel import Stoffel, ProtocolType

# 1. Compile and configure MPC parameters
runtime = (Stoffel.compile("main main() -> int64: return 42")
    .parties(4)              # HoneyBadger MPC requires n >= 3
    .threshold(1)            # Fault tolerance (n >= 3t+1)
    .instance_id(42)
    .protocol(ProtocolType.HONEYBADGER)
    .build())

# 2. Create MPC participants
# Client provides secret inputs
client = (runtime.client(100)
    .with_inputs([25, 17])
    .build())

# Servers perform the computation
servers = [
    runtime.server(i).with_preprocessing(10, 25).build()
    for i in range(4)
]

# 3. Access program info
print(f"Program bytecode: {runtime.program().bytecode()[:20]}...")
print(f"MPC config: n={runtime.mpc_config()[0]}, t={runtime.mpc_config()[1]}")
```

### Peer-to-Peer MPC with Nodes

```python
from stoffel import Stoffel
from stoffel.advanced import NetworkBuilder

# Setup runtime
runtime = (Stoffel.load(b"compiled_bytecode")
    .parties(4)
    .threshold(1)
    .build())

# Create nodes (each party provides inputs AND computes)
nodes = []
for party_id in range(4):
    node = (runtime.node(party_id)
        .with_inputs([10 * party_id, 20 * party_id])
        .with_preprocessing(5, 12)
        .build())
    nodes.append(node)

# Configure network topology
topology = (NetworkBuilder(n_parties=4)
    .localhost(base_port=19300)
    .full_mesh()
    .build())
```

## Examples

The `examples/` directory contains comprehensive examples:

### Simple API Demo (Recommended for Most Users)

```bash
poetry run python examples/simple_api_demo.py
```

### Complete Architecture Example

```bash
poetry run python examples/correct_flow.py
```

### Advanced VM Operations

```bash
poetry run python examples/vm_example.py
```

## API Reference

### Main API

#### `Stoffel` - Entry Point

```python
class Stoffel:
    @staticmethod
    def compile(source: str) -> StoffelBuilder

    @staticmethod
    def compile_file(path: str) -> StoffelBuilder

    @staticmethod
    def load(bytecode: bytes) -> StoffelBuilder
```

#### `StoffelBuilder` - Configuration

```python
class StoffelBuilder:
    def parties(self, n: int) -> StoffelBuilder
    def threshold(self, t: int) -> StoffelBuilder
    def instance_id(self, id: int) -> StoffelBuilder
    def protocol(self, protocol: ProtocolType) -> StoffelBuilder
    def share_type(self, share_type: ShareType) -> StoffelBuilder
    def network_config_file(self, path: str) -> StoffelBuilder
    def build(self) -> StoffelRuntime
```

#### `StoffelRuntime` - Runtime Access

```python
class StoffelRuntime:
    def program(self) -> Program
    def client(self, client_id: int) -> MPCClientBuilder
    def server(self, party_id: int) -> MPCServerBuilder
    def node(self, party_id: int) -> MPCNodeBuilder
    def mpc_config(self) -> Tuple[int, int]  # (n_parties, threshold)
```

### MPC Participants

#### `MPCClient` - Input Provider

```python
class MPCClientBuilder:
    def with_inputs(self, inputs: List[Any]) -> MPCClientBuilder
    def build(self) -> MPCClient

class MPCClient:
    def generate_input_shares_robust(self) -> List[bytes]
    def generate_input_shares_non_robust(self) -> List[bytes]
    def receive_outputs(self, shares: List[bytes]) -> Any
```

#### `MPCServer` - Compute Node

```python
class MPCServerBuilder:
    def with_preprocessing(self, triples: int, randoms: int) -> MPCServerBuilder
    def build(self) -> MPCServer

class MPCServer:
    def run_preprocessing(self) -> None
    def receive_client_inputs(self, client_id: int, shares: List[bytes]) -> None
    def compute(self, bytecode: bytes) -> List[bytes]
    def add_peer(self, peer_id: int, address: str) -> None
```

#### `MPCNode` - Combined Client+Server

```python
class MPCNodeBuilder:
    def with_inputs(self, inputs: List[Any]) -> MPCNodeBuilder
    def with_preprocessing(self, triples: int, randoms: int) -> MPCNodeBuilder
    def build(self) -> MPCNode

class MPCNode:
    def run(self, bytecode: bytes) -> Any
```

### Advanced Module

```python
from stoffel.advanced import ShareManager, NetworkBuilder

# Low-level secret sharing
manager = ShareManager(n_parties=4, threshold=1)
shares = manager.create_shares(42)
reconstructed = manager.reconstruct(shares)

# Network topology configuration
topology = (NetworkBuilder(n_parties=4)
    .localhost(base_port=19200)
    .full_mesh()
    .build())
```

## MPC Protocol Requirements

The Stoffel SDK uses **HoneyBadger MPC** which requires:
- **Minimum 3 parties** (`n >= 3`)
- **Byzantine fault tolerance**: `n >= 3t + 1` where `t` is the threshold

Common configurations:
- `parties(3).threshold(0)` - 3 parties, no fault tolerance
- `parties(4).threshold(1)` - 4 parties, tolerates 1 fault
- `parties(7).threshold(2)` - 7 parties, tolerates 2 faults

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=stoffel

# Run specific test file
poetry run pytest tests/test_stoffel.py
```

### Code Quality

```bash
# Format code
poetry run black stoffel/ tests/ examples/

# Sort imports
poetry run isort stoffel/ tests/ examples/

# Lint code
poetry run flake8 stoffel/ tests/ examples/

# Type checking
poetry run mypy stoffel/
```

## Architecture

The SDK provides a clean, high-level interface with proper separation of concerns:

### Main Components

**Stoffel** - Entry point with builder pattern for compilation and configuration

**StoffelRuntime** - Holds compiled program and MPC configuration, creates participants

**Program** - Compiled bytecode with save/load capabilities

**MPC Participants**:
- `MPCClient`: Input providers with secret sharing
- `MPCServer`: Compute nodes with preprocessing
- `MPCNode`: Combined for peer-to-peer architectures

### Design Principles

- **Builder Pattern**: Fluent API for configuration
- **Simple Public API**: All internal complexity hidden behind intuitive methods
- **Generic Field Operations**: Not tied to specific cryptographic curves
- **MPC-as-a-Service**: Client-side interface to MPC networks
- **Clean Architecture**: Clear boundaries between Program, Client, Server, Node

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`poetry run pytest`)
6. Run code quality checks (`poetry run black . && poetry run flake8 .`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Status

**This project is under active development**

- Stoffel entry point with builder pattern
- MPCClient, MPCServer, MPCNode participants
- NetworkConfig with TOML support
- Advanced module (ShareManager, NetworkBuilder)
- Stoffel VM FFI bindings
- MPC network integration (awaiting PyO3 bindings)

## Related Projects

- [Stoffel VM](https://github.com/stoffel-labs/stoffel-vm) - The core virtual machine with MPC integration
- [MPC Protocols](https://github.com/stoffel-labs/mpc-protocols) - Rust implementation of MPC protocols
- [Stoffel Lang](https://github.com/stoffel-labs/stoffel-lang) - The programming language that compiles to Stoffel VM

## Support

- [Documentation](docs/)
- [Issue Tracker](https://github.com/stoffel-labs/stoffel-python-sdk/issues)
- [Discussions](https://github.com/stoffel-labs/stoffel-python-sdk/discussions)
