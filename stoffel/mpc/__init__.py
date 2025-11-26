"""
MPC types, participants, and configurations

This module provides MPC participant classes (Client, Server, Node) and their builders,
along with basic MPC types and configurations.

Usage:
    from stoffel.mpc import MPCClient, MPCServer, MPCNode, MPCConfig
"""

from .types import (
    MPCConfig,
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

from .client import MPCClient, MPCClientBuilder
from .server import MPCServer, MPCServerBuilder
from .node import MPCNode, MPCNodeBuilder

__all__ = [
    # MPC participants
    "MPCClient",
    "MPCClientBuilder",
    "MPCServer",
    "MPCServerBuilder",
    "MPCNode",
    "MPCNodeBuilder",

    # Configuration
    "MPCConfig",

    # Exceptions
    "StoffelError",
    "MPCError",
    "ComputationError",
    "NetworkError",
    "ConfigurationError",
    "ProtocolError",
    "PreprocessingError",
    "IoError",
    "InvalidInputError",
    "FunctionNotFoundError",
]