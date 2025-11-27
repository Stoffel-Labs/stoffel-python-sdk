"""
Core bindings module - provides access to native Stoffel bindings

This module provides a unified interface to native Stoffel components
using ctypes C FFI bindings to pre-built shared libraries.

The native bindings require building the Rust libraries:
    cd external/stoffel-lang && cargo build --release
    cd external/stoffel-vm && cargo build --release
    cd external/mpc-protocols && cargo build --release

Usage:
    from stoffel._core import (
        compile_source, compile_file, execute_local,
        create_shares, reconstruct_shares,
        is_native_available
    )
"""

from typing import Any, List, Optional

# Track which binding method is available
_BINDING_METHOD: Optional[str] = None

# =============================================================================
# Try ctypes C FFI bindings
# =============================================================================
_NativeCompiler = None
_NativeVM = None
_NativeShareManager = None

try:
    from stoffel.native.compiler import NativeCompiler as _NativeCompiler
    from stoffel.native.vm import NativeVM as _NativeVM
    from stoffel.native.mpc import NativeShareManager as _NativeShareManager
    _BINDING_METHOD = "ctypes"
except ImportError:
    pass


def is_native_available() -> bool:
    """Check if native bindings are available (ctypes)"""
    return _BINDING_METHOD is not None


def get_binding_method() -> Optional[str]:
    """Get the current binding method ('ctypes' or None)"""
    return _BINDING_METHOD


# =============================================================================
# Unified API Functions
# =============================================================================

def compile_source(source: str, optimize: bool = False) -> bytes:
    """
    Compile Stoffel source code to bytecode

    Args:
        source: Stoffel source code as a string
        optimize: Whether to enable optimizations

    Returns:
        Compiled bytecode as bytes

    Raises:
        NotImplementedError: If no native bindings are available
        RuntimeError: If compilation fails
    """
    if _BINDING_METHOD == "ctypes" and _NativeCompiler is not None:
        try:
            from stoffel.native.compiler import CompilerOptions
            compiler = _NativeCompiler()
            options = CompilerOptions(optimize=optimize)
            return compiler.compile(source, options=options)
        except RuntimeError as e:
            raise RuntimeError(f"Compilation failed: {e}")

    raise NotImplementedError(
        "Native compilation requires ctypes bindings. "
        "Build shared libraries with 'cargo build --release' in external/stoffel-lang."
    )


def compile_file(path: str, optimize: bool = False) -> bytes:
    """
    Compile a Stoffel file to bytecode

    Args:
        path: Path to the .stfl source file
        optimize: Whether to enable optimizations

    Returns:
        Compiled bytecode as bytes

    Raises:
        NotImplementedError: If no native bindings are available
        RuntimeError: If compilation fails
    """
    if _BINDING_METHOD == "ctypes" and _NativeCompiler is not None:
        try:
            from stoffel.native.compiler import CompilerOptions
            compiler = _NativeCompiler()
            options = CompilerOptions(optimize=optimize)
            return compiler.compile_file(path, options=options)
        except RuntimeError as e:
            raise RuntimeError(f"Compilation failed: {e}")

    raise NotImplementedError(
        "Native compilation requires ctypes bindings. "
        "Build shared libraries with 'cargo build --release' in external/stoffel-lang."
    )


def execute_local(
    bytecode: bytes,
    function_name: str = "main",
    args: Optional[List[Any]] = None,
) -> Any:
    """
    Execute bytecode locally on the VM

    Args:
        bytecode: Compiled bytecode
        function_name: Name of the function to execute
        args: Optional list of arguments

    Returns:
        Execution result

    Raises:
        NotImplementedError: If no native bindings are available
        RuntimeError: If execution fails
    """
    if _BINDING_METHOD == "ctypes" and _NativeVM is not None:
        try:
            vm = _NativeVM()
            # Note: ctypes VM needs bytecode loading which requires more work
            # For now, raise NotImplementedError
            raise NotImplementedError(
                "ctypes VM execution not yet fully implemented. "
                "The VM C FFI needs to be exported in stoffel-vm (add 'pub mod cffi;' to lib.rs)."
            )
        except RuntimeError as e:
            raise RuntimeError(f"Execution failed: {e}")

    raise NotImplementedError(
        "Native VM execution requires ctypes bindings. "
        "Build shared libraries with 'cargo build --release' in external/stoffel-vm."
    )


def create_shares(
    value: int,
    n_parties: int,
    threshold: int,
    robust: bool = True,
) -> List[bytes]:
    """
    Create secret shares for a value

    Args:
        value: The secret value to share
        n_parties: Total number of parties
        threshold: Reconstruction threshold
        robust: Whether to use robust shares

    Returns:
        List of share bytes, one for each party

    Raises:
        NotImplementedError: If no native bindings are available
        ValueError: If parameters are invalid
    """
    if _BINDING_METHOD == "ctypes" and _NativeShareManager is not None:
        try:
            manager = _NativeShareManager(n_parties, threshold, robust)
            shares = manager.create_shares(value)
            return [share.share_bytes for share in shares]
        except Exception as e:
            raise ValueError(f"Failed to create shares: {e}")

    raise NotImplementedError(
        "Native secret sharing requires ctypes bindings. "
        "Build shared libraries with 'cargo build --release' in external/mpc-protocols."
    )


def reconstruct_shares(
    shares: List[bytes],
    n_parties: int,
    threshold: int,
    robust: bool = True,
) -> int:
    """
    Reconstruct a secret from shares

    Args:
        shares: List of share bytes
        n_parties: Total number of parties
        threshold: Reconstruction threshold
        robust: Whether shares are robust shares

    Returns:
        Reconstructed secret value

    Raises:
        NotImplementedError: If no native bindings are available
        ValueError: If reconstruction fails
    """
    if _BINDING_METHOD == "ctypes" and _NativeShareManager is not None:
        try:
            from stoffel.native.mpc import Share, ShareType
            manager = _NativeShareManager(n_parties, threshold, robust)

            # Convert bytes to Share objects
            share_type = ShareType.ROBUST if robust else ShareType.NON_ROBUST
            share_objs = []
            for i, share_bytes in enumerate(shares):
                share_objs.append(Share(
                    share_bytes=share_bytes,
                    party_id=i,
                    threshold=threshold,
                    share_type=share_type,
                ))

            return manager.reconstruct(share_objs)
        except Exception as e:
            raise ValueError(f"Failed to reconstruct shares: {e}")

    raise NotImplementedError(
        "Native secret reconstruction requires ctypes bindings. "
        "Build shared libraries with 'cargo build --release' in external/mpc-protocols."
    )


# =============================================================================
# Class Wrappers
# =============================================================================

class VM:
    """
    Virtual Machine for executing Stoffel bytecode

    This class wraps the native Stoffel VM when available.
    """

    def __init__(self):
        self._native = None
        self._bytecode = None

        if _BINDING_METHOD == "ctypes" and _NativeVM is not None:
            try:
                self._native = _NativeVM()
            except RuntimeError:
                pass

    def load(self, bytecode: bytes) -> None:
        """Load bytecode into the VM"""
        self._bytecode = bytecode
        if self._native is not None and hasattr(self._native, "load"):
            self._native.load(bytecode)

    def execute(
        self,
        function_name: str = "main",
        args: Optional[List[Any]] = None,
    ) -> Any:
        """Execute a function"""
        if self._native is not None and hasattr(self._native, "execute"):
            if args:
                return self._native.execute_with_args(function_name, args)
            return self._native.execute(function_name)

        raise NotImplementedError(
            "Native VM execution requires ctypes bindings with VM C FFI exported. "
            "Add 'pub mod cffi;' to stoffel-vm/crates/stoffel-vm/src/lib.rs and rebuild."
        )


class Compiler:
    """
    Compiler for Stoffel source code

    This class wraps the native Stoffel compiler when available.
    """

    def __init__(self, optimize: bool = False):
        self._optimize = optimize
        self._native = None

        if _BINDING_METHOD == "ctypes" and _NativeCompiler is not None:
            try:
                self._native = _NativeCompiler()
            except RuntimeError:
                pass

    def compile(self, source: str) -> bytes:
        """Compile source code to bytecode"""
        if self._native is not None:
            from stoffel.native.compiler import CompilerOptions
            options = CompilerOptions(optimize=self._optimize)
            return self._native.compile(source, options=options)

        return compile_source(source, self._optimize)

    def compile_file(self, path: str) -> bytes:
        """Compile a file to bytecode"""
        if self._native is not None:
            from stoffel.native.compiler import CompilerOptions
            options = CompilerOptions(optimize=self._optimize)
            return self._native.compile_file(path, options=options)

        return compile_file(path, self._optimize)


class NativeShareManager:
    """
    Native ShareManager wrapper for secret sharing operations

    This class wraps the native ShareManager when available.
    """

    def __init__(self, n_parties: int, threshold: int, robust: bool = True):
        # Validate parameters
        if n_parties < 3:
            raise ValueError(
                f"HoneyBadger MPC requires at least 3 parties, got n={n_parties}"
            )
        if n_parties < 3 * threshold + 1:
            raise ValueError(
                f"Invalid parameters: n={n_parties} must be >= 3t+1={3 * threshold + 1} for t={threshold}"
            )

        self._n_parties = n_parties
        self._threshold = threshold
        self._robust = robust
        self._native = None

        if _BINDING_METHOD == "ctypes" and _NativeShareManager is not None:
            try:
                from stoffel.native.mpc import NativeShareManager as _NativeMPC
                self._native = _NativeMPC(n_parties, threshold, robust)
            except RuntimeError:
                pass

    @property
    def n_parties(self) -> int:
        return self._n_parties

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def robust(self) -> bool:
        return self._robust

    def create_shares(self, value: int) -> List[bytes]:
        """Create shares for a secret value"""
        if self._native is not None:
            shares = self._native.create_shares(value)
            return [share.share_bytes for share in shares]

        return create_shares(value, self._n_parties, self._threshold, self._robust)

    def reconstruct(self, shares: List[bytes]) -> int:
        """Reconstruct a secret from shares"""
        if self._native is not None:
            from stoffel.native.mpc import Share, ShareType
            share_type = ShareType.ROBUST if self._robust else ShareType.NON_ROBUST
            share_objs = []
            for i, share_bytes in enumerate(shares):
                share_objs.append(Share(
                    share_bytes=share_bytes,
                    party_id=i,
                    threshold=self._threshold,
                    share_type=share_type,
                ))
            return self._native.reconstruct(share_objs)

        return reconstruct_shares(shares, self._n_parties, self._threshold, self._robust)
