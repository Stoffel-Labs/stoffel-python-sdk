"""
Stoffel SDK Entry Point

Main entry point for the Stoffel SDK, providing a fluent builder API
for compiling StoffelLang programs and configuring MPC parameters.

Example:
    from stoffel import Stoffel, ProtocolType, ShareType

    # Compile and configure MPC
    runtime = Stoffel.compile("fn main() { return 42; }") \
        .parties(5) \
        .threshold(1) \
        .protocol(ProtocolType.HONEYBADGER) \
        .build()

    # Access program and config
    print(runtime.program)       # bytes
    print(runtime.mpc_config)    # MPCConfig

    # Quick local execution
    result = Stoffel.compile(source).execute_local()
"""

from typing import Any, Optional, Union
from pathlib import Path

from .enums import ProtocolType, ShareType, OptimizationLevel
from .error import (
    CompilationError,
    ConfigurationError,
    IoError,
    StoffelRuntimeError,
)
from .runtime import StoffelRuntime, MPCConfig
from .compiler.compiler import StoffelCompiler, CompilerOptions
from .compiler.exceptions import CompilationError as CompilerCompilationError


class Stoffel:
    """
    Main entry point for Stoffel SDK

    Provides static methods for compiling StoffelLang source code
    and loading pre-compiled bytecode. All methods return a
    StoffelBuilder for fluent configuration.

    Example:
        # From source code
        builder = Stoffel.compile("fn main() { return 42; }")

        # From file
        builder = Stoffel.compile_file("program.stfl")

        # From pre-compiled bytecode
        builder = Stoffel.load(bytecode)
    """

    @staticmethod
    def compile(source: str, filename: str = "main.stfl") -> "StoffelBuilder":
        """
        Compile StoffelLang source code

        Args:
            source: StoffelLang source code
            filename: Optional filename for error messages

        Returns:
            StoffelBuilder for further configuration

        Raises:
            CompilationError: If compilation fails
        """
        return StoffelBuilder._from_source(source, filename)

    @staticmethod
    def compile_file(path: str) -> "StoffelBuilder":
        """
        Compile StoffelLang source from file

        Args:
            path: Path to .stfl source file

        Returns:
            StoffelBuilder for further configuration

        Raises:
            CompilationError: If compilation fails
            IoError: If file cannot be read
        """
        return StoffelBuilder._from_file(path)

    @staticmethod
    def load(bytecode: bytes) -> "StoffelBuilder":
        """
        Load pre-compiled bytecode

        Args:
            bytecode: Compiled program bytecode (.stfb content)

        Returns:
            StoffelBuilder for further configuration
        """
        return StoffelBuilder._from_bytecode(bytecode)

    @staticmethod
    def load_file(path: str) -> "StoffelBuilder":
        """
        Load pre-compiled bytecode from file

        Args:
            path: Path to .stfb bytecode file

        Returns:
            StoffelBuilder for further configuration

        Raises:
            IoError: If file cannot be read
        """
        return StoffelBuilder._from_bytecode_file(path)


class StoffelBuilder:
    """
    Fluent builder for configuring Stoffel programs and MPC parameters

    This builder allows chained configuration of:
    - MPC party count and threshold
    - Instance ID for computation isolation
    - Protocol and share type selection
    - Compilation optimization level

    Example:
        runtime = Stoffel.compile(source) \
            .parties(5) \
            .threshold(1) \
            .instance_id(123) \
            .protocol(ProtocolType.HONEYBADGER) \
            .share_type(ShareType.ROBUST) \
            .build()
    """

    def __init__(self):
        """Initialize builder with default values"""
        self._program: Optional[bytes] = None
        self._source: Optional[str] = None
        self._source_filename: str = "main.stfl"
        self._source_path: Optional[str] = None
        self._parties: int = 5  # Default
        self._threshold: int = 1  # Default
        self._instance_id: int = 0
        self._protocol_type: ProtocolType = ProtocolType.HONEYBADGER
        self._share_type: ShareType = ShareType.ROBUST
        self._optimization_level: OptimizationLevel = OptimizationLevel.NONE
        self._compiled: bool = False

    @classmethod
    def _from_source(cls, source: str, filename: str = "main.stfl") -> "StoffelBuilder":
        """Create builder from source code (internal)"""
        builder = cls()
        builder._source = source
        builder._source_filename = filename
        return builder

    @classmethod
    def _from_file(cls, path: str) -> "StoffelBuilder":
        """Create builder from source file (internal)"""
        if not Path(path).exists():
            raise IoError(f"Source file not found: {path}")
        builder = cls()
        builder._source_path = path
        return builder

    @classmethod
    def _from_bytecode(cls, bytecode: bytes) -> "StoffelBuilder":
        """Create builder from bytecode (internal)"""
        builder = cls()
        builder._program = bytecode
        builder._compiled = True
        return builder

    @classmethod
    def _from_bytecode_file(cls, path: str) -> "StoffelBuilder":
        """Create builder from bytecode file (internal)"""
        try:
            bytecode = Path(path).read_bytes()
        except Exception as e:
            raise IoError(f"Failed to read bytecode file: {path}", cause=e)
        return cls._from_bytecode(bytecode)

    def parties(self, n: int) -> "StoffelBuilder":
        """
        Set number of MPC parties

        Args:
            n: Number of parties (must be >= 1)

        Returns:
            Self for chaining
        """
        if n < 1:
            raise ConfigurationError("parties must be at least 1")
        self._parties = n
        return self

    def threshold(self, t: int) -> "StoffelBuilder":
        """
        Set Byzantine fault tolerance threshold

        The threshold determines how many malicious parties can be
        tolerated. For HoneyBadger, n >= 3t + 1 must hold.

        Args:
            t: Fault tolerance threshold (must be >= 0)

        Returns:
            Self for chaining
        """
        if t < 0:
            raise ConfigurationError("threshold cannot be negative")
        self._threshold = t
        return self

    def instance_id(self, id: int) -> "StoffelBuilder":
        """
        Set computation instance ID

        Instance IDs isolate computations, ensuring different
        MPC executions don't interfere with each other.

        Args:
            id: Instance ID (must be >= 0)

        Returns:
            Self for chaining
        """
        if id < 0:
            raise ConfigurationError("instance_id cannot be negative")
        self._instance_id = id
        return self

    def protocol(self, protocol: ProtocolType) -> "StoffelBuilder":
        """
        Set MPC protocol type

        Args:
            protocol: Protocol to use (currently only HONEYBADGER)

        Returns:
            Self for chaining
        """
        self._protocol_type = protocol
        return self

    def share_type(self, share_type: ShareType) -> "StoffelBuilder":
        """
        Set secret sharing scheme

        Args:
            share_type: Share type (ROBUST or NON_ROBUST)

        Returns:
            Self for chaining
        """
        self._share_type = share_type
        return self

    def optimize(self, level: Union[int, OptimizationLevel] = OptimizationLevel.O1) -> "StoffelBuilder":
        """
        Enable compilation optimization

        Args:
            level: Optimization level (0-3 or OptimizationLevel enum)

        Returns:
            Self for chaining
        """
        if isinstance(level, int):
            if level < 0 or level > 3:
                raise ConfigurationError(f"Invalid optimization level: {level} (must be 0-3)")
            level = OptimizationLevel(level)
        self._optimization_level = level
        return self

    def _validate_config(self) -> None:
        """Validate MPC configuration constraints"""
        # HoneyBadger requires n >= 3t + 1
        if self._protocol_type == ProtocolType.HONEYBADGER:
            min_parties = 3 * self._threshold + 1
            if self._parties < min_parties:
                raise ConfigurationError(
                    f"HoneyBadger requires n >= 3t + 1: "
                    f"got n={self._parties}, t={self._threshold} "
                    f"(need at least {min_parties} parties)"
                )

        # Robust shares required for HoneyBadger
        if self._protocol_type == ProtocolType.HONEYBADGER and self._share_type == ShareType.NON_ROBUST:
            raise ConfigurationError(
                "HoneyBadger protocol requires ROBUST share type for error correction"
            )

    def _compile_program(self) -> bytes:
        """Compile source to bytecode"""
        if self._compiled and self._program is not None:
            return self._program

        try:
            compiler = StoffelCompiler()
            options = CompilerOptions(
                optimization_level=int(self._optimization_level)
            )

            if self._source is not None:
                program = compiler.compile_source(
                    self._source,
                    filename=self._source_filename,
                    options=options
                )
            elif self._source_path is not None:
                program = compiler.compile_file(
                    self._source_path,
                    options=options
                )
            else:
                raise CompilationError("No source or bytecode provided")

            # Extract bytecode from CompiledProgram
            # The program.binary_path contains the path to the .stfb file
            bytecode = Path(program.binary_path).read_bytes()
            self._program = bytecode
            self._compiled = True
            return bytecode

        except CompilerCompilationError as e:
            raise CompilationError(str(e), cause=e)
        except Exception as e:
            raise CompilationError(f"Compilation failed: {e}", cause=e)

    def build(self) -> StoffelRuntime:
        """
        Build the StoffelRuntime

        Compiles the program (if needed), validates MPC configuration,
        and creates the runtime.

        Returns:
            StoffelRuntime containing program and MPC config

        Raises:
            CompilationError: If compilation fails
            ConfigurationError: If MPC parameters are invalid
        """
        # Validate configuration first
        self._validate_config()

        # Compile if needed
        program = self._compile_program()

        # Create config
        config = MPCConfig(
            parties=self._parties,
            threshold=self._threshold,
            instance_id=self._instance_id,
            protocol_type=self._protocol_type,
            share_type=self._share_type,
        )

        return StoffelRuntime(program, config)

    def execute_local(self, function_name: str = "main", *args: Any) -> Any:
        """
        Quick local execution (non-MPC)

        Compiles and executes the program locally using the VM
        without MPC. Useful for testing and development.

        Args:
            function_name: Function to execute (default: "main")
            *args: Arguments to pass to the function

        Returns:
            Result of the function execution

        Raises:
            CompilationError: If compilation fails
            StoffelRuntimeError: If execution fails
        """
        try:
            # Try using native VM FFI first
            from .native import is_vm_available, VirtualMachine as NativeVM

            if is_vm_available():
                program = self._compile_program()
                vm = NativeVM()
                vm.load_bytecode(program)
                if args:
                    return vm.execute_with_args(function_name, list(args))
                else:
                    return vm.execute(function_name)

        except ImportError:
            pass
        except Exception as e:
            # Fall through to compiler-based approach
            pass

        # Fallback: Use the compiler's CompiledProgram
        try:
            compiler = StoffelCompiler()
            options = CompilerOptions(
                optimization_level=int(self._optimization_level)
            )

            if self._source is not None:
                program = compiler.compile_source(
                    self._source,
                    filename=self._source_filename,
                    options=options
                )
            elif self._source_path is not None:
                program = compiler.compile_file(
                    self._source_path,
                    options=options
                )
            elif self._program is not None:
                # Need to write bytecode to temp file and load
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.stfb', delete=False) as f:
                    f.write(self._program)
                    temp_path = f.name
                try:
                    from .compiler.program import CompiledProgram
                    program = CompiledProgram.load_from_file(temp_path)
                finally:
                    Path(temp_path).unlink(missing_ok=True)
            else:
                raise CompilationError("No source or bytecode provided")

            if args:
                return program.execute_function(function_name, *args)
            else:
                return program.execute_function(function_name)

        except Exception as e:
            raise StoffelRuntimeError(f"Local execution failed: {e}", cause=e)
