"""
Type definitions for MPC protocols

This module defines high-level types for MPC functionality,
abstracting away low-level cryptographic details.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json


class MPCProtocol(Enum):
    """Available MPC protocols"""
    HONEYBADGER = "honeybadger"
    SHAMIR = "shamir"  # For simpler threshold schemes


@dataclass
class SecretValue:
    """
    Represents a secret value in an MPC computation
    
    This abstraction hides the underlying field operations and
    share types from the developer.
    """
    value: Union[int, float, str, bytes]
    value_type: str = "auto"  # auto-detect from value type
    
    @classmethod
    def from_int(cls, value: int) -> "SecretValue":
        """Create secret value from integer"""
        return cls(value=value, value_type="int")
    
    @classmethod
    def from_float(cls, value: float) -> "SecretValue":
        """Create secret value from float"""
        return cls(value=value, value_type="float")
    
    @classmethod
    def from_string(cls, value: str) -> "SecretValue":
        """Create secret value from string"""
        return cls(value=value, value_type="string")
    
    @classmethod
    def from_bytes(cls, value: bytes) -> "SecretValue":
        """Create secret value from bytes"""
        return cls(value=value, value_type="bytes")
    
    def to_native(self) -> Any:
        """Convert back to native Python type"""
        return self.value


@dataclass
class MPCFunction:
    """
    Represents a function to be executed in MPC
    
    The function is defined in StoffelVM and executed securely
    across multiple parties.
    """
    name: str
    inputs: List[SecretValue]
    protocol: MPCProtocol = MPCProtocol.HONEYBADGER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "inputs": [{"value": inp.value, "type": inp.value_type} for inp in self.inputs],
            "protocol": self.protocol.value
        }


@dataclass
class MPCResult:
    """
    Result of an MPC computation
    
    Contains the computed result and metadata about the computation.
    """
    value: Any
    computation_id: str
    success: bool
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def is_success(self) -> bool:
        """Check if computation was successful"""
        return self.success
    
    def get_value(self) -> Any:
        """Get the computed value"""
        if not self.success:
            raise ValueError(f"Computation failed: {self.error_message}")
        return self.value


@dataclass
class MPCConfig:
    """
    Configuration for MPC operations
    
    Specifies the protocol parameters without exposing
    low-level cryptographic details.
    """
    protocol: MPCProtocol = MPCProtocol.HONEYBADGER
    security_level: int = 128  # bits of security
    fault_tolerance: Optional[int] = None  # auto-calculate if None
    network_timeout: float = 30.0  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "protocol": self.protocol.value,
            "security_level": self.security_level,
            "fault_tolerance": self.fault_tolerance,
            "network_timeout": self.network_timeout
        }


class MPCError(Exception):
    """Base exception for MPC operations"""
    pass


class ComputationError(MPCError):
    """Exception raised when MPC computation fails"""
    pass


class NetworkError(MPCError):
    """Exception raised for network-related errors"""
    pass


class ProtocolError(MPCError):
    """Exception raised for protocol-specific errors"""
    pass


class ConfigurationError(MPCError):
    """Exception raised for configuration errors"""
    pass