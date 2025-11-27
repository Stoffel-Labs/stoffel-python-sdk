# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Commands (Python-only mode)
- `pip install -e .` - Install in development mode (Python stubs only)
- `pytest` - Run tests
- `pytest --cov=stoffel` - Run tests with coverage
- `black stoffel/ tests/ examples/` - Format code
- `isort stoffel/ tests/ examples/` - Sort imports
- `flake8 stoffel/ tests/ examples/` - Lint code
- `mypy stoffel/` - Type check

### Development Commands (with native ctypes bindings)
- `git submodule update --init --recursive` - Initialize git submodules
- `cd external/stoffel-lang && cargo build --release` - Build compiler library
- `cd external/stoffel-vm && cargo build --release` - Build VM library
- `cd external/mpc-protocols && cargo build --release` - Build MPC library
- `python test_native_bindings.py` - Test native bindings

### Example Commands
- `python examples/simple_api_demo.py` - Run simple API demonstration
- `python examples/correct_flow.py` - Run complete architecture example
- `python examples/vm_example.py` - Run Stoffel VM low-level bindings example

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

**Native Bindings** (`stoffel/_core.py` + `stoffel/native/`):
- Unified interface using ctypes C FFI bindings
- `is_native_available()` checks if native bindings are loaded
- `get_binding_method()` returns 'ctypes' or None

**ctypes C FFI Bindings** (`stoffel/native/`):
- **compiler.py**: NativeCompiler using stoffellang.h C API
- **vm.py**: NativeVM using stoffel_vm.h C API (requires cffi module export)
- **mpc.py**: NativeShareManager using MPC protocols C FFI
- Uses pre-built shared libraries from `external/` submodules
- Build libraries with `cargo build --release` in each external/ subdirectory

**Stoffel VM Integration** (`stoffel/vm/`):
- **vm.py**: VirtualMachine class (legacy ctypes FFI, deprecated)
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
7. **Graceful Degradation**: Works without native bindings (limited functionality)

## Network Architecture

- **Client-Server Model**: Clients provide inputs, servers compute
- **Peer-to-Peer Model**: All parties provide inputs AND compute (MPCNode)
- **NetworkConfig**: TOML-based configuration for deployment
- **NetworkBuilder**: Programmatic network topology creation

## External Dependencies

The SDK uses git submodules for native Rust libraries (`external/`):
- `stoffel-lang` - Stoffel language compiler (exposes C FFI via `stoffellang.h`)
- `stoffel-vm` - Virtual machine runtime (has C FFI in `cffi.rs`, needs export)
- `mpc-protocols` - MPC protocol implementations (exposes C FFI for secret sharing)
- `stoffel-networking` - QUIC networking layer

## Project Structure

```
stoffel-python-sdk/
├── pyproject.toml       # Python package configuration
├── .gitmodules          # Git submodule definitions
├── external/            # Git submodules (Rust dependencies)
│   ├── stoffel-lang/
│   ├── stoffel-vm/
│   ├── mpc-protocols/
│   └── stoffel-networking/
├── stoffel/             # Python package
│   ├── __init__.py     # Main API exports
│   ├── _core.py        # Native bindings wrapper (with fallback)
│   ├── stoffel.py      # Stoffel, StoffelBuilder, StoffelRuntime, Program
│   ├── network_config.py
│   ├── native/         # ctypes C FFI bindings
│   │   ├── __init__.py
│   │   ├── compiler.py # NativeCompiler
│   │   ├── vm.py       # NativeVM
│   │   └── mpc.py      # NativeShareManager
│   ├── compiler/       # Stoffel compiler interface
│   ├── vm/             # Stoffel VM Python bindings (legacy)
│   ├── mpc/            # MPC types and participants
│   └── advanced/       # Low-level APIs
├── examples/
│   ├── simple_api_demo.py
│   ├── correct_flow.py
│   └── vm_example.py
└── tests/
    ├── test_stoffel.py
    ├── test_mpc.py
    ├── test_network_config.py
    ├── test_advanced.py
    └── test_errors.py
```

## Important Notes

- MPC protocol selection happens via Stoffel VM, not direct protocol management
- Secret sharing schemes are completely abstracted from developers
- Field operations are generic, not tied to specific curves like BLS12-381
- HoneyBadger MPC protocol requires n >= 3t + 1 (Byzantine fault tolerance)
- Minimum 3 parties required for HoneyBadger MPC
- Examples demonstrate proper separation of concerns and clean API usage
- Native bindings required for actual compilation and execution
- Uses ctypes to interface with C FFI from pre-built Rust libraries in external/ submodules

## Building Native Libraries

```bash
# Initialize submodules
git submodule update --init --recursive

# Build all native libraries
cd external/stoffel-lang && cargo build --release && cd ../..
cd external/stoffel-vm && cargo build --release && cd ../..
cd external/mpc-protocols && cargo build --release && cd ../..

# Test bindings
python test_native_bindings.py
```

**Note**: The VM C FFI requires adding `pub mod cffi;` to `external/stoffel-vm/crates/stoffel-vm/src/lib.rs` before building. Without this, only compiler and MPC bindings work.
