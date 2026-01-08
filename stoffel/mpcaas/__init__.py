"""
MPCaaS (MPC as a Service) module

This module provides the client-server architecture for Stoffel MPC operations:
- StoffelClient: For app developers connecting to an MPC network
- StoffelServer: For infrastructure operators running MPC compute nodes

Protocol messages are defined in protocol.py and are compatible with the
Rust SDK's message format.
"""

from .protocol import (
    MPCaaSMessage,
    ErrorCode,
    MessageBuffer,
    serialize_message,
    deserialize_message,
    MPCAAS_MAGIC,
    PROTOCOL_VERSION,
)

from .client import (
    StoffelClient,
    StoffelClientBuilder,
    ClientState,
    ComputationHandle,
)

from .server import (
    StoffelServer,
    StoffelServerBuilder,
    ServerState,
)

__all__ = [
    # Protocol
    "MPCaaSMessage",
    "ErrorCode",
    "MessageBuffer",
    "serialize_message",
    "deserialize_message",
    "MPCAAS_MAGIC",
    "PROTOCOL_VERSION",

    # Client
    "StoffelClient",
    "StoffelClientBuilder",
    "ClientState",
    "ComputationHandle",

    # Server
    "StoffelServer",
    "StoffelServerBuilder",
    "ServerState",
]
