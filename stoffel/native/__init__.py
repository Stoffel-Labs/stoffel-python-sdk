"""
Native FFI bindings for Stoffel MPC operations

This module provides ctypes-based bindings to the Stoffel native libraries:
- libstoffelmpc_mpc: MPC protocols (HoneyBadger, secret sharing, QUIC networking)
- libstoffel_vm: Virtual machine execution
- libstoffellang: StoffelLang compiler

Usage:
    from stoffel.native import is_native_available, get_mpc_library

    if is_native_available():
        lib = get_mpc_library()
        # Use FFI functions...
"""

from ._lib_loader import (
    is_native_available,
    get_mpc_library,
    get_vm_library,
    get_compiler_library,
    LibraryLoadError,
)

from .types import (
    U256,
    ByteSlice,
    UsizeSlice,
    U256Slice,
    ShamirShare,
    ShamirShareSlice,
    RobustShare,
    RobustShareSlice,
    NonRobustShare,
    NonRobustShareSlice,
    QuicNetworkOpaque,
    QuicPeerConnectionsOpaque,
    NetworkOpaque,
    HoneyBadgerMPCClientOpaque,
    FieldKind,
    Share,
)

from .errors import (
    FFIError,
    NetworkError,
    HoneyBadgerError,
    ShareError,
    NetworkErrorCode,
    HoneyBadgerErrorCode,
    ShareErrorCode,
    check_network_error,
    check_hb_error,
    check_share_error,
)

from .quic_ffi import get_quic_ffi, is_quic_available
from .network import QUICNetwork, QUICConnection
from .hb_client_ffi import get_hb_client_ffi, is_hb_client_available
from .share_ffi import get_share_ffi, is_share_available
from .vm_ffi import (
    get_vm_ffi,
    is_vm_available,
    VirtualMachine,
    StoffelValue,
    StoffelValueType,
    VMError,
)
from .compiler_ffi import (
    get_compiler_ffi,
    is_compiler_available,
    StoffelCompiler,
    CompilerOptions,
    CompilerError,
    CompilationError,
)

# Native implementations (from PRs #3 and #4)
from .vm import NativeVM
from .compiler import NativeCompiler
from .mpc import NativeShareManager, ShareType as NativeShareType, FieldKind as NativeFieldKind

# HoneyBadger MPC Engine FFI (STO-356)
from .hb_engine_ffi import (
    HBEngineFFI,
    HBEngineErrorCode,
    HBEngineError,
    HoneyBadgerMpcEngine,
    ShareTypeKind,
    get_hb_engine_ffi,
    is_hb_engine_available,
)

# Stoffel Networking FFI
from .network_ffi import (
    NetworkFFI,
    StoffelNetError,
    ConnectionState,
    NetworkError,
    TokioRuntime,
    NetworkNode,
    NetworkManager,
    PeerConnection,
    get_network_ffi,
    is_network_available,
)

__all__ = [
    # Library loading
    "is_native_available",
    "get_mpc_library",
    "get_vm_library",
    "get_compiler_library",
    "LibraryLoadError",

    # Types
    "U256",
    "ByteSlice",
    "UsizeSlice",
    "U256Slice",
    "ShamirShare",
    "ShamirShareSlice",
    "RobustShare",
    "RobustShareSlice",
    "NonRobustShare",
    "NonRobustShareSlice",
    "QuicNetworkOpaque",
    "QuicPeerConnectionsOpaque",
    "NetworkOpaque",
    "HoneyBadgerMPCClientOpaque",
    "FieldKind",
    "Share",

    # Errors
    "FFIError",
    "NetworkError",
    "HoneyBadgerError",
    "ShareError",
    "NetworkErrorCode",
    "HoneyBadgerErrorCode",
    "ShareErrorCode",
    "check_network_error",
    "check_hb_error",
    "check_share_error",

    # QUIC Network
    "get_quic_ffi",
    "is_quic_available",
    "QUICNetwork",
    "QUICConnection",

    # HoneyBadger Client
    "get_hb_client_ffi",
    "is_hb_client_available",

    # Secret Sharing
    "get_share_ffi",
    "is_share_available",

    # StoffelVM
    "get_vm_ffi",
    "is_vm_available",
    "VirtualMachine",
    "StoffelValue",
    "StoffelValueType",
    "VMError",

    # Stoffel-Lang Compiler
    "get_compiler_ffi",
    "is_compiler_available",
    "StoffelCompiler",
    "CompilerOptions",
    "CompilerError",
    "CompilationError",

    # Native implementations (from PRs #3 and #4)
    "NativeVM",
    "NativeCompiler",
    "NativeShareManager",
    "NativeShareType",
    "NativeFieldKind",

    # HoneyBadger MPC Engine (STO-356)
    "HBEngineFFI",
    "HBEngineErrorCode",
    "HBEngineError",
    "HoneyBadgerMpcEngine",
    "ShareTypeKind",
    "get_hb_engine_ffi",
    "is_hb_engine_available",

    # Stoffel Networking
    "NetworkFFI",
    "StoffelNetError",
    "ConnectionState",
    "NetworkError",
    "TokioRuntime",
    "NetworkNode",
    "NetworkManager",
    "PeerConnection",
    "get_network_ffi",
    "is_network_available",
]
