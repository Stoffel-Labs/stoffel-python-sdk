#!/usr/bin/env python3
"""
Complete MPC Workflow Example

This example demonstrates the complete Stoffel MPC workflow using the new API:
1. Compile a Stoffel program
2. Configure MPC parameters
3. Create MPC participants (clients, servers, nodes)
4. Set up network topology
5. Run secure computation
"""

import sys
import os

# Add the parent directory to the path so we can import stoffel
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from stoffel import (
    Stoffel,
    StoffelRuntime,
    Program,
    ProtocolType,
    ShareType,
    MPCClient,
    MPCServer,
    MPCNode,
    NetworkConfig,
    NetworkSettings,
    MPCSettings,
)
from stoffel.advanced import NetworkBuilder


async def client_server_workflow():
    """
    Client-Server MPC Architecture

    In this model:
    - Clients provide inputs (secret share them)
    - Servers perform the computation
    - Clients receive outputs
    """
    print("=== Client-Server MPC Workflow ===\n")

    # Step 1: Compile the program
    print("1. Compiling program...")

    # Using load() with fake bytecode for this demo
    # In production, use compile() or compile_file()
    runtime = (Stoffel.load(b"compiled_bytecode")
        .parties(5)
        .threshold(1)
        .instance_id(42)
        .build())

    print(f"   MPC config: n={runtime.mpc_config()[0]}, t={runtime.mpc_config()[1]}")

    # Step 2: Create clients
    print("\n2. Creating clients...")

    # Client 100: provides first input
    client_a = (runtime.client(100)
        .with_inputs([42])
        .build())
    print(f"   Client A (ID={client_a.client_id}): inputs={client_a.inputs}")

    # Client 101: provides second input
    client_b = (runtime.client(101)
        .with_inputs([17])
        .build())
    print(f"   Client B (ID={client_b.client_id}): inputs={client_b.inputs}")

    # Step 3: Create servers
    print("\n3. Creating servers...")

    servers = []
    for party_id in range(5):
        server = (runtime.server(party_id)
            .with_preprocessing(10, 25)  # 10 triples, 25 random shares
            .build())
        servers.append(server)
        print(f"   Server {party_id}: party_id={server.party_id}")

    # Step 4: Configure network
    print("\n4. Setting up network...")

    # Build a full mesh network on localhost
    topology = (NetworkBuilder(n_parties=5)
        .localhost(base_port=19200)
        .full_mesh()
        .build())

    print(f"   Network: {topology.n_parties} parties, mode={topology.mode.value}")

    # Configure each server with its peers
    for server in servers:
        peers = topology.get_peers_for(server.party_id)
        for peer_id, address in peers:
            server.add_peer(peer_id, address)
        print(f"   Server {server.party_id}: connected to {len(peers)} peers")

    # Step 5: Run computation (placeholder)
    print("\n5. Running computation...")
    print("   Note: Actual MPC execution requires PyO3 bindings")

    # In production, this would be:
    # for server in servers:
    #     await server.bind_and_listen(topology.get_node(server.party_id).bind_address)
    #     await server.connect_to_peers()
    #     await server.run_preprocessing()
    #
    # for client in [client_a, client_b]:
    #     shares = client.generate_input_shares()
    #     # Send shares to servers...
    #
    # results = await asyncio.gather(*[
    #     server.compute(bytecode) for server in servers
    # ])

    print("\n=== Client-Server Workflow Complete ===")


async def peer_to_peer_workflow():
    """
    Peer-to-Peer MPC Architecture

    In this model:
    - All parties provide inputs AND compute
    - Uses MPCNode which combines client and server functionality
    """
    print("\n=== Peer-to-Peer MPC Workflow ===\n")

    # Step 1: Set up runtime
    print("1. Setting up runtime...")

    runtime = (Stoffel.load(b"compiled_bytecode")
        .parties(4)
        .threshold(1)
        .build())

    print(f"   MPC config: n={runtime.mpc_config()[0]}, t={runtime.mpc_config()[1]}")

    # Step 2: Create nodes (each party has both inputs and compute)
    print("\n2. Creating nodes...")

    nodes = []
    inputs_per_party = [[10, 20], [30, 40], [50, 60], [70, 80]]

    for party_id in range(4):
        node = (runtime.node(party_id)
            .with_inputs(inputs_per_party[party_id])
            .with_preprocessing(5, 12)
            .build())
        nodes.append(node)
        print(f"   Node {party_id}: inputs={node.inputs}")

    # Step 3: Configure network
    print("\n3. Setting up network...")

    topology = (NetworkBuilder(n_parties=4)
        .localhost(base_port=19300)
        .full_mesh()
        .build())

    print(f"   Network: {topology.n_parties} parties, full mesh")

    # Step 4: Run computation (placeholder)
    print("\n4. Running computation...")
    print("   Note: Actual MPC execution requires PyO3 bindings")

    # In production:
    # for node in nodes:
    #     node.network_mut().listen(topology.get_node(node.party_id).bind_address)
    #     for peer_id, addr in topology.get_peers_for(node.party_id):
    #         node.network_mut().add_node_with_party_id(peer_id, addr)
    #
    # results = await asyncio.gather(*[
    #     node.run(bytecode) for node in nodes
    # ])

    print("\n=== Peer-to-Peer Workflow Complete ===")


def config_file_workflow():
    """
    Using TOML Configuration Files

    For production deployments, use config files to specify network topology.
    """
    print("\n=== TOML Config File Workflow ===\n")

    # Create a config programmatically (normally loaded from file)
    config = NetworkConfig(
        network=NetworkSettings(
            party_id=0,
            bind_address="127.0.0.1:19200",
            bootstrap_address="127.0.0.1:19200",
            min_parties=5,
        ),
        mpc=MPCSettings(
            n_parties=5,
            threshold=1,
            instance_id=100,
        ),
    )

    print("1. Config loaded:")
    print(f"   party_id: {config.network.party_id}")
    print(f"   bind_address: {config.network.bind_address}")
    print(f"   n_parties: {config.mpc.n_parties}")
    print(f"   threshold: {config.mpc.threshold}")

    # Validate the config
    config.validate()
    print("\n2. Config validated successfully")

    # Use with Stoffel builder
    # In production:
    # runtime = (Stoffel.compile_file("program.stfl")
    #     .network_config_file("stoffel.toml")
    #     .build())

    print("\n=== Config File Workflow Complete ===")


def demonstrate_architecture():
    """
    Explain the overall architecture
    """
    print("\n=== Stoffel SDK Architecture ===\n")

    print("Entry Point: Stoffel")
    print("├── compile(source) / compile_file(path) / load(bytecode)")
    print("├── Builder methods: parties(), threshold(), protocol(), etc.")
    print("└── build() -> StoffelRuntime")

    print("\nStoffelRuntime:")
    print("├── program() -> Program (compiled bytecode)")
    print("├── client(id) -> MPCClientBuilder -> MPCClient")
    print("├── server(id) -> MPCServerBuilder -> MPCServer")
    print("└── node(id) -> MPCNodeBuilder -> MPCNode")

    print("\nMPC Participants:")
    print("├── MPCClient: Input provider")
    print("│   ├── with_inputs([...]) - Set secret inputs")
    print("│   ├── generate_input_shares() - Create secret shares")
    print("│   └── receive_outputs() - Get computation result")
    print("├── MPCServer: Compute node")
    print("│   ├── with_preprocessing(triples, randoms)")
    print("│   ├── run_preprocessing() - Generate crypto material")
    print("│   ├── receive_client_inputs() - Get shares from clients")
    print("│   └── compute() - Execute secure computation")
    print("└── MPCNode: Combined (peer-to-peer)")
    print("    ├── with_inputs([...]) - Set own secret inputs")
    print("    ├── with_preprocessing(triples, randoms)")
    print("    └── run() - Full MPC protocol")

    print("\nAdvanced Components (stoffel.advanced):")
    print("├── ShareManager: Low-level secret sharing")
    print("│   ├── create_shares(secret) - Manual share creation")
    print("│   ├── reconstruct(shares) - Manual reconstruction")
    print("│   └── add_shares(), multiply_by_constant()")
    print("└── NetworkBuilder: Custom network topology")
    print("    ├── add_node(party_id, address)")
    print("    ├── full_mesh() / star(hub)")
    print("    └── localhost() - Quick local setup")


if __name__ == "__main__":
    asyncio.run(client_server_workflow())
    asyncio.run(peer_to_peer_workflow())
    config_file_workflow()
    demonstrate_architecture()
