#!/usr/bin/env python3
"""
Simple API Demo - Minimal Example

Demonstrates the simplest possible usage of the Stoffel Python SDK.
Shows the clean, high-level API for basic MPC operations.
"""

import sys
import os

# Add the parent directory to the path so we can import stoffel
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from stoffel import Stoffel, ProtocolType, ShareType


async def main():
    print("=== Simple Stoffel API Demo ===\n")

    # 1. Load bytecode and set up MPC configuration
    print("1. Setting up program with MPC configuration...")

    # Load pre-compiled bytecode and configure MPC
    # In production, you would use Stoffel.compile() or Stoffel.compile_file()
    # but that requires the Stoffel compiler to be installed
    runtime = (Stoffel.load(b"example_bytecode")
        .parties(5)
        .threshold(1)
        .build())

    print("   Program compiled and MPC configured")
    print(f"   MPC config: {runtime.mpc_config()}")

    # 2. Create MPC participants
    print("\n2. Creating MPC participants...")

    # Create a client (input provider)
    client = (runtime.client(100)
        .with_inputs([42, 17])
        .build())

    print(f"   Client created with ID: {client.client_id}")
    print(f"   Inputs: {client.inputs}")

    # Create servers (compute nodes)
    servers = []
    for party_id in range(5):
        server = runtime.server(party_id).build()
        servers.append(server)
        print(f"   Server {party_id} created")

    # 3. Show configuration
    print("\n3. Configuration details...")
    print(f"   Client config: {client.config()}")
    print(f"   Server 0 config: {servers[0].config()}")

    print("\n=== Demo Complete ===")
    print("\nNote: Actual MPC execution requires PyO3 bindings (coming soon)")


async def quick_local_test():
    """
    Quick local execution for testing (no MPC)
    """
    print("\n=== Quick Local Test ===")

    # For testing, you can skip MPC config and execute locally
    # Note: This requires PyO3 bindings which are not yet available
    try:
        result = Stoffel.load(b"example_bytecode").execute_local()
        print(f"Local result: {result}")
    except NotImplementedError as e:
        print(f"Note: {e}")


def show_api_design():
    """
    Show the clean API design principles
    """
    print("\n=== Clean API Design ===")

    print("\nStoffel Entry Point:")
    print("  Stoffel.compile(source)     - Compile from string")
    print("  Stoffel.compile_file(path)  - Compile from file")
    print("  Stoffel.load(bytecode)      - Load pre-compiled bytecode")

    print("\nBuilder Pattern Methods:")
    print("  .parties(n)                 - Set number of MPC parties")
    print("  .threshold(t)               - Set fault tolerance (n >= 3t+1)")
    print("  .instance_id(id)            - Set computation instance ID")
    print("  .protocol(ProtocolType)     - Set MPC protocol")
    print("  .share_type(ShareType)      - Set secret sharing scheme")
    print("  .build()                    - Build StoffelRuntime")
    print("  .execute_local()            - Quick local execution")

    print("\nStoffelRuntime Methods:")
    print("  .program()                  - Get the compiled Program")
    print("  .client(id)                 - Create MPCClientBuilder")
    print("  .server(party_id)           - Create MPCServerBuilder")
    print("  .node(party_id)             - Create MPCNodeBuilder")

    print("\nMPC Participants:")
    print("  MPCClient   - Input provider (sends shares, receives results)")
    print("  MPCServer   - Compute node (performs secure computation)")
    print("  MPCNode     - Combined client + server (peer-to-peer MPC)")

    print("\nKey Design Principles:")
    print("  ✓ Builder pattern for fluent configuration")
    print("  ✓ All complexity hidden behind intuitive methods")
    print("  ✓ HoneyBadger protocol by default (Byzantine fault tolerant)")
    print("  ✓ Clean separation: Program vs Runtime vs Participants")


def show_error_types():
    """
    Show available error types
    """
    from stoffel import (
        StoffelError,
        MPCError,
        ComputationError,
        NetworkError,
        ConfigurationError,
        ProtocolError,
        PreprocessingError,
        IoError,
        InvalidInputError,
        FunctionNotFoundError,
    )

    print("\n=== Exception Hierarchy ===")
    print("\nStoffelError (base)")
    print("├── MPCError (MPC-specific errors)")
    print("│   ├── ComputationError")
    print("│   ├── NetworkError")
    print("│   ├── ConfigurationError")
    print("│   ├── ProtocolError")
    print("│   └── PreprocessingError")
    print("├── IoError")
    print("├── InvalidInputError")
    print("└── FunctionNotFoundError")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(quick_local_test())
    show_api_design()
    show_error_types()
