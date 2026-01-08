"""
Stoffel-Lang Compiler FFI bindings

Raw ctypes bindings for StoffelLang compilation.
Based on: Stoffel-Lang/src/ffi.rs

This module provides:
- Source code compilation
- Direct-to-binary compilation (for VM loading)
- Compiler options configuration
- Error handling for compilation failures
"""

import ctypes
from ctypes import (
    POINTER, Structure, Union,
    c_void_p, c_char_p, c_int, c_int8, c_int16, c_int32, c_int64,
    c_uint8, c_uint16, c_uint32, c_uint64, c_size_t
)
from enum import IntEnum
from typing import Optional, List, NamedTuple
from dataclasses import dataclass

from ._lib_loader import get_compiler_library, LibraryLoadError


# ==============================================================================
# Type Definitions
# ==============================================================================

class CCompilerOptions(Structure):
    """Compiler options structure

    Must match: Stoffel-Lang/src/ffi.rs CCompilerOptions struct
    """
    _fields_ = [
        ("optimize", c_int),           # Whether to optimize (0 or 1)
        ("optimization_level", c_uint8),  # 0-3
        ("print_ir", c_int),           # Whether to print IR (0 or 1)
    ]


class CCompilerError(Structure):
    """Single compiler error

    Must match: Stoffel-Lang/src/ffi.rs CCompilerError struct
    """
    _fields_ = [
        ("message", c_char_p),
        ("file", c_char_p),
        ("line", c_size_t),
        ("column", c_size_t),
        ("severity", c_int),    # 0=Warning, 1=Error, 2=Fatal
        ("category", c_int),    # 0=Syntax, 1=Type, 2=Semantic, 3=Internal
        ("code", c_char_p),
        ("hint", c_char_p),
    ]


class CCompilerErrors(Structure):
    """List of compiler errors

    Must match: Stoffel-Lang/src/ffi.rs CCompilerErrors struct
    """
    _fields_ = [
        ("errors", POINTER(CCompilerError)),
        ("count", c_size_t),
    ]


class CConstantData(Union):
    """Union to hold constant data

    Must match: Stoffel-Lang/src/ffi.rs CConstantData union
    """
    _fields_ = [
        ("i64_val", c_int64),
        ("i32_val", c_int32),
        ("i16_val", c_int16),
        ("i8_val", c_int8),
        ("u64_val", c_uint64),
        ("u32_val", c_uint32),
        ("u16_val", c_uint16),
        ("u8_val", c_uint8),
        ("float_val", c_int64),
        ("bool_val", c_int),
        ("string_val", c_char_p),
        ("object_val", c_size_t),
        ("array_val", c_size_t),
        ("foreign_val", c_size_t),
    ]


class CConstant(Structure):
    """Constant value

    Must match: Stoffel-Lang/src/ffi.rs CConstant struct
    """
    _fields_ = [
        ("const_type", c_int),
        ("data", CConstantData),
    ]


class CInstruction(Structure):
    """Single VM instruction

    Must match: Stoffel-Lang/src/ffi.rs CInstruction struct
    """
    _fields_ = [
        ("opcode", c_uint8),
        ("operand1", c_size_t),
        ("operand2", c_size_t),
        ("operand3", c_size_t),
    ]


class CBytecodeChunk(Structure):
    """Bytecode chunk containing instructions and constants

    Must match: Stoffel-Lang/src/ffi.rs CBytecodeChunk struct
    """
    _fields_ = [
        ("instructions", POINTER(CInstruction)),
        ("instruction_count", c_size_t),
        ("constants", POINTER(CConstant)),
        ("constant_count", c_size_t),
    ]


class CFunctionChunk(Structure):
    """Named function chunk

    Must match: Stoffel-Lang/src/ffi.rs CFunctionChunk struct
    """
    _fields_ = [
        ("name", c_char_p),
        ("chunk", CBytecodeChunk),
    ]


class CCompiledProgram(Structure):
    """Complete compiled program

    Must match: Stoffel-Lang/src/ffi.rs CCompiledProgram struct
    """
    _fields_ = [
        ("main_chunk", CBytecodeChunk),
        ("function_chunks", POINTER(CFunctionChunk)),
        ("function_count", c_size_t),
    ]


class CCompilationResult(Structure):
    """Compilation result

    Must match: Stoffel-Lang/src/ffi.rs CCompilationResult struct
    """
    _fields_ = [
        ("success", c_int),
        ("program", POINTER(CCompiledProgram)),
        ("errors", CCompilerErrors),
    ]


class CBinaryResult(Structure):
    """Binary compilation result

    Must match: Stoffel-Lang/src/ffi.rs CBinaryResult struct
    """
    _fields_ = [
        ("data", POINTER(c_uint8)),
        ("len", c_size_t),
        ("error", c_char_p),
    ]


# ==============================================================================
# Enums
# ==============================================================================

class ErrorSeverity(IntEnum):
    """Compiler error severity levels"""
    WARNING = 0
    ERROR = 1
    FATAL = 2


class ErrorCategory(IntEnum):
    """Compiler error categories"""
    SYNTAX = 0
    TYPE = 1
    SEMANTIC = 2
    INTERNAL = 3


class ConstantType(IntEnum):
    """Constant value types"""
    I64 = 0
    I32 = 1
    I16 = 2
    I8 = 3
    U8 = 4
    U16 = 5
    U32 = 6
    U64 = 7
    FLOAT = 8
    BOOL = 9
    STRING = 10
    OBJECT = 11
    ARRAY = 12
    FOREIGN = 13
    CLOSURE = 14
    UNIT = 15
    SHARE = 16


# ==============================================================================
# Python Data Classes
# ==============================================================================

@dataclass
class CompilerError:
    """Python representation of a compiler error"""
    message: str
    file: str
    line: int
    column: int
    severity: ErrorSeverity
    category: ErrorCategory
    code: str
    hint: Optional[str] = None


@dataclass
class CompilerOptions:
    """Python representation of compiler options"""
    optimize: bool = False
    optimization_level: int = 0
    print_ir: bool = False

    def to_c_struct(self) -> CCompilerOptions:
        """Convert to C structure"""
        return CCompilerOptions(
            optimize=1 if self.optimize else 0,
            optimization_level=self.optimization_level,
            print_ir=1 if self.print_ir else 0,
        )


class CompilationError(Exception):
    """Error during compilation"""

    def __init__(self, message: str, errors: Optional[List[CompilerError]] = None):
        super().__init__(message)
        self.errors = errors or []


# ==============================================================================
# FFI Function Wrappers
# ==============================================================================

class CompilerFunctions:
    """
    Raw Stoffel-Lang compiler FFI function bindings

    This class provides direct access to the C FFI functions for
    compilation operations. Functions are lazily initialized on first use.
    """

    _instance: Optional["CompilerFunctions"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self._lib = get_compiler_library()
            self._setup_functions()
            self._initialized = True
        except LibraryLoadError:
            self._lib = None
            self._initialized = True

    @property
    def available(self) -> bool:
        """Check if compiler FFI functions are available"""
        return self._lib is not None

    def _setup_functions(self):
        """Set up C function signatures"""
        lib = self._lib

        # ======================================================================
        # Compilation Functions
        # ======================================================================

        # stoffel_compile - Compile source to program structure
        lib.stoffel_compile.argtypes = [
            c_char_p,                   # source
            c_char_p,                   # filename
            POINTER(CCompilerOptions),  # options
        ]
        lib.stoffel_compile.restype = POINTER(CCompilationResult)

        # stoffel_compile_to_binary - Compile source directly to VM binary
        lib.stoffel_compile_to_binary.argtypes = [
            c_char_p,                   # source
            c_char_p,                   # filename
            POINTER(CCompilerOptions),  # options
        ]
        lib.stoffel_compile_to_binary.restype = POINTER(CBinaryResult)

        # ======================================================================
        # Memory Management Functions
        # ======================================================================

        # stoffel_free_compilation_result
        lib.stoffel_free_compilation_result.argtypes = [POINTER(CCompilationResult)]
        lib.stoffel_free_compilation_result.restype = None

        # stoffel_free_compiled_program
        lib.stoffel_free_compiled_program.argtypes = [POINTER(CCompiledProgram)]
        lib.stoffel_free_compiled_program.restype = None

        # stoffel_free_bytecode_chunk
        lib.stoffel_free_bytecode_chunk.argtypes = [POINTER(CBytecodeChunk)]
        lib.stoffel_free_bytecode_chunk.restype = None

        # stoffel_free_compiler_errors
        lib.stoffel_free_compiler_errors.argtypes = [POINTER(CCompilerErrors)]
        lib.stoffel_free_compiler_errors.restype = None

        # stoffel_free_binary_result
        lib.stoffel_free_binary_result.argtypes = [POINTER(CBinaryResult)]
        lib.stoffel_free_binary_result.restype = None

        # ======================================================================
        # Utility Functions
        # ======================================================================

        # stoffel_get_version
        lib.stoffel_get_version.argtypes = []
        lib.stoffel_get_version.restype = c_char_p

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _extract_errors(self, c_errors: CCompilerErrors) -> List[CompilerError]:
        """Convert C compiler errors to Python objects"""
        errors = []
        for i in range(c_errors.count):
            c_err = c_errors.errors[i]
            errors.append(CompilerError(
                message=c_err.message.decode('utf-8') if c_err.message else "",
                file=c_err.file.decode('utf-8') if c_err.file else "",
                line=c_err.line,
                column=c_err.column,
                severity=ErrorSeverity(c_err.severity),
                category=ErrorCategory(c_err.category),
                code=c_err.code.decode('utf-8') if c_err.code else "",
                hint=c_err.hint.decode('utf-8') if c_err.hint else None,
            ))
        return errors

    # ==========================================================================
    # Compilation Methods
    # ==========================================================================

    def compile(
        self,
        source: str,
        filename: str = "<source>",
        options: Optional[CompilerOptions] = None
    ) -> POINTER(CCompiledProgram):
        """
        Compile source code to a program structure

        Args:
            source: The source code to compile
            filename: Filename for error reporting
            options: Compiler options (optional)

        Returns:
            Pointer to the compiled program structure

        Raises:
            LibraryLoadError: If compiler library not available
            CompilationError: If compilation fails
        """
        if not self.available:
            raise LibraryLoadError("Compiler library not available")

        opts = options or CompilerOptions()
        c_opts = opts.to_c_struct()

        result_ptr = self._lib.stoffel_compile(
            source.encode('utf-8'),
            filename.encode('utf-8'),
            ctypes.byref(c_opts)
        )

        if not result_ptr:
            raise CompilationError("Compilation failed: null result")

        result = result_ptr.contents

        if result.success == 0:
            # Compilation failed
            errors = self._extract_errors(result.errors)
            error_msgs = [f"{e.file}:{e.line}:{e.column}: {e.message}" for e in errors]
            self._lib.stoffel_free_compilation_result(result_ptr)
            raise CompilationError(
                f"Compilation failed with {len(errors)} error(s):\n" + "\n".join(error_msgs),
                errors
            )

        program = result.program
        # Note: We don't free the result here as the program is part of it
        # The caller must free using free_compilation_result

        return program

    def compile_to_binary(
        self,
        source: str,
        filename: str = "<source>",
        options: Optional[CompilerOptions] = None
    ) -> bytes:
        """
        Compile source code directly to VM-compatible binary

        This is the recommended compilation method for loading into StoffelVM.

        Args:
            source: The source code to compile
            filename: Filename for error reporting
            options: Compiler options (optional)

        Returns:
            Compiled bytecode as bytes

        Raises:
            LibraryLoadError: If compiler library not available
            CompilationError: If compilation fails
        """
        if not self.available:
            raise LibraryLoadError("Compiler library not available")

        opts = options or CompilerOptions()
        c_opts = opts.to_c_struct()

        result_ptr = self._lib.stoffel_compile_to_binary(
            source.encode('utf-8'),
            filename.encode('utf-8'),
            ctypes.byref(c_opts)
        )

        if not result_ptr:
            raise CompilationError("Compilation failed: null result")

        result = result_ptr.contents

        if result.error:
            error_msg = result.error.decode('utf-8')
            self._lib.stoffel_free_binary_result(result_ptr)
            raise CompilationError(f"Compilation failed: {error_msg}")

        if not result.data or result.len == 0:
            self._lib.stoffel_free_binary_result(result_ptr)
            raise CompilationError("Compilation produced empty output")

        # Copy the binary data to Python bytes
        bytecode = bytes(result.data[:result.len])

        # Free the result
        self._lib.stoffel_free_binary_result(result_ptr)

        return bytecode

    # ==========================================================================
    # Memory Management Methods
    # ==========================================================================

    def free_compilation_result(self, result: POINTER(CCompilationResult)) -> None:
        """Free a compilation result"""
        if self.available and result:
            self._lib.stoffel_free_compilation_result(result)

    def free_compiled_program(self, program: POINTER(CCompiledProgram)) -> None:
        """Free a compiled program"""
        if self.available and program:
            self._lib.stoffel_free_compiled_program(program)

    def free_binary_result(self, result: POINTER(CBinaryResult)) -> None:
        """Free a binary result"""
        if self.available and result:
            self._lib.stoffel_free_binary_result(result)

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def get_version(self) -> str:
        """
        Get the compiler version

        Returns:
            Version string

        Raises:
            LibraryLoadError: If compiler library not available
        """
        if not self.available:
            raise LibraryLoadError("Compiler library not available")

        version = self._lib.stoffel_get_version()
        return version.decode('utf-8') if version else "unknown"


# ==============================================================================
# High-Level Compiler Wrapper
# ==============================================================================

class StoffelCompiler:
    """
    High-level wrapper around Stoffel-Lang compiler FFI

    Provides a Pythonic interface for compilation.

    Usage:
        compiler = StoffelCompiler()
        bytecode = compiler.compile_source(source_code)
    """

    def __init__(self):
        self._ffi = get_compiler_ffi()
        if not self._ffi.available:
            raise LibraryLoadError("Stoffel-Lang compiler library not available")

    def compile_source(
        self,
        source: str,
        filename: str = "<source>",
        optimize: bool = False,
        optimization_level: int = 0,
        print_ir: bool = False
    ) -> bytes:
        """
        Compile source code to bytecode

        Args:
            source: StoffelLang source code
            filename: Filename for error reporting
            optimize: Whether to enable optimization
            optimization_level: Optimization level (0-3)
            print_ir: Whether to print IR (for debugging)

        Returns:
            Compiled bytecode bytes

        Raises:
            CompilationError: If compilation fails
        """
        options = CompilerOptions(
            optimize=optimize,
            optimization_level=optimization_level,
            print_ir=print_ir,
        )
        return self._ffi.compile_to_binary(source, filename, options)

    def compile_file(
        self,
        filepath: str,
        optimize: bool = False,
        optimization_level: int = 0
    ) -> bytes:
        """
        Compile a source file to bytecode

        Args:
            filepath: Path to the source file
            optimize: Whether to enable optimization
            optimization_level: Optimization level (0-3)

        Returns:
            Compiled bytecode bytes

        Raises:
            CompilationError: If compilation fails
            FileNotFoundError: If file doesn't exist
        """
        with open(filepath, 'r') as f:
            source = f.read()

        return self.compile_source(
            source,
            filename=filepath,
            optimize=optimize,
            optimization_level=optimization_level
        )

    @property
    def version(self) -> str:
        """Get the compiler version"""
        return self._ffi.get_version()


# ==============================================================================
# Global Singleton Access
# ==============================================================================

_compiler_ffi: Optional[CompilerFunctions] = None


def get_compiler_ffi() -> CompilerFunctions:
    """Get the Stoffel-Lang compiler FFI singleton"""
    global _compiler_ffi
    if _compiler_ffi is None:
        _compiler_ffi = CompilerFunctions()
    return _compiler_ffi


def is_compiler_available() -> bool:
    """Check if Stoffel-Lang compiler FFI is available"""
    return get_compiler_ffi().available
