# Stoffel Python SDK

[![CI](https://github.com/stoffel-labs/stoffel-python-sdk/workflows/CI/badge.svg)](https://github.com/stoffel-labs/stoffel-python-sdk/actions)
[![PyPI version](https://badge.fury.io/py/stoffel-python-sdk.svg)](https://badge.fury.io/py/stoffel-python-sdk)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A clean, high-level Python SDK for the Stoffel framework, providing easy access to StoffelLang program compilation and secure multi-party computation (MPC) networks.

## Overview

The Stoffel Python SDK provides a simple, developer-friendly interface with proper separation of concerns:

- **StoffelProgram**: Handles StoffelLang compilation, VM operations, and execution parameters  
- **StoffelClient**: Handles MPC network communication, public/secret data, and result reconstruction

This SDK enables developers to:
- Compile and execute StoffelLang programs locally
- Connect to MPC networks for secure multi-party computation
- Manage private data with automatic secret sharing
- Reconstruct results from distributed computation
- Build privacy-preserving applications without understanding cryptographic details

## Installation

### Prerequisites

- Python 3.8 or higher
- Poetry (recommended) or pip
- StoffelVM shared library (`libstoffel_vm.so` or `libstoffel_vm.dylib`)
- StoffelLang compiler (for compiling `.stfl` programs)

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
import asyncio
from stoffel import StoffelProgram, StoffelClient

async def main():
    # 1. Program Setup (VM handles compilation and parameters)
    program = StoffelProgram("secure_add.stfl")  # Your StoffelLang program
    program.compile()
    program.set_execution_params({
        "computation_id": "secure_addition",
        "function_name": "main",
        "expected_inputs": ["a", "b", "threshold"]
    })
    
    # 2. Stoffel Client Setup (handles network communication)
    client = StoffelClient({
        "nodes": ["http://mpc-node1:9000", "http://mpc-node2:9000", "http://mpc-node3:9000"],
        "client_id": "client_001",
        "program_id": "secure_addition"
    })
    
    # 3. Execute with explicit public and secret inputs
    result = await client.execute_with_inputs(
        secret_inputs={
            "a": 25,        # Private: secret-shared across nodes
            "b": 17         # Private: secret-shared across nodes
        },
        public_inputs={
            "threshold": 50  # Public: visible to all nodes
        }
    )
    
    print(f"Secure computation result: {result}")
    await client.disconnect()

asyncio.run(main())
```

### Even Simpler Usage

```python
import asyncio
from stoffel import StoffelClient

async def main():
    # One-liner client setup
    client = StoffelClient({
        "nodes": ["http://mpc-node1:9000", "http://mpc-node2:9000", "http://mpc-node3:9000"],
        "client_id": "my_client",
        "program_id": "my_secure_program"
    })
    
    # One-liner execution with explicit input types
    result = await client.execute_with_inputs(
        secret_inputs={"user_data": 123, "private_value": 456},
        public_inputs={"config_param": 100}
    )
    
    print(f"Result: {result}")
    await client.disconnect()

asyncio.run(main())
```

## Examples

The `examples/` directory contains comprehensive examples:

### Simple API Demo (Recommended for Most Users)

```bash
poetry run python examples/simple_api_demo.py
```

Demonstrates the simplest possible usage:
- Clean, high-level API for basic MPC operations
- One-call execution patterns
- Status checking and client management

### Complete Architecture Example

```bash
poetry run python examples/correct_flow.py
```

Shows the complete workflow and proper separation of concerns:
- StoffelLang program compilation and VM setup
- MPC network client configuration and execution
- Local testing vs. MPC network execution
- Multiple network configuration options
- Architectural boundaries and responsibilities

### Advanced VM Operations

```bash
poetry run python examples/vm_example.py
```

For advanced users needing low-level VM control:
- Direct StoffelVM Python bindings usage
- Foreign function registration
- Value type handling and VM object management

## API Reference

### Main API (Recommended)

#### `StoffelProgram` - VM Operations

```python
class StoffelProgram:
    def __init__(self, source_file: Optional[str] = None)
    def compile(self, optimize: bool = True) -> str  # Returns compiled binary path
    def load_program(self) -> None
    def set_execution_params(self, params: Dict[str, Any]) -> None
    def execute_locally(self, inputs: Dict[str, Any]) -> Any  # For testing
    def get_computation_id(self) -> str
    def get_program_info(self) -> Dict[str, Any]
```

#### `StoffelClient` - Network Operations

```python
class StoffelClient:
    def __init__(self, network_config: Dict[str, Any])
    
    # Recommended API - explicit public/secret inputs
    async def execute_with_inputs(self, secret_inputs: Optional[Dict[str, Any]] = None,
                                  public_inputs: Optional[Dict[str, Any]] = None) -> Any
    
    # Individual input methods
    def set_secret_input(self, name: str, value: Any) -> None
    def set_public_input(self, name: str, value: Any) -> None
    def set_inputs(self, secret_inputs: Optional[Dict[str, Any]] = None, 
                   public_inputs: Optional[Dict[str, Any]] = None) -> None
    
    # Legacy API (for backward compatibility)
    async def execute_program_with_inputs(self, inputs: Dict[str, Any]) -> Any
    def set_private_data(self, name: str, value: Any) -> None
    def set_private_inputs(self, inputs: Dict[str, Any]) -> None
    async def execute_program(self) -> Any
    
    # Status and management
    def is_ready(self) -> bool
    def get_connection_status(self) -> Dict[str, Any]
    def get_program_info(self) -> Dict[str, Any]
    async def connect(self) -> None
    async def disconnect(self) -> None
```

#### Network Configuration

```python
# Direct connection to MPC nodes
client = StoffelClient({
    "nodes": ["http://mpc-node1:9000", "http://mpc-node2:9000", "http://mpc-node3:9000"],
    "client_id": "your_client_id",
    "program_id": "your_program_id"
})

# With optional coordinator for metadata exchange
client = StoffelClient({
    "nodes": ["http://mpc-node1:9000", "http://mpc-node2:9000", "http://mpc-node3:9000"],
    "coordinator_url": "http://coordinator:8080",  # Optional
    "client_id": "your_client_id", 
    "program_id": "your_program_id"
})

# Usage examples with new API
await client.execute_with_inputs(
    secret_inputs={"user_age": 25, "salary": 75000},    # Secret-shared
    public_inputs={"threshold": 50000, "rate": 0.1}     # Visible to all nodes
)
```

### Advanced API (For Specialized Use Cases)

#### `VirtualMachine` - Low-Level VM Bindings

```python
class VirtualMachine:
    def __init__(self, library_path: Optional[str] = None)
    def execute(self, function_name: str) -> Any
    def execute_with_args(self, function_name: str, args: List[Any]) -> Any
    def register_foreign_function(self, name: str, func: Callable) -> None
    def register_foreign_object(self, obj: Any) -> int
    def create_string(self, value: str) -> StoffelValue
```

#### `StoffelValue` - VM Value Types

```python
class StoffelValue:
    @classmethod
    def unit(cls) -> "StoffelValue"
    @classmethod 
    def integer(cls, value: int) -> "StoffelValue"
    @classmethod
    def float_value(cls, value: float) -> "StoffelValue"
    @classmethod
    def boolean(cls, value: bool) -> "StoffelValue"
    @classmethod
    def string(cls, value: str) -> "StoffelValue"
    
    def to_python(self) -> Any
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=stoffel

# Run specific test file
poetry run pytest tests/test_vm.py
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

**StoffelProgram** (`stoffel.program`):
- **Responsibility**: StoffelLang compilation, VM operations, execution parameters
- Handles program compilation from `.stfl` to `.stfb`
- Manages execution parameters and local testing
- Interfaces with StoffelVM for program lifecycle management

**StoffelClient** (`stoffel.client`):  
- **Responsibility**: MPC network communication, public/secret data handling, result reconstruction
- Connects directly to MPC nodes (addresses known via deployment)
- Handles secret sharing for secret inputs and distribution of public inputs
- Provides clean API with explicit public/secret input distinction
- Hides all cryptographic complexity while maintaining clear data visibility semantics

**Optional Coordinator Integration**:
- Used for metadata exchange between client and MPC network orchestration
- Not required for MPC node discovery (nodes specified directly)
- Skeleton implementation for future development

### Core Components

**StoffelVM Bindings** (`stoffel.vm`):
- Uses `ctypes` for FFI to StoffelVM's C API
- Enhanced with Share types for MPC integration
- Supports foreign function registration and VM lifecycle management

**MPC Types** (`stoffel.mpc`):
- Core MPC types and configurations for high-level interface
- Exception hierarchy for MPC-specific error handling
- Abstract types that hide protocol implementation details

### Design Principles

- **Simple Public API**: All internal complexity hidden behind intuitive methods
- **Generic Field Operations**: Not tied to specific cryptographic curves  
- **MPC-as-a-Service**: Client-side interface to MPC networks
- **Clean Architecture**: Clear boundaries between VM, Client, and Coordinator

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

🚧 **This project is under active development**

- ✅ Clean API design with proper separation of concerns
- ✅ StoffelProgram for compilation and VM operations (skeleton ready for StoffelLang integration)
- ✅ StoffelClient for network communication (skeleton ready for MPC network integration)  
- ✅ StoffelVM FFI bindings (ready for integration with libstoffel_vm.so)
- 🚧 MPC network integration (awaiting actual MPC service infrastructure)
- 🚧 StoffelLang compiler integration  
- 📋 Integration tests with actual shared libraries and MPC networks

## Related Projects

- [StoffelVM](https://github.com/stoffel-labs/StoffelVM) - The core virtual machine with MPC integration
- [MPC Protocols](https://github.com/stoffel-labs/mpc-protocols) - Rust implementation of MPC protocols
- [StoffelLang](https://github.com/stoffel-labs/stoffel-lang) - The programming language that compiles to StoffelVM

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/stoffel-labs/stoffel-python-sdk/issues)
- 💬 [Discussions](https://github.com/stoffel-labs/stoffel-python-sdk/discussions)