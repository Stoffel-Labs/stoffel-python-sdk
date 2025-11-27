"""
Network Setup Helpers

High-level functions for setting up MPC networks quickly.
These helpers simplify common network configurations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..mpc.client import MPCClient
    from ..mpc.server import MPCServer
    from ..stoffel import StoffelRuntime

logger = logging.getLogger(__name__)


async def setup_honeybadger_network(
    runtime: "StoffelRuntime",
    server_addresses: Dict[int, str],
    bind_addresses: Optional[Dict[int, str]] = None,
) -> List["MPCServer"]:
    """
    Set up a HoneyBadger MPC network with multiple servers

    This is a convenience function that creates and starts all servers
    for a HoneyBadger network. Each server is configured with connections
    to all other servers.

    Args:
        runtime: Configured StoffelRuntime with parties/threshold set
        server_addresses: Dict mapping party_id -> address (host:port)
        bind_addresses: Optional separate bind addresses (defaults to server_addresses)

    Returns:
        List of started MPCServer instances

    Example::

        runtime = Stoffel.compile("...").parties(4).threshold(1).build()

        # Define server addresses
        addresses = {
            0: "127.0.0.1:19200",
            1: "127.0.0.1:19201",
            2: "127.0.0.1:19202",
            3: "127.0.0.1:19203",
        }

        # Start all servers
        servers = await setup_honeybadger_network(runtime, addresses)

        # Servers are now running and connected to each other
    """
    if bind_addresses is None:
        bind_addresses = server_addresses

    servers: List["MPCServer"] = []

    # Create all servers and add peer info
    for party_id in sorted(server_addresses.keys()):
        server = runtime.server(party_id).build()

        # Add all other servers as peers
        for peer_id, peer_addr in server_addresses.items():
            if peer_id != party_id:
                server.add_peer(peer_id, peer_addr)

        servers.append(server)

    # Phase 1: Start all listeners first (in parallel)
    async def start_listener(server: "MPCServer", addr: str):
        server._bind_address = addr
        server._running = True
        server._initialized = True
        manager = server._get_network_manager()
        await manager.start_server(addr)
        logger.info(f"Server {server.party_id} listening on {addr}")

    await asyncio.gather(*[
        start_listener(server, bind_addresses[server.party_id])
        for server in servers
    ])

    # Give all listeners time to bind
    await asyncio.sleep(0.2)

    # Phase 2: Connect peers (each server connects to higher-ID peers)
    async def connect_to_higher_peers(server: "MPCServer"):
        peers_to_connect = {
            pid: addr for pid, addr in server._peers.items()
            if pid > server.party_id
        }
        if peers_to_connect:
            manager = server._get_network_manager()
            try:
                await manager.connect_to_peers(peers_to_connect)
                logger.info(f"Server {server.party_id} connected to peers {list(peers_to_connect.keys())}")
            except ConnectionError as e:
                logger.warning(f"Server {server.party_id} peer connection: {e}")

    await asyncio.gather(*[
        connect_to_higher_peers(server)
        for server in servers
    ])

    logger.info(f"HoneyBadger network started with {len(servers)} servers")
    return servers


async def setup_client_with_servers(
    runtime: "StoffelRuntime",
    client_id: int,
    inputs: List[int],
    server_addresses: Dict[int, str],
) -> "MPCClient":
    """
    Create and connect an MPC client to all servers

    Args:
        runtime: Configured StoffelRuntime
        client_id: Unique client identifier
        inputs: List of integer inputs to contribute
        server_addresses: Dict mapping server_id -> address

    Returns:
        Connected MPCClient instance

    Example::

        runtime = Stoffel.compile("...").parties(4).threshold(1).build()

        client = await setup_client_with_servers(
            runtime,
            client_id=100,
            inputs=[42, 17],
            server_addresses={
                0: "127.0.0.1:19200",
                1: "127.0.0.1:19201",
                2: "127.0.0.1:19202",
                3: "127.0.0.1:19203",
            },
        )

        # Client is now connected and ready to send inputs
        await client.send_inputs()
    """
    client = runtime.client(client_id).with_inputs(inputs).build()

    # Add all servers
    for server_id, address in server_addresses.items():
        client.add_server(server_id, address)

    # Connect to all servers
    await client.connect_to_servers()

    logger.info(
        f"Client {client_id} connected to {len(server_addresses)} servers "
        f"with {len(inputs)} inputs"
    )
    return client


async def run_mpc_computation(
    runtime: "StoffelRuntime",
    server_addresses: Dict[int, str],
    client_inputs: Dict[int, List[int]],
    bytecode: Optional[bytes] = None,
    timeout: float = 60.0,
) -> Dict[int, List[int]]:
    """
    Run a complete MPC computation end-to-end

    This high-level function:
    1. Starts all MPC servers
    2. Connects all clients
    3. Sends inputs from all clients
    4. Runs computation on servers
    5. Returns reconstructed outputs to each client

    Args:
        runtime: Configured StoffelRuntime with program compiled
        server_addresses: Dict mapping party_id -> address
        client_inputs: Dict mapping client_id -> list of inputs
        bytecode: Optional bytecode (uses runtime's bytecode if None)
        timeout: Timeout for operations

    Returns:
        Dict mapping client_id -> list of reconstructed outputs

    Example::

        runtime = Stoffel.compile("fn main(a, b) -> a + b").parties(4).threshold(1).build()

        results = await run_mpc_computation(
            runtime,
            server_addresses={
                0: "127.0.0.1:19200",
                1: "127.0.0.1:19201",
                2: "127.0.0.1:19202",
                3: "127.0.0.1:19203",
            },
            client_inputs={
                100: [42, 17],  # Client 100 provides a=42, b=17
            },
        )

        print(results[100])  # [59] (42 + 17)
    """
    servers: List["MPCServer"] = []
    clients: List["MPCClient"] = []

    try:
        # Start servers
        servers = await setup_honeybadger_network(runtime, server_addresses)

        # Run preprocessing on all servers
        await asyncio.gather(*[
            server.run_preprocessing()
            for server in servers
        ])

        # Create and connect clients
        for client_id, inputs in client_inputs.items():
            client = await setup_client_with_servers(
                runtime,
                client_id=client_id,
                inputs=inputs,
                server_addresses=server_addresses,
            )
            clients.append(client)

        # Send inputs from all clients
        await asyncio.gather(*[
            client.send_inputs()
            for client in clients
        ])

        # Compute on all servers
        expected_clients = list(client_inputs.keys())
        inputs_per_client = max(len(inputs) for inputs in client_inputs.values())

        await asyncio.gather(*[
            server.run_computation(
                expected_clients=expected_clients,
                inputs_per_client=inputs_per_client,
                timeout=timeout,
            )
            for server in servers
        ])

        # Receive outputs at each client
        results: Dict[int, List[int]] = {}
        for client in clients:
            outputs = await client.receive_outputs(
                output_count=1,  # Configurable based on program
                timeout=timeout,
            )
            results[client.client_id] = outputs

        return results

    finally:
        # Cleanup
        for client in clients:
            await client.disconnect()
        for server in servers:
            await server.stop()


def generate_local_addresses(
    n_parties: int,
    base_port: int = 19200,
    host: str = "127.0.0.1",
) -> Dict[int, str]:
    """
    Generate local addresses for testing

    Args:
        n_parties: Number of parties
        base_port: Starting port number
        host: Host address (default localhost)

    Returns:
        Dict mapping party_id -> address

    Example::

        addresses = generate_local_addresses(4)
        # {0: "127.0.0.1:19200", 1: "127.0.0.1:19201", ...}
    """
    return {
        party_id: f"{host}:{base_port + party_id}"
        for party_id in range(n_parties)
    }


class MPCNetwork:
    """
    Context manager for MPC network lifecycle

    Manages the startup and shutdown of an MPC network automatically.

    Example::

        runtime = Stoffel.compile("...").parties(4).threshold(1).build()
        addresses = generate_local_addresses(4)

        async with MPCNetwork(runtime, addresses) as network:
            # Network is running
            client = await network.create_client(100, [42, 17])
            await client.send_inputs()
            result = await client.receive_outputs()
    """

    def __init__(
        self,
        runtime: "StoffelRuntime",
        server_addresses: Dict[int, str],
    ):
        self._runtime = runtime
        self._server_addresses = server_addresses
        self._servers: List["MPCServer"] = []
        self._clients: List["MPCClient"] = []

    @property
    def servers(self) -> List["MPCServer"]:
        """Get list of running servers"""
        return self._servers

    @property
    def server_addresses(self) -> Dict[int, str]:
        """Get server addresses"""
        return self._server_addresses

    async def start(self) -> None:
        """Start the network"""
        self._servers = await setup_honeybadger_network(
            self._runtime,
            self._server_addresses,
        )

        # Run preprocessing
        await asyncio.gather(*[
            server.run_preprocessing()
            for server in self._servers
        ])

    async def create_client(
        self,
        client_id: int,
        inputs: List[int],
    ) -> "MPCClient":
        """
        Create and connect a client to this network

        Args:
            client_id: Unique client identifier
            inputs: List of inputs

        Returns:
            Connected MPCClient
        """
        client = await setup_client_with_servers(
            self._runtime,
            client_id=client_id,
            inputs=inputs,
            server_addresses=self._server_addresses,
        )
        self._clients.append(client)
        return client

    async def stop(self) -> None:
        """Stop the network and cleanup"""
        for client in self._clients:
            await client.disconnect()
        for server in self._servers:
            await server.stop()
        self._clients.clear()
        self._servers.clear()

    async def __aenter__(self) -> "MPCNetwork":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
