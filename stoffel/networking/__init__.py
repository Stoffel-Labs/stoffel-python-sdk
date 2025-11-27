"""
Networking module for Stoffel MPC

This module provides async networking infrastructure for MPC communication
using Python's asyncio. It supports both TCP and (optionally) QUIC transports.

Components:
- MPCConnection: Individual connection to a peer
- MPCTransport: Transport layer abstraction
- MPCMessageHandler: Message routing and handling
- MPCNetworkManager: Connection lifecycle management
- Helper functions for easy network setup
"""

from .transport import (
    MPCConnection,
    MPCTransport,
    TCPTransport,
    ConnectionState,
)
from .messages import (
    MPCMessage,
    MessageType,
    ShareMessage,
    OutputShareMessage,
    PreprocessingMessage,
    HandshakeMessage,
    serialize_message,
    deserialize_message,
)
from .manager import MPCNetworkManager
from .helpers import (
    setup_honeybadger_network,
    setup_client_with_servers,
    run_mpc_computation,
    generate_local_addresses,
    MPCNetwork,
)

__all__ = [
    # Transport
    "MPCConnection",
    "MPCTransport",
    "TCPTransport",
    "ConnectionState",
    # Messages
    "MPCMessage",
    "MessageType",
    "ShareMessage",
    "OutputShareMessage",
    "PreprocessingMessage",
    "HandshakeMessage",
    "serialize_message",
    "deserialize_message",
    # Manager
    "MPCNetworkManager",
    # Helpers
    "setup_honeybadger_network",
    "setup_client_with_servers",
    "run_mpc_computation",
    "generate_local_addresses",
    "MPCNetwork",
]
