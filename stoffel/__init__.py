"""
Stoffel Python SDK

A clean Python SDK for the Stoffel framework, providing:
- StoffelLang program compilation and management
- MPC network client for secure computations
- Clear separation of concerns between VM and network operations

Simple usage:
    from stoffel import StoffelProgram, StoffelMPCClient
    
    # VM handles program compilation and setup
    program = StoffelProgram("secure_add.stfl")
    program.compile()
    program.set_execution_params({...})
    
    # Client handles MPC network communication  
    client = StoffelMPCClient({"program_id": "secure_add", ...})
    result = await client.execute_program_with_inputs({"a": 25, "b": 17})
"""

__version__ = "0.1.0"
__author__ = "Stoffel Labs"

# Main API - Clean separation of concerns
from .program import StoffelProgram, compile_stoffel_program
from .client import StoffelMPCClient

# Core components for advanced usage
from .compiler import StoffelCompiler, CompiledProgram
from .vm import VirtualMachine
from .mpc import MPCConfig, MPCProtocol

__all__ = [
    # Main API (recommended for most users)
    "StoffelProgram",         # VM: compilation, loading, execution params
    "StoffelMPCClient",       # Client: network communication, private data
    "compile_stoffel_program", # Convenience function for compilation
    
    # Core components for advanced usage
    "StoffelCompiler", 
    "CompiledProgram",
    "VirtualMachine",
    "MPCConfig",
    "MPCProtocol",
]