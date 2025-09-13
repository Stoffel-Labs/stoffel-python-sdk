#!/usr/bin/env python3
"""
Simple API Demo - Minimal Example

Demonstrates the simplest possible usage of the Stoffel Python SDK.
Shows the clean, high-level API for basic MPC operations.
"""

import asyncio
from stoffel import StoffelProgram, StoffelMPCClient


async def main():
    print("=== Simple Stoffel API Demo ===\n")
    
    # 1. Program setup (handled by VM/StoffelProgram)
    print("1. Setting up program...")
    program = StoffelProgram()  # Placeholder - would use real .stfl file
    print("   ✓ Program compiled and loaded")
    
    # 2. Clean MPC client initialization
    print("\n2. Initializing MPC client...")
    client = StoffelMPCClient({
        "nodes": ["http://mpc-node1:9000", "http://mpc-node2:9000", "http://mpc-node3:9000"],
        "client_id": "demo_client",
        "program_id": "secure_addition_demo"
    })
    print("   ✓ Client initialized")
    
    # 3. Simple execution - all complexity hidden
    print("\n3. Executing secure computation...")
    
    # Option A: Set inputs then execute
    client.set_private_data("a", 42)
    client.set_private_data("b", 17)
    result = await client.execute_program()
    
    print(f"   Result: {result}")
    
    # Option B: Execute with inputs in one call (even cleaner)
    print("\n4. One-call execution...")
    result2 = await client.execute_program_with_inputs({
        "x": 100,
        "y": 25
    })
    print(f"   Result: {result2}")
    
    # 5. Status information (without exposing internals)
    print("\n5. Status information...")
    
    if client.is_ready():
        print("   ✓ Client is ready")
    else:
        print("   ⚠ Client not ready")
    
    status = client.get_connection_status()
    print(f"   Connected: {status['connected']}")
    print(f"   Program: {status['program_id']}")
    print(f"   MPC nodes: {status['mpc_nodes_count']}")
    print(f"   Coordinator: {status['coordinator_url'] or 'Not configured'}")
    
    program_info = client.get_program_info()
    print(f"   Available inputs: {program_info['expected_inputs']}")
    
    # 6. Clean disconnection
    await client.disconnect()
    print("\n   ✓ Disconnected cleanly")
    
    print("\n=== Demo Complete ===")


async def even_simpler_example():
    """
    Ultra-simple example for basic use cases
    """
    print("\n=== Ultra-Simple Example ===")
    
    # One-liner client setup
    client = StoffelMPCClient({
        "nodes": ["http://mpc-node1:9000", "http://mpc-node2:9000", "http://mpc-node3:9000"],
        "client_id": "simple_client", 
        "program_id": "my_secure_program"
    })
    
    # One-liner execution
    result = await client.execute_program_with_inputs({
        "secret_input": 123,
        "another_input": 456
    })
    
    print(f"Secure computation result: {result}")
    
    # Clean up
    await client.disconnect()


def show_api_design():
    """
    Show the clean API design principles
    """
    print("\n=== Clean API Design ===")
    
    print("\nDeveloper-Facing Methods (Public API):")
    print("✓ StoffelMPCClient(config)           - Simple initialization")
    print("✓ set_private_data(name, value)      - Set individual input")
    print("✓ set_private_inputs(inputs)         - Set multiple inputs")  
    print("✓ execute_program()                  - Execute with set inputs")
    print("✓ execute_program_with_inputs(...)   - One-call execution")
    print("✓ is_ready()                         - Simple status check")
    print("✓ get_connection_status()            - High-level status")
    print("✓ get_program_info()                 - Program information")
    print("✓ disconnect()                       - Clean shutdown")
    
    print("\nHidden Implementation (Private Methods):")
    print("- _discover_mpc_nodes_from_coordinator()")
    print("- _register_with_coordinator()")
    print("- _connect_to_mpc_nodes()")
    print("- _create_secret_shares()")
    print("- _send_shares_to_nodes()")
    print("- _collect_result_shares_from_nodes()")
    print("- _reconstruct_final_result()")
    
    print("\nBenefits:")
    print("✓ Simple, intuitive API")
    print("✓ All complexity hidden")
    print("✓ Easy to use correctly")
    print("✓ Hard to use incorrectly")
    print("✓ Clean separation of concerns")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(even_simpler_example())
    show_api_design()