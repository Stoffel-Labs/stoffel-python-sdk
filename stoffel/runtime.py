"""
Stoffel Runtime

Thin wrapper holding compiled program bytecode and MPC configuration.
Users access client/server builders separately via mpcaas module.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from .enums import ProtocolType, ShareType
from .error import IoError


@dataclass
class MPCConfig:
    """
    MPC configuration matching Rust SDK API

    Holds the parameters needed for MPC execution. Validated
    during StoffelBuilder.build().
    """
    parties: int
    threshold: int
    instance_id: int
    protocol_type: ProtocolType = ProtocolType.HONEYBADGER
    share_type: ShareType = ShareType.ROBUST

    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.parties < 1:
            raise ValueError("parties must be at least 1")
        if self.threshold < 0:
            raise ValueError("threshold cannot be negative")
        if self.instance_id < 0:
            raise ValueError("instance_id cannot be negative")


class StoffelRuntime:
    """
    Holds compiled program + MPC configuration (thin wrapper)

    This is the result of calling StoffelBuilder.build(). It contains
    the compiled bytecode and MPC parameters, but does not provide
    client/server builder methods.

    Users should use the existing builders directly:
    - StoffelClient.builder() from stoffel.mpcaas
    - StoffelServer.builder() from stoffel.mpcaas

    Example:
        runtime = Stoffel.compile(source) \\
            .parties(5) \\
            .threshold(1) \\
            .build()

        # Access program bytecode
        bytecode = runtime.program

        # Access MPC configuration
        config = runtime.mpc_config

        # Save program to file
        runtime.save_program("program.stfb")
    """

    def __init__(self, program: bytes, config: MPCConfig):
        """
        Initialize runtime with program and config

        Args:
            program: Compiled bytecode
            config: MPC configuration
        """
        self._program = program
        self._config = config

    @property
    def program(self) -> bytes:
        """Get compiled program bytecode"""
        return self._program

    @property
    def mpc_config(self) -> MPCConfig:
        """Get MPC configuration"""
        return self._config

    @property
    def parties(self) -> int:
        """Number of MPC parties"""
        return self._config.parties

    @property
    def threshold(self) -> int:
        """Byzantine fault tolerance threshold"""
        return self._config.threshold

    @property
    def instance_id(self) -> int:
        """Computation instance ID"""
        return self._config.instance_id

    @property
    def protocol_type(self) -> ProtocolType:
        """MPC protocol type"""
        return self._config.protocol_type

    @property
    def share_type(self) -> ShareType:
        """Secret sharing scheme"""
        return self._config.share_type

    def save_program(self, path: str) -> None:
        """
        Save program bytecode to file

        Args:
            path: File path to save to (typically .stfb extension)

        Raises:
            IoError: If file cannot be written
        """
        try:
            Path(path).write_bytes(self._program)
        except Exception as e:
            raise IoError(f"Failed to save program to {path}", cause=e)

    def __repr__(self) -> str:
        return (
            f"StoffelRuntime("
            f"program={len(self._program)} bytes, "
            f"parties={self.parties}, "
            f"threshold={self.threshold}, "
            f"instance_id={self.instance_id}, "
            f"protocol={self.protocol_type.name}, "
            f"share_type={self.share_type.name})"
        )
