# Stoffel Python SDK Examples

This directory contains examples demonstrating how to use the Stoffel Python SDK.

## Examples Overview

### `simple_api_demo.py` - Quick Start
**Recommended for most users**
- Demonstrates the simplest possible usage
- Shows clean, high-level API for basic MPC operations
- One-call execution patterns
- Status checking and client management

### `correct_flow.py` - Complete Architecture
**Comprehensive example showing proper separation of concerns**
- Full workflow: StoffelLang compilation → MPC network execution
- Proper separation between VM (StoffelProgram) and Client (StoffelMPCClient)
- Multiple network configuration options
- Demonstrates both local testing and MPC network execution
- Shows architectural boundaries and responsibilities

### `vm_example.py` - Advanced VM Operations
**For advanced users needing low-level VM control**
- Direct StoffelVM Python bindings usage
- Foreign function registration
- Value type handling
- VM object management
- Lower-level API for specialized use cases

## Running Examples

Note: These examples use placeholder functionality for demonstration. 
For actual execution, you would need:
- Compiled StoffelLang programs (`.stfl` → `.stfb`)
- Running MPC network nodes
- Optional coordinator service (for metadata exchange)

```bash
# Run the simple demo
python examples/simple_api_demo.py

# Run the complete flow example  
python examples/correct_flow.py

# Run the VM example
python examples/vm_example.py
```

## Architecture Overview

The Stoffel framework has clear separation of concerns:

- **StoffelProgram** (VM): Compilation, execution parameters, local testing
- **StoffelMPCClient** (Network): MPC communication, private data, result reconstruction
- **Coordinator** (Optional): MPC orchestration and metadata exchange

Examples demonstrate this clean architecture with proper boundaries between components.