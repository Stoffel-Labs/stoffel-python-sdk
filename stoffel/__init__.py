"""
Stoffel Python SDK

A clean Python SDK for the Stoffel framework, providing:
- StoffelLang program compilation and management
- MPC network client for secure computations
- MPCaaS (MPC as a Service) client-server architecture

Simple usage (MPCaaS - recommended):
    from stoffel import StoffelClient, StoffelServer

    # Client API - for app developers
    client = await StoffelClient.builder() \
        .with_servers(["server1:19200", "server2:19200"]) \
        .connect()
    result = await client.run([42, 100])

    # Server API - for infrastructure operators
    server = StoffelServer.builder(party_id=0) \
        .bind("0.0.0.0:19200") \
        .with_peers([(1, "127.0.0.1:19201")]) \
        .with_instance_id(12345) \
        .build()
    await server.start()
    await server.run_forever()

Legacy usage:
    from stoffel import StoffelProgram, StoffelMPCClient

    program = StoffelProgram("secure_add.stfl")
    program.compile()
"""

__version__ = "0.1.0"
__author__ = "Stoffel Labs"

# MPCaaS API (recommended)
from .mpcaas import (
    StoffelClient,
    StoffelClientBuilder,
    ClientState,
    ComputationHandle,
    StoffelServer,
    StoffelServerBuilder,
    ServerState,
)

# Native bindings
from .native import is_native_available

# Legacy API
from .program import StoffelProgram, compile_stoffel_program
from .client import StoffelClient as LegacyStoffelClient

# Core components for advanced usage
from .compiler import StoffelCompiler, CompiledProgram
from .vm import VirtualMachine
from .mpc import MPCConfig, MPCProtocol

__all__ = [
    # MPCaaS API (recommended for most users)
    "StoffelClient",          # MPCaaS client for app developers
    "StoffelClientBuilder",   # Builder for StoffelClient
    "ClientState",            # Client connection states
    "ComputationHandle",      # Async computation handle
    "StoffelServer",          # MPCaaS server for infrastructure
    "StoffelServerBuilder",   # Builder for StoffelServer
    "ServerState",            # Server states

    # Native bindings
    "is_native_available",    # Check if native libs are loaded

    # Legacy API
    "StoffelProgram",         # VM: compilation, loading, execution params
    "LegacyStoffelClient",    # Legacy client (renamed to avoid conflict)
    "compile_stoffel_program", # Convenience function for compilation

    # Core components for advanced usage
    "StoffelCompiler",
    "CompiledProgram",
    "VirtualMachine",
    "MPCConfig",
    "MPCProtocol",
]