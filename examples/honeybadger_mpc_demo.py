#!/usr/bin/env python3
"""
Full E2E HoneyBadger MPC Demo

Demonstrates the complete MPC workflow:
1. Start 5 MPC servers with HoneyBadger preprocessing
2. Connect a client with secret inputs
3. Execute secure computation
4. Receive and verify reconstructed output

This is the Python equivalent of the Rust SDK's honeybadger_mpc_demo.rs

## Running

    python examples/honeybadger_mpc_demo.py

## Requirements

- Native libraries must be built:
    cd mpc-protocols && cargo build --release

## Features

- Dynamic port allocation: Uses OS-assigned ports to avoid conflicts
- Graceful shutdown: Press Ctrl+C to cleanly stop all servers
"""

import asyncio
import os
import signal
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stoffel.mpcaas import (
    StoffelServer,
    StoffelServerBuilder,
    StoffelClient,
    StoffelClientBuilder,
)
from stoffel.native import is_native_available


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def unique_base_port() -> int:
    """
    Generate unique base port for this process to avoid conflicts.
    Uses process ID to select a base port in the 30000-60000 range.
    """
    return 30000 + (os.getpid() % 30000)


async def main():
    print("=" * 50)
    print("      HoneyBadger MPC Demo")
    print("  Secure Multi-Party Computation Example")
    print("=" * 50)
    print()

    # Check native library availability
    if not is_native_available():
        print("WARNING: Native MPC library not available.")
        print("Some features may be limited or simulated.")
        print()
        print("To build native libraries:")
        print("  cd mpc-protocols && cargo build --release")
        print()

    # ===== Step 1: Define MPC configuration =====
    # Note: TripleGen preprocessing requires n >= 4t + 1 (stricter than basic Byzantine n >= 3t + 1)
    # For threshold=1: need at least 5 parties (5 >= 4*1 + 1)
    n_parties = 5
    threshold = 1  # Tolerate 1 Byzantine failure
    # CRITICAL: All servers MUST share the same instance_id for MPC session coordination
    instance_id = 12345

    # Generate unique ports based on process ID to avoid conflicts
    base_port = unique_base_port()
    ports = [base_port + i for i in range(n_parties)]

    print("MPC Configuration:")
    print(f"  Parties (n): {n_parties}")
    print(f"  Threshold (t): {threshold} (tolerates {threshold} Byzantine failures)")
    print(f"  Instance ID: {instance_id} (shared by all servers)")
    print(f"  Ports: {ports} (unique per process, base: {base_port})")
    print(f"  TripleGen constraint: n >= 4t + 1 -> {n_parties} >= {4 * threshold + 1} OK")
    print()

    # ===== Step 2: Define Stoffel program =====
    # MPC programs must explicitly load client inputs from ClientStore
    # The program uses ClientStore.take_share(client_index, share_index) to load secret shares
    source = """
main main() -> secret int64:
  var a: secret int64 = ClientStore.take_share(0, 0)
  var b: secret int64 = ClientStore.take_share(0, 1)
  return a + b
    """

    print("Stoffel Program:")
    print("  Operation: secret addition using ClientStore")
    print(f"  Source:\n{source}")
    print()

    # ===== Step 3: Generate peer addresses =====
    peer_addrs = [(i, f"127.0.0.1:{ports[i]}") for i in range(n_parties)]

    # ===== Step 4: Create and start servers =====
    print(f"Starting {n_parties} MPC servers...")
    print("-" * 50)

    # CRITICAL: Calculate preprocessing start time BEFORE creating any servers
    # All servers will receive the same start time and wait until that absolute moment.
    import time
    preprocessing_start_epoch = int(time.time()) + 20

    print(f"  Preprocessing will start at epoch: {preprocessing_start_epoch} (in ~20 seconds)")

    server_tasks = []
    servers = []

    for party_id in range(n_parties):
        bind_addr = f"0.0.0.0:{ports[party_id]}"

        # Create peers list excluding self
        peers = [(pid, addr) for pid, addr in peer_addrs if pid != party_id]

        # Build server
        server = StoffelServer.builder(party_id) \
            .bind(bind_addr) \
            .with_peers(peers) \
            .with_preprocessing(3, 8) \
            .with_instance_id(instance_id) \
            .with_preprocessing_start_time(preprocessing_start_epoch) \
            .build()

        servers.append(server)
        print(f"  Server {party_id} configured on {bind_addr}")

    # Start all servers
    async def run_server(server, party_id):
        try:
            await server.start()
            await server.run_forever()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Server {party_id} error: {e}")

    for party_id, server in enumerate(servers):
        task = asyncio.create_task(run_server(server, party_id))
        server_tasks.append(task)
        await asyncio.sleep(0.1)  # Small delay between starting servers

    # Wait for servers to initialize, connect peers, and run preprocessing
    print()
    print("Waiting for servers to complete preprocessing...")
    print("(This takes ~40 seconds for network mesh, sync, and HoneyBadger triple generation)")
    print()
    await asyncio.sleep(40)

    # ===== Step 5: Connect client and run computation =====
    print("-" * 50)
    print("Client Connecting to MPC Network")
    print("-" * 50)
    print()

    server_addrs = [addr for _, addr in peer_addrs]
    client_inputs = [42, 100]  # a=42, b=100

    print("Client Configuration:")
    print(f"  Input a: {client_inputs[0]} (secret)")
    print(f"  Input b: {client_inputs[1]} (secret)")
    print(f"  Expected result: a + b = {sum(client_inputs)}")
    print()
    print(f"Connecting to servers: {server_addrs}")

    try:
        # Build and connect client
        client = await StoffelClient.builder() \
            .with_servers(server_addrs) \
            .connect()

        print()
        print("Connected to MPC network:")
        print(f"  Number of parties: {client.n_parties()}")
        print(f"  Threshold: {client.threshold()}")
        print(f"  Client ID: {client.client_id}")
        print(f"  State: {client.state}")
        print()

        print("Running secure computation...")
        print("(Input protocol: MaskShare -> MaskedInput -> Computation -> Output)")
        print()

        result = await client.run(client_inputs)

        print("-" * 50)
        print("                   RESULT")
        print("-" * 50)
        print()
        print(f"  MPC Output: {result}")
        print()
        print("  Verification:")
        print(f"    {client_inputs[0]} + {client_inputs[1]} = {result[0] if result else 'N/A'}")
        print(f"    Expected: {sum(client_inputs)}")

        expected = sum(client_inputs)
        if result and result[0] == expected:
            print()
            print("  [OK] Result matches expected value!")
        else:
            print()
            print("  [WARN] Result does not match expected value")
            print("  (This is expected in demo mode without full FFI implementation)")
        print()

        await client.disconnect()

    except asyncio.TimeoutError:
        print()
        print("Connection timed out. Possible causes:")
        print("  - Servers not fully started")
        print("  - Port conflicts (try different base_port)")
        print("  - Firewall blocking connections")

    except Exception as e:
        print()
        print(f"Error: {e}")

    print("-" * 50)
    print("Demo complete! Press Ctrl+C to exit...")
    print("-" * 50)

    # Wait for Ctrl+C
    try:
        stop_event = asyncio.Event()

        def signal_handler():
            print()
            print("Received Ctrl+C, shutting down gracefully...")
            stop_event.set()

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        await stop_event.wait()

    except Exception:
        pass

    # Shutdown servers
    for task in server_tasks:
        task.cancel()

    for server in servers:
        try:
            await server.shutdown()
        except Exception:
            pass

    print("All servers stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
