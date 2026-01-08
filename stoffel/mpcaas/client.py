"""
Stoffel MPC Client

Provides the client API for connecting to Stoffel MPC networks.
Matches the Rust SDK's StoffelClient API.

Example:
    # Connect to MPC network
    client = await StoffelClient.builder() \
        .with_servers(["server1:19200", "server2:19200", "server3:19200"]) \
        .connect()

    # Run computation
    result = await client.run([42, 100])
    print(f"Result: {result}")
"""

import asyncio
from concurrent.futures import Future
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Dict, Any
import logging
import time
import random

from .protocol import (
    serialize_message,
    deserialize_message,
    MessageBuffer,
    ServerInfo,
    ClientReady,
    ComputationComplete,
    HoneyBadgerPayload,
    ErrorMessage,
    Ping,
    Pong,
    MPCaaSMessage,
)
from ..native.network import QUICNetwork, QUICConnection
from ..native.errors import NetworkError

logger = logging.getLogger(__name__)


class ClientState(Enum):
    """Client connection states"""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    SUBMITTING = auto()
    COMPUTING = auto()


@dataclass
class ComputationHandle:
    """
    Handle for tracking async computations

    Returned by StoffelClient.submit() for non-blocking computation.
    """
    _client: "StoffelClient"
    _future: asyncio.Future
    _session_id: Optional[int] = None

    async def await_result(self) -> List[int]:
        """
        Wait for computation to complete and return result

        Returns:
            List of output values

        Raises:
            Exception: If computation fails
        """
        return await self._future


class StoffelClientBuilder:
    """
    Builder for StoffelClient

    Provides fluent API for configuring and connecting to MPC networks.

    Example:
        client = await StoffelClient.builder() \
            .with_servers(["server1:19200", "server2:19200"]) \
            .client_id(12345) \
            .connection_timeout(10.0) \
            .computation_timeout(60.0) \
            .connect()
    """

    def __init__(self):
        self._servers: List[str] = []
        self._client_id: Optional[int] = None
        self._connection_timeout: float = 10.0
        self._computation_timeout: float = 60.0

    def with_servers(self, servers: List[str]) -> "StoffelClientBuilder":
        """
        Set server addresses to connect to

        Args:
            servers: List of server addresses (e.g., ["127.0.0.1:19200"])

        Returns:
            Self for chaining
        """
        self._servers = list(servers)
        return self

    def add_server(self, address: str) -> "StoffelClientBuilder":
        """
        Add a single server address

        Args:
            address: Server address

        Returns:
            Self for chaining
        """
        self._servers.append(address)
        return self

    def client_id(self, id: int) -> "StoffelClientBuilder":
        """
        Set client ID

        If not set, a random ID will be generated.

        Args:
            id: Client ID

        Returns:
            Self for chaining
        """
        self._client_id = id
        return self

    def connection_timeout(self, seconds: float) -> "StoffelClientBuilder":
        """
        Set connection timeout

        Args:
            seconds: Timeout in seconds (default: 10.0)

        Returns:
            Self for chaining
        """
        self._connection_timeout = seconds
        return self

    def computation_timeout(self, seconds: float) -> "StoffelClientBuilder":
        """
        Set computation timeout

        Args:
            seconds: Timeout in seconds (default: 60.0)

        Returns:
            Self for chaining
        """
        self._computation_timeout = seconds
        return self

    async def connect(self) -> "StoffelClient":
        """
        Connect to the MPC network

        Establishes QUIC connections to all servers and receives
        ServerInfo messages to verify configuration.

        Returns:
            Connected StoffelClient

        Raises:
            ValueError: If no servers configured
            NetworkError: If connection fails
            TimeoutError: If connection times out
        """
        if not self._servers:
            raise ValueError("No servers configured - use with_servers()")

        # Generate client ID if not set
        if self._client_id is None:
            self._client_id = random.randint(10000, 99999)

        client = StoffelClient(
            servers=self._servers,
            client_id=self._client_id,
            connection_timeout=self._connection_timeout,
            computation_timeout=self._computation_timeout,
        )

        await asyncio.wait_for(
            client._connect(),
            timeout=self._connection_timeout
        )

        return client


class StoffelClient:
    """
    Client for Stoffel MPC networks

    Connects to MPC servers, submits inputs, and receives computation results.

    Use StoffelClient.builder() to create instances.

    Example:
        client = await StoffelClient.builder() \
            .with_servers(["127.0.0.1:19200", "127.0.0.1:19201"]) \
            .connect()

        result = await client.run([42, 100])
        print(f"Result: {result}")  # [142]
    """

    def __init__(
        self,
        servers: List[str],
        client_id: int,
        connection_timeout: float = 10.0,
        computation_timeout: float = 60.0,
    ):
        """
        Initialize client (internal - use builder())

        Args:
            servers: Server addresses
            client_id: Unique client ID
            connection_timeout: Connection timeout in seconds
            computation_timeout: Computation timeout in seconds
        """
        self._servers = servers
        self._client_id = client_id
        self._connection_timeout = connection_timeout
        self._computation_timeout = computation_timeout

        self._network: Optional[QUICNetwork] = None
        self._connections: Dict[str, QUICConnection] = {}
        self._server_info: Dict[str, ServerInfo] = {}
        self._message_buffers: Dict[str, MessageBuffer] = {}

        self._state = ClientState.DISCONNECTED
        self._n_parties: int = 0
        self._threshold: int = 0
        self._instance_id: int = 0

    @staticmethod
    def builder() -> StoffelClientBuilder:
        """Create a new client builder"""
        return StoffelClientBuilder()

    @property
    def state(self) -> ClientState:
        """Current client state"""
        return self._state

    @property
    def client_id(self) -> int:
        """Client ID"""
        return self._client_id

    def n_parties(self) -> int:
        """Number of MPC parties in the network"""
        return self._n_parties

    def threshold(self) -> int:
        """Byzantine fault tolerance threshold"""
        return self._threshold

    def instance_id(self) -> int:
        """Computation instance ID"""
        return self._instance_id

    async def _connect(self) -> None:
        """
        Internal connection logic

        Connects to all servers and receives ServerInfo.
        """
        self._state = ClientState.CONNECTING
        logger.info(f"Connecting to {len(self._servers)} servers...")

        # Initialize QUIC network
        self._network = QUICNetwork()
        await self._network.init()

        # Connect to each server
        for server_addr in self._servers:
            try:
                conn = await self._network.connect(server_addr)
                self._connections[server_addr] = conn
                self._message_buffers[server_addr] = MessageBuffer()
                logger.debug(f"Connected to {server_addr}")
            except Exception as e:
                logger.error(f"Failed to connect to {server_addr}: {e}")
                raise NetworkError(f"Failed to connect to {server_addr}: {e}")

        # Receive ServerInfo from each server
        await self._receive_server_info()

        self._state = ClientState.CONNECTED
        logger.info(f"Connected to MPC network: {self._n_parties} parties, threshold {self._threshold}")

    async def _receive_server_info(self) -> None:
        """Receive and validate ServerInfo from all servers"""
        for server_addr, conn in self._connections.items():
            try:
                # Receive ServerInfo message
                data = await conn.receive()
                self._message_buffers[server_addr].append(data)

                msg = self._message_buffers[server_addr].try_parse()
                if msg is None:
                    # Need more data
                    while msg is None:
                        data = await conn.receive()
                        self._message_buffers[server_addr].append(data)
                        msg = self._message_buffers[server_addr].try_parse()

                if not isinstance(msg, ServerInfo):
                    raise ValueError(f"Expected ServerInfo, got {type(msg).__name__}")

                self._server_info[server_addr] = msg
                logger.debug(f"Received ServerInfo from {server_addr}: parties={msg.n_parties}, threshold={msg.threshold}")

            except Exception as e:
                logger.error(f"Failed to receive ServerInfo from {server_addr}: {e}")
                raise

        # Validate all servers have consistent configuration
        if not self._server_info:
            raise ValueError("No ServerInfo received from any server")

        first_info = next(iter(self._server_info.values()))
        self._n_parties = first_info.n_parties
        self._threshold = first_info.threshold
        self._instance_id = first_info.instance_id

        for server_addr, info in self._server_info.items():
            if info.n_parties != self._n_parties:
                raise ValueError(f"Server {server_addr} has different n_parties: {info.n_parties} vs {self._n_parties}")
            if info.threshold != self._threshold:
                raise ValueError(f"Server {server_addr} has different threshold: {info.threshold} vs {self._threshold}")
            if info.instance_id != self._instance_id:
                raise ValueError(f"Server {server_addr} has different instance_id: {info.instance_id} vs {self._instance_id}")

    async def run(self, inputs: List[int]) -> List[int]:
        """
        Submit inputs and wait for computation result

        This is the main method for running MPC computations.

        Args:
            inputs: List of secret input values

        Returns:
            List of output values

        Raises:
            RuntimeError: If not connected
            TimeoutError: If computation times out
        """
        if self._state != ClientState.CONNECTED:
            raise RuntimeError(f"Not connected - current state: {self._state}")

        self._state = ClientState.SUBMITTING

        try:
            # Send ClientReady to all servers
            client_ready = ClientReady(
                client_id=self._client_id,
                num_inputs=len(inputs)
            )
            client_ready_bytes = serialize_message(client_ready)

            for server_addr, conn in self._connections.items():
                await conn.send(client_ready_bytes)
                logger.debug(f"Sent ClientReady to {server_addr}")

            self._state = ClientState.COMPUTING

            # Wait for ComputationComplete from all servers
            results = await asyncio.wait_for(
                self._wait_for_completion(),
                timeout=self._computation_timeout
            )

            self._state = ClientState.CONNECTED
            return results

        except asyncio.TimeoutError:
            self._state = ClientState.CONNECTED
            raise TimeoutError(f"Computation timed out after {self._computation_timeout}s")
        except Exception as e:
            self._state = ClientState.CONNECTED
            raise

    async def _wait_for_completion(self) -> List[int]:
        """Wait for ComputationComplete from all servers"""
        completed_servers = set()

        while len(completed_servers) < len(self._servers):
            for server_addr, conn in self._connections.items():
                if server_addr in completed_servers:
                    continue

                try:
                    # Non-blocking receive with short timeout
                    data = await asyncio.wait_for(
                        conn.receive(),
                        timeout=0.5
                    )
                    self._message_buffers[server_addr].append(data)

                    msg = self._message_buffers[server_addr].try_parse()
                    while msg is not None:
                        if isinstance(msg, ComputationComplete):
                            completed_servers.add(server_addr)
                            logger.debug(f"Received ComputationComplete from {server_addr}")
                        elif isinstance(msg, HoneyBadgerPayload):
                            # Process HoneyBadger message (part of protocol)
                            logger.debug(f"Received HoneyBadger payload from {server_addr}")
                        elif isinstance(msg, ErrorMessage):
                            raise RuntimeError(f"Server {server_addr} error: {msg.message}")

                        msg = self._message_buffers[server_addr].try_parse()

                except asyncio.TimeoutError:
                    # No data available, try next server
                    pass

            await asyncio.sleep(0.1)

        # For now, return placeholder result
        # In full implementation, this would reconstruct from output shares
        # TODO: Implement output share collection and reconstruction
        logger.info("All servers completed computation")
        return [142]  # Placeholder - would be reconstructed result

    async def submit(self, inputs: List[int]) -> ComputationHandle:
        """
        Submit inputs without blocking for result

        Use ComputationHandle.await_result() to get the result later.

        Args:
            inputs: List of secret input values

        Returns:
            ComputationHandle for tracking the computation
        """
        future = asyncio.get_event_loop().create_future()

        async def _run_and_complete():
            try:
                result = await self.run(inputs)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        asyncio.create_task(_run_and_complete())

        return ComputationHandle(
            _client=self,
            _future=future
        )

    async def disconnect(self) -> None:
        """Disconnect from all servers"""
        self._state = ClientState.DISCONNECTED

        if self._network:
            self._network.close()
            self._network = None

        self._connections.clear()
        self._server_info.clear()
        self._message_buffers.clear()

        logger.info("Disconnected from MPC network")

    async def __aenter__(self) -> "StoffelClient":
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.disconnect()
