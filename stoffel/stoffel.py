"""
Stoffel - Main entry point for the Stoffel Python SDK

This module provides the Stoffel class, which is the main gateway for all SDK functionality.
It uses a builder pattern for configuring MPC parameters.

Usage:
    from stoffel import Stoffel

    # Compile and execute locally
    result = Stoffel.compile("main main() -> int64:\\n  return 42").execute_local()

    # Compile with MPC configuration (minimum 3 parties for HoneyBadger MPC)
    runtime = (Stoffel.compile("main main() -> int64:\\n  return 42")
        .parties(4)
        .threshold(1)
        .build())

    # Create MPC participants
    client = runtime.client(100).with_inputs([10, 20]).build()
    server = runtime.server(0).build()
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from enum import Enum
import os

from .compiler import StoffelCompiler, CompilerOptions
from .compiler.program import CompiledProgram


class ProtocolType(Enum):
    """
    MPC Protocol Type - specifies which MPC protocol to use

    The SDK automatically uses HoneyBadger by default. Developers don't need to
    worry about protocol selection for typical use cases.

    HoneyBadger Protocol provides:
    - Byzantine Fault Tolerance: Handles up to t malicious parties (where n >= 3t+1)
    - Asynchronous Communication: No timing assumptions or synchronization required
    - Robust Secret Sharing: Built-in error detection and correction
    - Optimal Resilience: Maximum fault tolerance for the given number of parties
    """
    HONEYBADGER = "honeybadger"


class ShareType(Enum):
    """
    Secret sharing scheme type

    This enum specifies which secret sharing implementation to use for MPC operations.
    Different share types provide different security guarantees and performance characteristics.

    Default: ROBUST (matches ProtocolType.HONEYBADGER)
    """
    ROBUST = "robust"
    """
    RobustShare - Shamir secret sharing with error correction

    This is the default share type. It uses Reed-Solomon erasure coding
    to provide robust reconstruction even when some shares are corrupted.
    Required for HoneyBadger protocol's Byzantine fault tolerance.

    Properties:
    - Error correction capability
    - Byzantine fault tolerant
    - Slightly higher computational cost
    """

    NON_ROBUST = "non_robust"
    """
    NonRobustShare - Standard Shamir secret sharing

    Simple Shamir secret sharing without error correction. Faster but
    requires all shares to be correct. Suitable for semi-honest settings
    or when error correction is not needed.

    Properties:
    - No error correction
    - Faster computation
    - Requires honest parties
    """


class OptimizationLevel(Enum):
    """Optimization levels for the compiler"""
    NONE = 0
    O1 = 1
    O2 = 2
    O3 = 3


class Stoffel:
    """
    High-level Stoffel SDK - the main entry point for the Stoffel ecosystem

    Stoffel is the gateway for all SDK functionality. It provides methods for:
    - Compiling Stoffel source code to bytecode
    - Configuring MPC infrastructure (parties, threshold, protocol, network)
    - Building StoffelRuntime instances for MPC execution

    The SDK uses the HoneyBadger MPC protocol by default, which provides Byzantine
    fault tolerance without requiring any configuration.

    Architecture::

        Stoffel.compile()
            |
            v
        Stoffel (configure MPC params + protocol)
            |
            v
        StoffelRuntime (holds Program + MPC config + Protocol)
            |
            v
        MPCClient / MPCServer / MPCNode (participants using configured protocol)

    Note:
        HoneyBadger MPC requires a minimum of 3 parties.

    Examples:
        Quick Local Execution::

            result = Stoffel.compile("main main() -> int64:\\n  return 42").execute_local()

        MPC Infrastructure Setup (minimum 3 parties)::

            runtime = (Stoffel.compile("main main() -> int64:\\n  return 42")
                .parties(4)
                .threshold(1)
                .instance_id(42)
                .build())

            # Create MPC participants
            client = runtime.client(100).with_inputs([42]).build()
            server = runtime.server(0).build()
    """

    def __init__(self):
        """Create a new Stoffel builder (internal use - prefer compile/compile_file/load)"""
        self._source: Optional[str] = None
        self._file_path: Optional[str] = None
        self._bytecode: Optional[bytes] = None
        self._optimize: bool = False
        self._optimization_level: OptimizationLevel = OptimizationLevel.NONE
        self._n_parties: Optional[int] = None
        self._threshold: Optional[int] = None
        self._instance_id: int = 0
        self._network_config: Optional[Dict[str, Any]] = None
        self._protocol_type: ProtocolType = ProtocolType.HONEYBADGER
        self._share_type: ShareType = ShareType.ROBUST

    @classmethod
    def compile(cls, source: str) -> "Stoffel":
        """
        Compile Stoffel source code

        Returns a Stoffel builder to configure MPC parameters.

        Args:
            source: Stoffel source code string

        Returns:
            Stoffel builder for further configuration

        Example:
            runtime = (Stoffel.compile("main main() -> int64:\\n  return 42")
                .parties(5)
                .threshold(1)
                .build())
        """
        builder = cls()
        builder._source = source

        # Compile immediately to catch errors early
        compiler = StoffelCompiler()
        compiled = compiler.compile_source(source)
        builder._bytecode = compiled.bytecode

        return builder

    @classmethod
    def compile_file(cls, path: str) -> "Stoffel":
        """
        Compile a Stoffel program from a file

        Args:
            path: Path to the .stfl source file

        Returns:
            Stoffel builder for further configuration

        Example:
            runtime = (Stoffel.compile_file("program.stfl")
                .parties(5)
                .build())
        """
        builder = cls()
        builder._file_path = path

        # Compile immediately to catch errors early
        compiler = StoffelCompiler()
        compiled = compiler.compile_file(path)
        builder._bytecode = compiled.bytecode

        return builder

    @classmethod
    def load(cls, bytecode: bytes) -> "Stoffel":
        """
        Load from pre-compiled bytecode

        Args:
            bytecode: Pre-compiled Stoffel bytecode

        Returns:
            Stoffel builder for further configuration

        Example:
            with open("program.stfb", "rb") as f:
                bytecode = f.read()
            runtime = Stoffel.load(bytecode).parties(5).build()
        """
        builder = cls()
        builder._bytecode = bytecode
        return builder

    @classmethod
    def new(cls) -> "Stoffel":
        """Create a new empty Stoffel builder"""
        return cls()

    def source(self, source: str) -> "Stoffel":
        """Set the source code to compile"""
        self._source = source
        return self

    def file(self, path: str) -> "Stoffel":
        """Set the file path to compile"""
        self._file_path = path
        return self

    def optimize(self, enable: bool = True) -> "Stoffel":
        """
        Enable optimization

        Args:
            enable: Whether to enable optimization (default: True)

        Returns:
            Self for method chaining
        """
        self._optimize = enable
        if enable and self._optimization_level == OptimizationLevel.NONE:
            self._optimization_level = OptimizationLevel.O2
        return self

    def optimization_level(self, level: OptimizationLevel) -> "Stoffel":
        """
        Set the optimization level

        Args:
            level: Optimization level (NONE, O1, O2, O3)

        Returns:
            Self for method chaining
        """
        self._optimization_level = level
        self._optimize = level != OptimizationLevel.NONE
        return self

    def parties(self, n: int) -> "Stoffel":
        """
        Set the number of MPC parties

        This is the total number of servers in the MPC network.
        HoneyBadger MPC requires a minimum of 3 parties.

        Args:
            n: Number of MPC parties (must be >= 3)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If n < 3 (validated at build time)

        Example:
            runtime = (Stoffel.compile("...")
                .parties(4)
                .threshold(1)
                .build())
        """
        self._n_parties = n
        return self

    def threshold(self, t: int) -> "Stoffel":
        """
        Set the fault tolerance threshold

        The protocol can tolerate up to t faulty parties where n >= 3t + 1.
        If not set, defaults to 1.

        Args:
            t: Fault tolerance threshold

        Returns:
            Self for method chaining
        """
        self._threshold = t
        return self

    def instance_id(self, id: int) -> "Stoffel":
        """
        Set the instance ID for this computation

        Defaults to 0 if not set.

        Args:
            id: Instance ID

        Returns:
            Self for method chaining
        """
        self._instance_id = id
        return self

    def protocol(self, protocol: ProtocolType) -> "Stoffel":
        """
        Set the MPC protocol to use

        Currently only HoneyBadger is supported. This method is provided for
        future extensibility when additional protocols are added.

        Args:
            protocol: Protocol type (ProtocolType.HONEYBADGER)

        Returns:
            Self for method chaining
        """
        self._protocol_type = protocol
        return self

    def share_type(self, share_type: ShareType) -> "Stoffel":
        """
        Set the secret sharing scheme type

        This configures which secret sharing implementation to use for MPC operations.
        By default, ShareType.ROBUST is used, which provides error correction.

        Args:
            share_type: The type of secret sharing to use

        Returns:
            Self for method chaining

        Example:
            # Use RobustShare (default - provides error correction)
            runtime = (Stoffel.compile("...")
                .parties(5)
                .share_type(ShareType.ROBUST)
                .build())

            # Use NonRobustShare (simpler, faster)
            runtime = (Stoffel.compile("...")
                .parties(5)
                .share_type(ShareType.NON_ROBUST)
                .build())
        """
        self._share_type = share_type
        return self

    def network_config_file(self, path: str) -> "Stoffel":
        """
        Load network configuration from a TOML file

        This will set MPC parameters (parties, threshold) from the config file.

        Args:
            path: Path to the TOML configuration file

        Returns:
            Self for method chaining

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        # Import here to avoid circular imports
        from .network_config import NetworkConfig

        config = NetworkConfig.from_file(path)

        # Extract MPC parameters from config if not already set
        if self._n_parties is None:
            self._n_parties = config.mpc.n_parties
        if self._threshold is None:
            self._threshold = config.mpc.threshold
        if config.mpc.instance_id is not None:
            self._instance_id = config.mpc.instance_id

        self._network_config = config.to_dict()
        return self

    def network_config(self, config: Dict[str, Any]) -> "Stoffel":
        """
        Set network configuration manually

        Args:
            config: Network configuration dictionary

        Returns:
            Self for method chaining
        """
        self._network_config = config

        # Extract MPC parameters from config
        if "mpc" in config:
            mpc = config["mpc"]
            if "n_parties" in mpc:
                self._n_parties = mpc["n_parties"]
            if "threshold" in mpc:
                self._threshold = mpc["threshold"]
            if "instance_id" in mpc:
                self._instance_id = mpc["instance_id"]

        return self

    def build(self) -> "StoffelRuntime":
        """
        Build a StoffelRuntime with MPC configuration

        Returns:
            StoffelRuntime instance

        Raises:
            ValueError: If no source, file, or bytecode provided
            ValueError: If MPC parameters are invalid (n < 3t + 1)

        Example:
            runtime = (Stoffel.compile("main main() -> int64:\\n  return 42")
                .parties(5)
                .threshold(1)
                .build())

            # Create MPC participants from the runtime
            client = runtime.client(100).with_inputs([42]).build()
            server = runtime.server(0).build()
        """
        # Get or compile bytecode
        bytecode = self._get_bytecode()

        # Validate MPC configuration if parties is set
        if self._n_parties is not None:
            # HoneyBadger MPC requires minimum 3 parties
            if self._n_parties < 3:
                raise ValueError(
                    f"HoneyBadger MPC requires at least 3 parties, got n={self._n_parties}"
                )

            threshold = self._threshold if self._threshold is not None else 1

            # Validate HoneyBadger constraint: n >= 3t + 1
            if self._n_parties < 3 * threshold + 1:
                raise ValueError(
                    f"Invalid parameters: n={self._n_parties} must be >= 3t+1={3 * threshold + 1} for t={threshold}"
                )

            return StoffelRuntime(
                bytecode=bytecode,
                n_parties=self._n_parties,
                threshold=threshold,
                instance_id=self._instance_id,
                network_config=self._network_config,
                protocol_type=self._protocol_type,
                share_type=self._share_type,
            )
        else:
            # No MPC configuration
            return StoffelRuntime(
                bytecode=bytecode,
                n_parties=None,
                threshold=None,
                instance_id=self._instance_id,
                network_config=self._network_config,
                protocol_type=self._protocol_type,
                share_type=self._share_type,
            )

    def execute_local(self) -> Any:
        """
        Compile and execute locally without building a StoffelRuntime

        This is a convenience method for testing that skips MPC configuration
        and runs the program directly on the local VM.

        Returns:
            The execution result

        Raises:
            ValueError: If no source, file, or bytecode provided
            NotImplementedError: VM bindings are not yet available

        Example:
            # Quick local test - no need for MPC config
            result = Stoffel.compile("main main() -> int64:\\n  return 42").execute_local()
        """
        # TODO: Execute via VM bindings
        # This will be implemented when we have proper PyO3 bindings
        raise NotImplementedError(
            "Local execution requires VM bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def _get_bytecode(self) -> bytes:
        """Get bytecode, compiling if necessary"""
        if self._bytecode is not None:
            return self._bytecode

        # Need to compile
        compiler = StoffelCompiler()

        if self._optimize:
            options = CompilerOptions(
                optimize=True,
                optimization_level=self._optimization_level.value
            )
        else:
            options = CompilerOptions()

        if self._source is not None:
            compiled = compiler.compile_source(self._source, options=options)
            return compiled.bytecode
        elif self._file_path is not None:
            compiled = compiler.compile_file(self._file_path, options=options)
            return compiled.bytecode
        else:
            raise ValueError("No source, file, or bytecode provided")


class StoffelRuntime:
    """
    Stoffel Runtime - manages a compiled program with MPC configuration

    This is what you get after calling .build() on a Stoffel builder.
    It contains the compiled program along with MPC infrastructure configuration,
    and provides methods to create MPC participants (clients, servers, and nodes).

    By default, the runtime uses the HoneyBadger MPC protocol.

    Note:
        HoneyBadger MPC requires a minimum of 3 parties.

    Example:
        runtime = (Stoffel.compile("main main() -> int64:\\n  return 42")
            .parties(4)
            .threshold(1)
            .build())

        # Access the program for local execution
        result = runtime.program().execute_local()

        # Create MPC participants
        client = runtime.client(100).with_inputs([42]).build()
        server = runtime.server(0).build()
    """

    def __init__(
        self,
        bytecode: bytes,
        n_parties: Optional[int],
        threshold: Optional[int],
        instance_id: int,
        network_config: Optional[Dict[str, Any]],
        protocol_type: ProtocolType,
        share_type: ShareType,
    ):
        self._bytecode = bytecode
        self._n_parties = n_parties
        self._threshold = threshold
        self._instance_id = instance_id
        self._network_config = network_config
        self._protocol_type = protocol_type
        self._share_type = share_type
        self._program: Optional["Program"] = None

    def program(self) -> "Program":
        """
        Get a reference to the underlying program

        Returns:
            Program instance
        """
        if self._program is None:
            self._program = Program(self._bytecode)
        return self._program

    def mpc_config(self) -> Optional[tuple]:
        """
        Get the MPC configuration (n_parties, threshold, instance_id)

        Returns:
            Tuple of (n_parties, threshold, instance_id) or None if not configured
        """
        if self._n_parties is not None and self._threshold is not None:
            return (self._n_parties, self._threshold, self._instance_id)
        return None

    def network_config(self) -> Optional[Dict[str, Any]]:
        """
        Get the network configuration if set

        Returns:
            Network configuration dictionary or None
        """
        return self._network_config

    def protocol_type(self) -> ProtocolType:
        """
        Get the configured MPC protocol type

        Returns:
            The protocol type (currently always ProtocolType.HONEYBADGER)
        """
        return self._protocol_type

    def share_type(self) -> ShareType:
        """
        Get the configured secret sharing scheme type

        Returns:
            The share type (default: ShareType.ROBUST)
        """
        return self._share_type

    def client(self, client_id: int) -> "MPCClientBuilder":
        """
        Create an MPC client builder

        Args:
            client_id: Unique identifier for this client

        Returns:
            MPCClientBuilder for further configuration

        Raises:
            RuntimeError: If MPC configuration is not set

        Example:
            client = runtime.client(100).with_inputs([42, 10]).build()
        """
        config = self.mpc_config()
        if config is None:
            raise RuntimeError(
                "Cannot create MPC client without MPC configuration. "
                "Use .parties(n).threshold(t) when building."
            )

        n_parties, threshold, instance_id = config

        from .mpc.client import MPCClientBuilder
        return MPCClientBuilder(
            client_id=client_id,
            n_parties=n_parties,
            threshold=threshold,
            instance_id=instance_id,
            protocol_type=self._protocol_type,
            share_type=self._share_type,
        )

    def server(self, party_id: int) -> "MPCServerBuilder":
        """
        Create an MPC server builder

        Args:
            party_id: Party ID for this server (0 to n_parties-1)

        Returns:
            MPCServerBuilder for further configuration

        Raises:
            RuntimeError: If MPC configuration is not set

        Example:
            server = runtime.server(0).with_preprocessing(10, 25).build()
        """
        config = self.mpc_config()
        if config is None:
            raise RuntimeError(
                "Cannot create MPC server without MPC configuration. "
                "Use .parties(n).threshold(t) when building."
            )

        n_parties, threshold, instance_id = config

        from .mpc.server import MPCServerBuilder
        return MPCServerBuilder(
            party_id=party_id,
            n_parties=n_parties,
            threshold=threshold,
            instance_id=instance_id,
            protocol_type=self._protocol_type,
        )

    def node(self, party_id: int) -> "MPCNodeBuilder":
        """
        Create an MPC node builder

        Nodes are for peer-to-peer scenarios where all parties both provide inputs
        and participate in computation.

        Args:
            party_id: Party ID for this node (0 to n_parties-1)

        Returns:
            MPCNodeBuilder for further configuration

        Raises:
            RuntimeError: If MPC configuration is not set

        Example:
            node = runtime.node(0).with_inputs([10, 20]).with_preprocessing(3, 8).build()
        """
        config = self.mpc_config()
        if config is None:
            raise RuntimeError(
                "Cannot create MPC node without MPC configuration. "
                "Use .parties(n).threshold(t) when building."
            )

        n_parties, threshold, instance_id = config

        from .mpc.node import MPCNodeBuilder
        return MPCNodeBuilder(
            party_id=party_id,
            n_parties=n_parties,
            threshold=threshold,
            instance_id=instance_id,
            protocol_type=self._protocol_type,
        )


class Program:
    """
    A compiled Stoffel program

    A Program is simply compiled bytecode that can be executed locally or in an MPC network.
    The Program itself doesn't contain MPC configuration - that's managed by StoffelRuntime.

    Programs can be:
    - Executed locally for testing via .execute_local()
    - Saved to disk via .save(path)
    - Used by StoffelRuntime to create MPC infrastructure (nodes and clients)
    """

    def __init__(self, bytecode: bytes):
        self._bytecode = bytecode

    def bytecode(self) -> bytes:
        """
        Get a reference to the bytecode

        Returns:
            The compiled bytecode
        """
        return self._bytecode

    def save(self, path: str) -> None:
        """
        Save the bytecode to a file

        Args:
            path: Path to save the bytecode to
        """
        with open(path, "wb") as f:
            f.write(self._bytecode)

    def execute_local(self) -> Any:
        """
        Execute the program locally on the VM for testing

        This runs the "main" function locally without MPC. Useful for testing
        program logic before setting up MPC infrastructure.

        Returns:
            The execution result

        Example:
            runtime = Stoffel.compile("main main() -> int64:\\n  return 42").build()
            program = runtime.program()
            result = program.execute_local()
        """
        return self.execute_local_function("main")

    def execute_local_function(self, function_name: str) -> Any:
        """
        Execute a specific function locally on the VM

        Args:
            function_name: Name of the function to execute

        Returns:
            The execution result
        """
        # TODO: Implement via VM bindings
        raise NotImplementedError(
            "Local execution requires VM bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def execute_local_with_args(self, function_name: str, args: List[Any]) -> Any:
        """
        Execute a function locally with arguments

        Args:
            function_name: Name of the function to execute
            args: Arguments to pass to the function

        Returns:
            The execution result
        """
        # TODO: Implement via VM bindings
        raise NotImplementedError(
            "Local execution requires VM bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def list_functions(self) -> List[Dict[str, Any]]:
        """
        List all functions in this program

        Returns:
            List of function information dictionaries
        """
        # TODO: Implement via VM bindings
        raise NotImplementedError(
            "Function listing requires VM bindings. "
            "This will be implemented when PyO3 bindings are available."
        )
