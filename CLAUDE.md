# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Commands
- `poetry install` - Install dependencies
- `poetry run pytest` - Run tests
- `poetry run pytest --cov=stoffel` - Run tests with coverage
- `poetry run black stoffel/ tests/ examples/` - Format code
- `poetry run isort stoffel/ tests/ examples/` - Sort imports
- `poetry run flake8 stoffel/ tests/ examples/` - Lint code
- `poetry run mypy stoffel/` - Type check

### Example Commands
- `poetry run python examples/simple_api_demo.py` - Run simple API demonstration
- `poetry run python examples/correct_flow.py` - Run complete architecture example
- `poetry run python examples/vm_example.py` - Run Stoffel VM low-level bindings example

## Architecture

This Python SDK provides a clean, high-level interface for the Stoffel framework with proper separation of concerns:

### Main API Components

**Stoffel** (`stoffel/stoffel.py`):
- Entry point for the SDK using builder pattern
- `Stoffel.compile(source)` / `Stoffel.compile_file(path)` / `Stoffel.load(bytecode)`
- Returns `StoffelBuilder` for configuration chaining

**StoffelBuilder** (`stoffel/stoffel.py`):
- Configures MPC parameters: `parties()`, `threshold()`, `instance_id()`, `protocol()`, `share_type()`
- `build()` returns `StoffelRuntime`

**StoffelRuntime** (`stoffel/stoffel.py`):
- Access to compiled program via `program()`
- Creates MPC participants: `client(id)`, `server(id)`, `node(id)`

**MPC Participants** (`stoffel/mpc/`):
- `MPCClient`: Input providers with secret sharing
- `MPCServer`: Compute nodes with preprocessing
- `MPCNode`: Combined client+server for peer-to-peer MPC

### Clean Separation of Concerns

- **Program**: Compilation, bytecode management, local execution
- **Client**: Input provision, secret sharing, output reception
- **Server**: Preprocessing, computation, networking
- **Node**: Combined client+server for P2P architectures

### Core Components

**Stoffel VM Integration** (`stoffel/vm/`):
- **vm.py**: VirtualMachine class using ctypes FFI to Stoffel VM's C API
- **types.py**: Value types including Share types for MPC
- **exceptions.py**: VM-specific exception hierarchy

**MPC Types** (`stoffel/mpc/`):
- **types.py**: Core MPC types (SecretValue, MPCResult, MPCConfig, etc.)
- **client.py, server.py, node.py**: MPC participant implementations
- Exception hierarchy for MPC-specific errors

**Advanced Module** (`stoffel/advanced/`):
- **ShareManager**: Low-level secret sharing operations
- **NetworkBuilder**: Custom network topology configuration

## Key Design Principles

1. **Builder Pattern**: Fluent API for configuration
2. **Simple Public API**: All internal complexity hidden behind intuitive methods
3. **Proper Abstractions**: Developers don't need to understand secret sharing schemes
4. **Generic Field Operations**: Not tied to specific cryptographic curves
5. **MPC-as-a-Service**: Client-side interface to MPC networks
6. **Clean Architecture**: Clear boundaries between Program, Client, Server, Node

## Network Architecture

- **Client-Server Model**: Clients provide inputs, servers compute
- **Peer-to-Peer Model**: All parties provide inputs AND compute (MPCNode)
- **NetworkConfig**: TOML-based configuration for deployment
- **NetworkBuilder**: Programmatic network topology creation

## FFI Integration

The SDK uses ctypes for FFI integration with:
- `libstoffel_vm.so/.dylib` - Stoffel VM C API
- Future: PyO3 bindings for improved performance

## Project Structure

```
stoffel/
├── __init__.py          # Main API exports
├── stoffel.py           # Stoffel, StoffelBuilder, StoffelRuntime, Program
├── network_config.py    # NetworkConfig with TOML support
├── program.py           # Legacy StoffelProgram (deprecated)
├── client.py            # Legacy StoffelMPCClient (deprecated)
├── compiler/            # Stoffel compiler interface
├── vm/                  # Stoffel VM Python bindings
│   ├── vm.py           # VirtualMachine class with FFI bindings
│   ├── types.py        # Value types including Share types
│   └── exceptions.py   # VM-specific exceptions
├── mpc/                 # MPC types and participants
│   ├── types.py        # Core MPC types and exceptions
│   ├── client.py       # MPCClient and MPCClientBuilder
│   ├── server.py       # MPCServer and MPCServerBuilder
│   └── node.py         # MPCNode and MPCNodeBuilder
└── advanced/            # Low-level APIs
    ├── share_manager.py # Manual secret sharing operations
    └── network_builder.py # Network topology configuration

examples/
├── README.md           # Examples documentation
├── simple_api_demo.py  # Minimal usage example
├── correct_flow.py     # Complete MPC workflow demonstration
└── vm_example.py       # Advanced VM bindings usage

tests/
├── test_stoffel.py     # Main API tests
├── test_mpc.py         # MPC participant tests
├── test_network_config.py # Network configuration tests
├── test_advanced.py    # Advanced module tests
└── test_errors.py      # Exception hierarchy tests
```

## Important Notes

- MPC protocol selection happens via Stoffel VM, not direct protocol management
- Secret sharing schemes are completely abstracted from developers
- Field operations are generic, not tied to specific curves like BLS12-381
- HoneyBadger MPC protocol requires n >= 3t + 1 (Byzantine fault tolerance)
- Examples demonstrate proper separation of concerns and clean API usage
