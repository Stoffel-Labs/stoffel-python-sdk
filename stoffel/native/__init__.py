"""
Native bindings for Stoffel components using ctypes

This module provides Python bindings to the Stoffel C FFI:
- stoffel-lang: Compiler (stoffellang.h)
- stoffel-vm: Virtual Machine (stoffel_vm.h) - requires cffi module export
- mpc-protocols: Secret sharing (mpc FFI)

Note: The VM bindings require the 'cffi' module to be exported in
stoffel-vm/crates/stoffel-vm/src/lib.rs. Without this, only compiler
and MPC bindings are available.
"""

from .compiler import NativeCompiler, CompilerOptions as NativeCompilerOptions
from .vm import NativeVM, VMError, ExecutionError, VMFFINotAvailable, is_vm_ffi_available
from .mpc import NativeShareManager, ShareError, ShareType

__all__ = [
    "NativeCompiler",
    "NativeCompilerOptions",
    "NativeVM",
    "VMError",
    "ExecutionError",
    "VMFFINotAvailable",
    "is_vm_ffi_available",
    "NativeShareManager",
    "ShareError",
    "ShareType",
]
