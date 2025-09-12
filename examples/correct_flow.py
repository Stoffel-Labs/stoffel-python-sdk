#!/usr/bin/env python3
"""
Correct Stoffel Framework Usage Flow

This example demonstrates the proper separation of concerns:
- StoffelProgram: Handles compilation, VM setup, and execution parameters
- StoffelMPCClient: Handles network communication and private data management

Flow:
1. Write StoffelLang program
2. Compile and setup program (VM responsibility)  
3. Define execution parameters (VM responsibility)
4. Initialize MPC client for network communication
5. Set private data in client
6. Execute computation through MPC network
7. Receive and reconstruct results
"""

import asyncio
import tempfile
import os
from stoffel.program import StoffelProgram
from stoffel.client import StoffelMPCClient


async def main():
    print("=== Correct Stoffel Framework Usage Flow ===\n")
    
    # Step 1: Write StoffelLang program
    # (Note: Using placeholder syntax - actual syntax needs verification)
    program_source = """
    // Simple secure addition program
    // TODO: Verify actual StoffelLang syntax from compiler source
    main(input1, input2) {
        return input1 + input2;
    }
    """
    
    print("1. StoffelLang Program:")
    print(program_source)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.stfl', delete=False) as f:
        f.write(program_source)
        source_file = f.name
    
    try:
        print("2. Program Management (VM Responsibility):")
        
        # Step 2 & 3: Compile and setup program (VM handles this)
        program = StoffelProgram(source_file)
        
        # Compile the program
        binary_path = program.compile(optimize=True)
        print(f"   Compiled: {source_file} -> {binary_path}")
        
        # Load program into VM
        program.load_program()
        print("   Program loaded into VM")
        
        # Define execution parameters (VM responsibility)
        program.set_execution_params({
            "computation_id": "secure_addition_demo",
            "function_name": "main",
            "expected_inputs": ["input1", "input2"],
            "input_mapping": {
                "param_a": "input1",
                "param_b": "input2"  
            },
            "mpc_protocol": "honeybadger",
            "threshold": 2,
            "num_parties": 3
        })
        print("   Execution parameters configured")
        
        # Test local execution (for debugging)
        local_result = program.execute_locally({"input1": 25, "input2": 17})
        print(f"   Local test execution: 25 + 17 = {local_result}")
        
        print("\n3. MPC Client (Network Communication Responsibility):")
        
        # Step 4: Initialize MPC client - knows the specific program running on MPC network
        program_id = program.get_computation_id()
        
        # Option 1: Direct connection to known MPC nodes
        network_config_direct = {
            "nodes": ["http://mpc-node1:9000", "http://mpc-node2:9000", "http://mpc-node3:9000"],
            "client_id": "client_001",
            "program_id": program_id  # MPC network is pre-configured to run this program
        }
        
        # Option 2: Direct connection with coordinator for metadata exchange
        network_config_with_coordinator = {
            "nodes": ["http://mpc-node1:9000", "http://mpc-node2:9000", "http://mpc-node3:9000"],
            "coordinator_url": "http://coordinator:8080",  # Optional: for metadata exchange only
            "client_id": "client_001",
            "program_id": program_id
        }
        
        # Use direct connection for this example
        client = StoffelMPCClient(network_config_direct)
        print(f"   MPC client initialized for program: {program_id}")
        print(f"   Connection type: direct to MPC nodes")
        print(f"   Note: Coordinator (if used) is for metadata exchange, not node discovery")
        
        # Step 5: Set private data in client
        client.set_private_data("input1", 25)
        client.set_private_data("input2", 17)
        print("   Private data set: input1=25, input2=17")
        
        print("\n4. MPC Network Execution:")
        
        # Step 6 & 7: Execute the pre-configured program (all complexity hidden)
        print(f"   Executing program '{program_id}' on MPC network...")
        
        result = await client.execute_program()
        print(f"   Final result: 25 + 17 = {result}")
        
        # Disconnect from network
        await client.disconnect()
        print("   Disconnected from MPC network")
        
        print("\n5. Program Information:")
        program_info = program.get_program_info()
        for key, value in program_info.items():
            print(f"   {key}: {value}")
        
        print("\n6. Client Status (Clean API):")
        if client.is_ready():
            print("   ✓ Client is ready for computation")
        
        status = client.get_connection_status()
        print(f"   Client ID: {status['client_id']}")
        print(f"   Program: {status['program_id']}")
        print(f"   MPC Nodes: {status['mpc_nodes_count']}")
        print(f"   Connected: {status['connected']}")
        print(f"   Coordinator: {status['coordinator_url'] or 'Not configured'}")
        
        program_info = client.get_program_info()
        print(f"   Inputs provided: {program_info['expected_inputs']}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: This example uses placeholder functionality")
        print("Real implementation would connect to actual MPC network")
        
    finally:
        # Clean up
        if os.path.exists(source_file):
            os.unlink(source_file)
        binary_file = source_file.replace('.stfl', '.stfb')
        if os.path.exists(binary_file):
            os.unlink(binary_file)
    
    print("\n=== Correct Flow Demonstrated ===")


async def demonstrate_separation_of_concerns():
    """
    Additional example showing clear separation between VM and Client responsibilities
    """
    print("\n=== Separation of Concerns ===")
    
    print("\nVM/Program Responsibilities:")
    print("- Compile StoffelLang source code")
    print("- Load programs into VM")  
    print("- Define execution parameters")
    print("- Handle local program execution")
    print("- Manage program lifecycle")
    
    print("\nMPC Client Responsibilities:")
    print("- Connect to MPC network nodes (with or without coordinator)")
    print("- Manage private data and secret sharing")
    print("- Send shares to each MPC node")
    print("- Collect result shares from each MPC node")
    print("- Reconstruct final results from collected shares")
    print("- Handle network communication")
    
    print("\nCoordinator vs MPC Network (when coordinator is used):")
    print("- Coordinator: Primarily for MPC network orchestration")
    print("- MPC Network: Actual secure computation on shares")
    print("- Client connects to coordinator for metadata exchange only (when needed)")
    print("- Client connects directly to known MPC nodes for computation")
    print("- Coordinator and MPC network are separate components")
    
    print("\nClear Boundaries:")
    print("- VM knows about programs, compilation, execution parameters")
    print("- Client knows about MPC networking, secret sharing, result reconstruction") 
    print("- Coordinator (if used) knows about MPC orchestration and metadata")
    print("- MPC Network knows about secure computation on shares")
    print("- No overlap in responsibilities")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(demonstrate_separation_of_concerns())