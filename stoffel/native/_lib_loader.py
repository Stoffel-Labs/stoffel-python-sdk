"""
Centralized library loading for Stoffel native FFI bindings

Handles platform-specific library names and search paths for:
- libstoffelmpc_mpc: MPC protocols (HoneyBadger, secret sharing, QUIC)
- libstoffel_vm: Virtual machine
- libstoffellang: Compiler
"""

import ctypes
import os
import platform
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LibraryLoadError(Exception):
    """Raised when a native library cannot be loaded"""
    pass


# Cached library instances
_mpc_library: Optional[ctypes.CDLL] = None
_vm_library: Optional[ctypes.CDLL] = None
_compiler_library: Optional[ctypes.CDLL] = None


def _get_lib_extension() -> str:
    """Get the platform-specific shared library extension"""
    system = platform.system()
    if system == "Darwin":
        return ".dylib"
    elif system == "Windows":
        return ".dll"
    else:
        return ".so"


def _get_lib_prefix() -> str:
    """Get the platform-specific library prefix"""
    system = platform.system()
    if system == "Windows":
        return ""
    return "lib"


def _get_search_paths() -> list:
    """Get list of paths to search for native libraries"""
    paths = []

    # Current working directory
    paths.append(Path.cwd())

    # SDK directory relative paths (for development)
    sdk_dir = Path(__file__).parent.parent.parent
    paths.extend([
        sdk_dir / "external" / "mpc-protocols" / "target" / "release",
        sdk_dir / "external" / "mpc-protocols" / "target" / "debug",
        sdk_dir / "external" / "stoffel-vm" / "target" / "release",
        sdk_dir / "external" / "stoffel-vm" / "target" / "debug",
        sdk_dir / "external" / "stoffel-lang" / "target" / "release",
        sdk_dir / "external" / "stoffel-lang" / "target" / "debug",
    ])

    # Monorepo paths (relative to Stoffel-Dev)
    stoffel_dev = sdk_dir.parent.parent
    paths.extend([
        stoffel_dev / "mpc-protocols" / "target" / "release",
        stoffel_dev / "mpc-protocols" / "target" / "debug",
        stoffel_dev / "StoffelVM" / "target" / "release",
        stoffel_dev / "StoffelVM" / "target" / "debug",
        stoffel_dev / "Stoffel-Lang" / "target" / "release",
        stoffel_dev / "Stoffel-Lang" / "target" / "debug",
    ])

    # System paths
    paths.extend([
        Path("/usr/local/lib"),
        Path("/usr/lib"),
    ])

    # Environment variable paths
    if "LD_LIBRARY_PATH" in os.environ:
        for p in os.environ["LD_LIBRARY_PATH"].split(":"):
            paths.append(Path(p))

    if "DYLD_LIBRARY_PATH" in os.environ:
        for p in os.environ["DYLD_LIBRARY_PATH"].split(":"):
            paths.append(Path(p))

    return paths


def _find_library(lib_names: list) -> Optional[Path]:
    """Find a library file in search paths"""
    ext = _get_lib_extension()
    prefix = _get_lib_prefix()

    for path in _get_search_paths():
        for name in lib_names:
            full_name = f"{prefix}{name}{ext}"
            full_path = path / full_name
            if full_path.exists():
                logger.debug(f"Found library: {full_path}")
                return full_path

    return None


def _load_library(lib_names: list, friendly_name: str) -> ctypes.CDLL:
    """Load a shared library by name"""
    # First try to find in search paths
    lib_path = _find_library(lib_names)

    if lib_path:
        try:
            return ctypes.CDLL(str(lib_path))
        except OSError as e:
            logger.warning(f"Found {lib_path} but failed to load: {e}")

    # Try loading by name directly (relies on system library path)
    ext = _get_lib_extension()
    prefix = _get_lib_prefix()

    for name in lib_names:
        full_name = f"{prefix}{name}{ext}"
        try:
            return ctypes.CDLL(full_name)
        except OSError:
            continue

    # Build helpful error message
    search_paths_str = "\n  ".join(str(p) for p in _get_search_paths()[:10])
    raise LibraryLoadError(
        f"Could not find {friendly_name} library.\n"
        f"Tried names: {lib_names}\n"
        f"Search paths:\n  {search_paths_str}\n\n"
        f"To build the library:\n"
        f"  cd mpc-protocols && cargo build --release"
    )


def get_mpc_library() -> ctypes.CDLL:
    """
    Get the MPC protocols library (libstoffelmpc_mpc)

    This library provides:
    - HoneyBadger MPC client/node operations
    - Secret sharing (Shamir, Robust, NonRobust)
    - QUIC networking
    - RBC protocols (Bracha, AVID, ABA)

    Returns:
        Loaded ctypes.CDLL instance

    Raises:
        LibraryLoadError: If library cannot be found or loaded
    """
    global _mpc_library

    if _mpc_library is None:
        _mpc_library = _load_library(
            ["stoffelmpc_mpc", "mpc_protocols", "stoffelmpc-mpc"],
            "MPC protocols"
        )
        logger.info("Loaded MPC protocols library")

    return _mpc_library


def get_vm_library() -> ctypes.CDLL:
    """
    Get the StoffelVM library (libstoffel_vm)

    This library provides:
    - VM creation and lifecycle
    - Bytecode loading and execution
    - Foreign function registration

    Returns:
        Loaded ctypes.CDLL instance

    Raises:
        LibraryLoadError: If library cannot be found or loaded
    """
    global _vm_library

    if _vm_library is None:
        _vm_library = _load_library(
            ["stoffel_vm", "stoffel-vm"],
            "StoffelVM"
        )
        logger.info("Loaded StoffelVM library")

    return _vm_library


def get_compiler_library() -> ctypes.CDLL:
    """
    Get the StoffelLang compiler library (libstoffellang)

    This library provides:
    - Source code compilation
    - Bytecode generation
    - IR printing and optimization

    Returns:
        Loaded ctypes.CDLL instance

    Raises:
        LibraryLoadError: If library cannot be found or loaded
    """
    global _compiler_library

    if _compiler_library is None:
        _compiler_library = _load_library(
            ["stoffellang", "stoffel_lang", "stoffel-lang"],
            "StoffelLang compiler"
        )
        logger.info("Loaded StoffelLang compiler library")

    return _compiler_library


def is_native_available() -> bool:
    """
    Check if native libraries are available

    Returns:
        True if at least the MPC library can be loaded
    """
    try:
        get_mpc_library()
        return True
    except LibraryLoadError:
        return False


def get_available_libraries() -> dict:
    """
    Get status of all native libraries

    Returns:
        Dictionary with library names and their availability status
    """
    status = {}

    try:
        get_mpc_library()
        status["mpc_protocols"] = True
    except LibraryLoadError:
        status["mpc_protocols"] = False

    try:
        get_vm_library()
        status["stoffel_vm"] = True
    except LibraryLoadError:
        status["stoffel_vm"] = False

    try:
        get_compiler_library()
        status["stoffellang"] = True
    except LibraryLoadError:
        status["stoffellang"] = False

    return status
