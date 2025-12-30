"""
Stoffel Python SDK

A Python SDK for the Stoffel framework, providing:
- Stoffel program compilation and management
- MPC network participants (clients, servers, nodes)
- Secure multi-party computation with Byzantine fault tolerance

Usage:
    from stoffel import Stoffel

    # Compile and execute locally
    result = Stoffel.compile("main main() -> int64:\\n  return 42").execute_local()

    # Compile with MPC configuration
    runtime = (Stoffel.compile("main main() -> int64:\\n  return 42")
        .parties(5)
        .threshold(1)
        .build())

    # Create MPC participants
    client = runtime.client(100).with_inputs([10, 20]).build()
    server = runtime.server(0).build()
"""

__version__ = "0.1.0"
__author__ = "Stoffel Labs"

# Main API
from .stoffel import (
    Stoffel,
    StoffelRuntime,
    Program,
    ProtocolType,
    ShareType,
    OptimizationLevel,
)

# MPC participants and errors
from .mpc import (
    MPCClient,
    MPCClientBuilder,
    MPCServer,
    MPCServerBuilder,
    MPCNode,
    MPCNodeBuilder,
    MPCConfig,
    # Exceptions
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

# Compiler
from .compiler import StoffelCompiler, CompilerOptions

# Network configuration
from .network_config import NetworkConfig, NetworkSettings, MPCSettings

# Coordinator (mock for testing, production uses external service)
from .coordinator import (
    MockMPCCoordinator,
    MPCSession,
    SessionState,
    ComputationResult,
    CoordinatorClient,
)

# Core bindings availability
from ._core import is_native_available, get_binding_method

__all__ = [
    # Main API
    "Stoffel",
    "StoffelRuntime",
    "Program",
    "ProtocolType",
    "ShareType",
    "OptimizationLevel",

    # MPC participants
    "MPCClient",
    "MPCClientBuilder",
    "MPCServer",
    "MPCServerBuilder",
    "MPCNode",
    "MPCNodeBuilder",
    "MPCConfig",

    # Compiler
    "StoffelCompiler",
    "CompilerOptions",

    # Network configuration
    "NetworkConfig",
    "NetworkSettings",
    "MPCSettings",

    # Coordinator
    "MockMPCCoordinator",
    "MPCSession",
    "SessionState",
    "ComputationResult",
    "CoordinatorClient",

    # Core bindings
    "is_native_available",
    "get_binding_method",

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