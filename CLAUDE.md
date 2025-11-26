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
- `poetry run python examples/vm_example.py` - Run StoffelVM low-level bindings example

## Architecture

This Python SDK provides a clean, high-level interface for the Stoffel framework with proper separation of concerns:

### Main API Components

**StoffelProgram** (`stoffel/program.py`):
- Handles StoffelLang program compilation and VM operations
- Manages execution parameters and local testing
- VM responsibility: compilation, loading, program lifecycle

**StoffelMPCClient** (`stoffel/client.py`):
- Handles MPC network communication and private data management  
- Manages secret sharing, result reconstruction, network connections
- Client responsibility: network communication, private data, MPC operations

### Clean Separation of Concerns

- **VM/Program**: Compilation, execution parameters, local program execution
- **Client/Network**: MPC communication, secret sharing, result reconstruction  
- **Coordinator** (optional): MPC orchestration and metadata exchange (not node discovery)

### Core Components (`stoffel/vm/`, `stoffel/mpc/`)

**StoffelVM Integration**:
- **vm.py**: VirtualMachine class using ctypes FFI to StoffelVM's C API
- **types.py**: Enhanced with Share types and ShareType enum for MPC integration
- **exceptions.py**: VM-specific exception hierarchy
- Uses ctypes to interface with libstoffel_vm shared library

**MPC Types**:
- **types.py**: Core MPC types (SecretValue, MPCResult, MPCConfig, etc.)
- Abstract MPC types for high-level interface
- Exception hierarchy for MPC-specific errors

## Key Design Principles

1. **Simple Public API**: All internal complexity hidden behind intuitive methods
2. **Proper Abstractions**: Developers don't need to understand secret sharing schemes or protocol details
3. **Generic Field Operations**: Not tied to specific cryptographic curves
4. **MPC-as-a-Service**: Client-side interface to MPC networks rather than full protocol implementation
5. **Clean Architecture**: Clear boundaries between VM, Client, and optional Coordinator

## Network Architecture

- **Direct Connection**: Client connects directly to known MPC nodes
- **Coordinator (Optional)**: Used for metadata exchange and MPC network orchestration (not discovery)
- **MPC Nodes**: Handle actual secure computation on secret shares
- **Client**: Always knows MPC node addresses directly (deployment responsibility)

## FFI Integration

The SDK uses ctypes for FFI integration with:
- `libstoffel_vm.so/.dylib` - StoffelVM C API 
- Future: `libmpc_protocols.so/.dylib` - MPC protocols (skeleton implementation)

FFI interfaces based on C headers in `~/Documents/Stoffel-Labs/dev/StoffelVM/` and `~/Documents/Stoffel-Labs/dev/mpc-protocols/`.

## Project Structure

```
stoffel/
├── __init__.py          # Main API exports (StoffelProgram, StoffelMPCClient)
├── program.py           # StoffelLang compilation and VM management
├── client.py            # MPC network client and communication
├── compiler.py          # StoffelLang compiler interface
├── vm/                  # StoffelVM Python bindings
│   ├── vm.py           # VirtualMachine class with FFI bindings
│   ├── types.py        # Enhanced with Share types for MPC
│   └── exceptions.py   # VM-specific exceptions
└── mpc/                # MPC types and configurations
    └── types.py        # Core MPC types and exceptions

examples/
├── README.md           # Examples documentation and architecture overview
├── simple_api_demo.py  # Minimal usage example (recommended for most users)  
├── correct_flow.py     # Complete architecture demonstration
└── vm_example.py       # Advanced VM bindings usage

tests/
└── test_client.py      # Clean client tests matching final API
```

## Important Notes

- MPC protocol selection happens via StoffelVM, not direct protocol management
- Secret sharing schemes are completely abstracted from developers
- Field operations are generic, not tied to specific curves like BLS12-381  
- Client configuration requires MPC nodes to be specified directly
- Coordinator interaction is limited to metadata exchange when needed
- Examples demonstrate proper separation of concerns and clean API usage