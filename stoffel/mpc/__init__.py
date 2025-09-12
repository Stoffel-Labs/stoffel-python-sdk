"""
MPC types and configurations

This module provides basic MPC types and configurations that are used
by the main client and program components.
"""

from .types import (
    SecretValue, 
    MPCResult, 
    MPCConfig, 
    MPCProtocol,
    MPCError,
    ComputationError,
    NetworkError,
    ConfigurationError
)

__all__ = [
    # Core types for advanced usage
    "SecretValue",
    "MPCResult", 
    "MPCConfig",
    "MPCProtocol",
    
    # Exceptions
    "MPCError",
    "ComputationError",
    "NetworkError", 
    "ConfigurationError",
]