"""
MPC Network Manager

High-level connection management for MPC clients and servers.
Handles connection lifecycle, message routing, and protocol coordination.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from .transport import MPCConnection, MPCTransport, TCPTransport, ConnectionState
from .messages import (
    MPCMessage,
    MessageType,
    HandshakeMessage,
    ShareMessage,
    OutputShareMessage,
)


logger = logging.getLogger(__name__)


MessageHandler = Callable[[MPCMessage, MPCConnection], Coroutine[Any, Any, None]]


@dataclass
class MPCNetworkManager:
    """
    Manages MPC network connections and message routing

    This class provides:
    - Connection lifecycle management
    - Automatic handshake protocol
    - Message routing to handlers
    - Reconnection with backoff
    """
    party_id: int
    n_parties: int
    threshold: int
    instance_id: int
    is_client: bool = False
    transport: Optional[MPCTransport] = None
    _message_handlers: Dict[MessageType, MessageHandler] = field(default_factory=dict)
    _pending_outputs: Dict[int, List[bytes]] = field(default_factory=dict)
    _output_events: Dict[int, asyncio.Event] = field(default_factory=dict)
    _connected_peers: Set[int] = field(default_factory=set)
    _recv_tasks: Dict[int, asyncio.Task] = field(default_factory=dict)
    _listen_task: Optional[asyncio.Task] = None
    _running: bool = False

    def __post_init__(self):
        if self.transport is None:
            self.transport = TCPTransport(local_id=self.party_id)

    def register_handler(
        self,
        msg_type: MessageType,
        handler: MessageHandler,
    ) -> None:
        """
        Register a handler for a message type

        Args:
            msg_type: The message type to handle
            handler: Async function(message, connection) -> None
        """
        self._message_handlers[msg_type] = handler

    async def connect_to_peer(self, peer_id: int, address: str) -> MPCConnection:
        """
        Connect to a peer and perform handshake

        Args:
            peer_id: The peer's party ID
            address: Network address (host:port)

        Returns:
            Connected MPCConnection

        Raises:
            ConnectionError: If connection or handshake fails
        """
        if self.transport is None:
            raise RuntimeError("Transport not initialized")

        # Connect
        conn = await self.transport.connect(address, peer_id)

        # Perform handshake
        await self._perform_handshake(conn)

        # Start receive loop
        self._start_recv_loop(conn)

        self._connected_peers.add(peer_id)
        return conn

    async def connect_to_peers(
        self,
        peers: Dict[int, str],
    ) -> Dict[int, MPCConnection]:
        """
        Connect to multiple peers concurrently

        Args:
            peers: Dict mapping peer_id -> address

        Returns:
            Dict mapping peer_id -> MPCConnection
        """
        tasks = {
            peer_id: self.connect_to_peer(peer_id, address)
            for peer_id, address in peers.items()
        }

        results = {}
        errors = []

        for peer_id, task in tasks.items():
            try:
                results[peer_id] = await task
            except Exception as e:
                errors.append(f"Failed to connect to peer {peer_id}: {e}")
                logger.error(errors[-1])

        if errors and len(errors) > self.threshold:
            # Too many failures for Byzantine fault tolerance
            raise ConnectionError(
                f"Too many connection failures ({len(errors)}): {errors}"
            )

        return results

    async def start_server(self, bind_address: str) -> None:
        """
        Start listening for incoming connections

        Args:
            bind_address: Address to bind to (host:port)
        """
        if self.transport is None:
            raise RuntimeError("Transport not initialized")

        self._running = True

        async def on_connection(conn: MPCConnection):
            """Handle incoming connection"""
            try:
                # Wait for handshake from peer
                handshake = await self._receive_handshake(conn)

                # Validate handshake
                if handshake.instance_id != self.instance_id:
                    raise ValueError(
                        f"Instance ID mismatch: expected {self.instance_id}, "
                        f"got {handshake.instance_id}"
                    )

                # Send handshake acknowledgment
                await self._send_handshake_ack(conn)

                # Register connection
                conn.peer_id = handshake.party_id
                conn.state = ConnectionState.READY

                if isinstance(self.transport, TCPTransport):
                    self.transport.add_connection(handshake.party_id, conn)

                self._connected_peers.add(handshake.party_id)
                logger.info(
                    f"Accepted connection from peer {handshake.party_id} "
                    f"(client={handshake.is_client})"
                )

                # Start receive loop
                self._start_recv_loop(conn)

            except Exception as e:
                logger.error(f"Handshake failed: {e}")
                await conn.close()

        # Start server in background
        self._listen_task = asyncio.create_task(
            self.transport.listen(bind_address, on_connection)
        )

    async def send_to_peer(self, peer_id: int, message: MPCMessage) -> None:
        """
        Send a message to a specific peer

        Args:
            peer_id: The peer to send to
            message: The message to send

        Raises:
            ConnectionError: If not connected to peer
        """
        if self.transport is None:
            raise RuntimeError("Transport not initialized")

        if isinstance(self.transport, TCPTransport):
            conn = self.transport.get_connection(peer_id)
            if conn is None:
                raise ConnectionError(f"Not connected to peer {peer_id}")
            await conn.send(message)
        else:
            raise NotImplementedError("Only TCP transport supported currently")

    async def broadcast(self, message: MPCMessage) -> None:
        """
        Broadcast a message to all connected peers

        Args:
            message: The message to broadcast
        """
        tasks = []
        for peer_id in self._connected_peers:
            tasks.append(self.send_to_peer(peer_id, message))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for peer_id, result in zip(self._connected_peers, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to send to peer {peer_id}: {result}")

    async def send_input_shares(
        self,
        shares_by_party: Dict[int, List[ShareMessage]],
    ) -> None:
        """
        Send input shares to all servers

        Args:
            shares_by_party: Dict mapping party_id -> list of ShareMessage
        """
        for party_id, shares in shares_by_party.items():
            for share in shares:
                msg = MPCMessage(
                    msg_type=MessageType.INPUT_SHARE,
                    sender_id=self.party_id,
                    instance_id=self.instance_id,
                    payload=share.to_payload(),
                )
                await self.send_to_peer(party_id, msg)

    async def wait_for_outputs(
        self,
        output_count: int,
        timeout: float = 60.0,
    ) -> List[List[bytes]]:
        """
        Wait for output shares from servers

        Args:
            output_count: Number of outputs to expect
            timeout: Timeout in seconds

        Returns:
            List of output share lists (one per output index)
        """
        # Set up events for each output
        for i in range(output_count):
            if i not in self._output_events:
                self._output_events[i] = asyncio.Event()
                self._pending_outputs[i] = []

        # Wait for all outputs
        try:
            await asyncio.wait_for(
                asyncio.gather(*[
                    self._output_events[i].wait()
                    for i in range(output_count)
                ]),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Timed out waiting for outputs after {timeout}s")

        # Collect results
        return [self._pending_outputs[i] for i in range(output_count)]

    async def close(self) -> None:
        """Close all connections and stop the server"""
        self._running = False

        # Cancel receive tasks
        for task in self._recv_tasks.values():
            task.cancel()

        # Cancel listen task
        if self._listen_task is not None:
            self._listen_task.cancel()

        # Close transport
        if self.transport is not None:
            await self.transport.close()

        self._connected_peers.clear()

    def _start_recv_loop(self, conn: MPCConnection) -> None:
        """Start background receive loop for a connection"""

        async def recv_loop():
            try:
                while self._running and conn.state == ConnectionState.READY:
                    try:
                        msg = await conn.recv()
                        await self._handle_message(msg, conn)
                    except ConnectionError:
                        break
                    except Exception as e:
                        logger.error(f"Error receiving from peer {conn.peer_id}: {e}")
                        break
            finally:
                if conn.peer_id in self._connected_peers:
                    self._connected_peers.remove(conn.peer_id)

        task = asyncio.create_task(recv_loop())
        self._recv_tasks[conn.peer_id] = task

    async def _handle_message(self, msg: MPCMessage, conn: MPCConnection) -> None:
        """Route a message to the appropriate handler"""
        # Handle output shares specially for clients
        if msg.msg_type == MessageType.OUTPUT_SHARE:
            output = OutputShareMessage.from_payload(msg.payload)
            if output.output_index not in self._pending_outputs:
                self._pending_outputs[output.output_index] = []
                self._output_events[output.output_index] = asyncio.Event()

            self._pending_outputs[output.output_index].append(output.share_bytes)

            # Check if we have enough shares (threshold + 1)
            if len(self._pending_outputs[output.output_index]) >= self.threshold + 1:
                self._output_events[output.output_index].set()

            return

        # Check for registered handler
        handler = self._message_handlers.get(msg.msg_type)
        if handler is not None:
            await handler(msg, conn)
        else:
            logger.warning(f"No handler for message type {msg.msg_type.name}")

    async def _perform_handshake(self, conn: MPCConnection) -> None:
        """Perform handshake as the connecting party"""
        conn.state = ConnectionState.HANDSHAKING

        # Send handshake
        handshake = HandshakeMessage(
            party_id=self.party_id,
            is_client=self.is_client,
            n_parties=self.n_parties,
            threshold=self.threshold,
            instance_id=self.instance_id,
        )

        msg = MPCMessage(
            msg_type=MessageType.HANDSHAKE,
            sender_id=self.party_id,
            instance_id=self.instance_id,
            payload=handshake.to_payload(),
        )

        await conn.send(msg)

        # Wait for acknowledgment
        ack = await conn.recv()
        if ack.msg_type != MessageType.HANDSHAKE_ACK:
            raise ConnectionError(
                f"Expected HANDSHAKE_ACK, got {ack.msg_type.name}"
            )

        conn.state = ConnectionState.READY
        logger.debug(f"Handshake complete with peer {conn.peer_id}")

    async def _receive_handshake(self, conn: MPCConnection) -> HandshakeMessage:
        """Receive handshake from connecting party"""
        msg = await conn.recv()

        if msg.msg_type != MessageType.HANDSHAKE:
            raise ConnectionError(f"Expected HANDSHAKE, got {msg.msg_type.name}")

        return HandshakeMessage.from_payload(msg.payload)

    async def _send_handshake_ack(self, conn: MPCConnection) -> None:
        """Send handshake acknowledgment"""
        msg = MPCMessage(
            msg_type=MessageType.HANDSHAKE_ACK,
            sender_id=self.party_id,
            instance_id=self.instance_id,
            payload=b"",
        )
        await conn.send(msg)
