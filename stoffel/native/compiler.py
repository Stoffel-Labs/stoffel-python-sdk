"""
Native compiler bindings using ctypes

Provides direct access to the Stoffel-Lang compiler via C FFI.
"""

import ctypes
from ctypes import (
    Structure, Union as CUnion, POINTER,
    c_int, c_int64, c_int32, c_int16, c_int8,
    c_uint64, c_uint32, c_uint16, c_uint8,
    c_char_p, c_size_t, c_void_p
)
from dataclasses import dataclass
from typing import Optional, List
import os
import platform


# C structure definitions matching stoffellang.h

class CCompilerOptions(Structure):
    """Compiler options structure"""
    _fields_ = [
        ("optimize", c_int),
        ("optimization_level", c_uint8),
        ("print_ir", c_int),
    ]


class CCompilerError(Structure):
    """Compiler error structure"""
    _fields_ = [
        ("message", c_char_p),
        ("file", c_char_p),
        ("line", c_size_t),
        ("column", c_size_t),
        ("severity", c_int),
        ("category", c_int),
        ("code", c_char_p),
        ("hint", c_char_p),
    ]


class CCompilerErrors(Structure):
    """Compiler errors collection"""
    _fields_ = [
        ("errors", POINTER(CCompilerError)),
        ("count", c_size_t),
    ]


class CConstantData(CUnion):
    """Union for constant values"""
    _fields_ = [
        ("i64_val", c_int64),
        ("i32_val", c_int32),
        ("i16_val", c_int16),
        ("i8_val", c_int8),
        ("u64_val", c_uint64),
        ("u32_val", c_uint32),
        ("u16_val", c_uint16),
        ("u8_val", c_uint8),
        ("float_val", c_int64),  # Fixed-point representation
        ("bool_val", c_int),
        ("string_val", c_char_p),
        ("object_val", c_size_t),
        ("array_val", c_size_t),
        ("foreign_val", c_size_t),
    ]


class CConstant(Structure):
    """Constant value structure"""
    _fields_ = [
        ("const_type", c_int),
        ("data", CConstantData),
    ]


class CInstruction(Structure):
    """Bytecode instruction structure"""
    _fields_ = [
        ("opcode", c_uint8),
        ("operand1", c_size_t),
        ("operand2", c_size_t),
        ("operand3", c_size_t),
    ]


class CBytecodeChunk(Structure):
    """Bytecode chunk structure"""
    _fields_ = [
        ("instructions", POINTER(CInstruction)),
        ("instruction_count", c_size_t),
        ("constants", POINTER(CConstant)),
        ("constant_count", c_size_t),
    ]


class CFunctionChunk(Structure):
    """Function chunk structure"""
    _fields_ = [
        ("name", c_char_p),
        ("chunk", CBytecodeChunk),
    ]


class CCompiledProgram(Structure):
    """Compiled program structure"""
    _fields_ = [
        ("main_chunk", CBytecodeChunk),
        ("function_chunks", POINTER(CFunctionChunk)),
        ("function_count", c_size_t),
    ]


class CCompilationResult(Structure):
    """Compilation result structure"""
    _fields_ = [
        ("success", c_int),
        ("program", POINTER(CCompiledProgram)),
        ("errors", CCompilerErrors),
    ]


class CBinaryResult(Structure):
    """Binary compilation result structure"""
    _fields_ = [
        ("data", POINTER(c_uint8)),
        ("len", c_size_t),
        ("error", c_char_p),
    ]


# Opcode constants
STOFFEL_OP_LD = 0
STOFFEL_OP_LDI = 1
STOFFEL_OP_MOV = 2
STOFFEL_OP_ADD = 3
STOFFEL_OP_SUB = 4
STOFFEL_OP_MUL = 5
STOFFEL_OP_DIV = 6
STOFFEL_OP_MOD = 7
STOFFEL_OP_AND = 8
STOFFEL_OP_OR = 9
STOFFEL_OP_XOR = 10
STOFFEL_OP_NOT = 11
STOFFEL_OP_SHL = 12
STOFFEL_OP_SHR = 13
STOFFEL_OP_JMP = 14
STOFFEL_OP_JMPEQ = 15
STOFFEL_OP_JMPNEQ = 16
STOFFEL_OP_JMPLT = 17
STOFFEL_OP_JMPGT = 18
STOFFEL_OP_CALL = 19
STOFFEL_OP_RET = 20
STOFFEL_OP_PUSHARG = 21
STOFFEL_OP_CMP = 22

# Constant type constants
STOFFEL_CONST_I64 = 0
STOFFEL_CONST_I32 = 1
STOFFEL_CONST_I16 = 2
STOFFEL_CONST_I8 = 3
STOFFEL_CONST_U8 = 4
STOFFEL_CONST_U16 = 5
STOFFEL_CONST_U32 = 6
STOFFEL_CONST_U64 = 7
STOFFEL_CONST_FLOAT = 8
STOFFEL_CONST_BOOL = 9
STOFFEL_CONST_STRING = 10
STOFFEL_CONST_OBJECT = 11
STOFFEL_CONST_ARRAY = 12
STOFFEL_CONST_FOREIGN = 13
STOFFEL_CONST_CLOSURE = 14
STOFFEL_CONST_UNIT = 15
STOFFEL_CONST_SHARE = 16

# Severity levels
STOFFEL_SEVERITY_WARNING = 0
STOFFEL_SEVERITY_ERROR = 1
STOFFEL_SEVERITY_FATAL = 2

# Error categories
STOFFEL_CATEGORY_SYNTAX = 0
STOFFEL_CATEGORY_TYPE = 1
STOFFEL_CATEGORY_SEMANTIC = 2
STOFFEL_CATEGORY_INTERNAL = 3


@dataclass
class CompilerOptions:
    """Python-friendly compiler options"""
    optimize: bool = False
    optimization_level: int = 0

    def to_c_options(self) -> CCompilerOptions:
        """Convert to C structure"""
        return CCompilerOptions(
            optimize=1 if self.optimize else 0,
            optimization_level=self.optimization_level,
            print_ir=0,  # IR output is internal compiler detail
        )


@dataclass
class CompilerError:
    """Python-friendly compiler error"""
    message: str
    file: str
    line: int
    column: int
    severity: int
    category: int
    code: str
    hint: Optional[str]

    @classmethod
    def from_c_error(cls, c_error: CCompilerError) -> "CompilerError":
        """Create from C structure"""
        return cls(
            message=c_error.message.decode("utf-8") if c_error.message else "",
            file=c_error.file.decode("utf-8") if c_error.file else "",
            line=c_error.line,
            column=c_error.column,
            severity=c_error.severity,
            category=c_error.category,
            code=c_error.code.decode("utf-8") if c_error.code else "",
            hint=c_error.hint.decode("utf-8") if c_error.hint else None,
        )


class CompilationException(Exception):
    """Exception raised when compilation fails"""
    def __init__(self, message: str, errors: List[CompilerError]):
        super().__init__(message)
        self.errors = errors


class NativeCompiler:
    """
    Native Stoffel compiler using C FFI

    Provides direct access to the Stoffel-Lang compiler library.
    """

    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize the native compiler

        Args:
            library_path: Path to the libstoffellang shared library.
                         If None, attempts to find it in standard locations.
        """
        self._lib = self._load_library(library_path)
        self._setup_functions()

    def _load_library(self, library_path: Optional[str]) -> ctypes.CDLL:
        """Load the Stoffel-Lang shared library"""
        if library_path:
            return ctypes.CDLL(library_path)

        # Try common locations
        system = platform.system()
        if system == "Darwin":
            lib_names = ["libstoffellang.dylib"]
        elif system == "Windows":
            lib_names = ["stoffellang.dll", "libstoffellang.dll"]
        else:
            lib_names = ["libstoffellang.so"]

        search_paths = [
            ".",
            "./target/release",
            "./target/debug",
            "./external/stoffel-lang/target/release",
            "./external/stoffel-lang/target/debug",
            "/usr/local/lib",
            "/usr/lib",
        ]

        for path in search_paths:
            for lib_name in lib_names:
                full_path = os.path.join(path, lib_name)
                if os.path.exists(full_path):
                    try:
                        return ctypes.CDLL(full_path)
                    except OSError:
                        continue

        # Try loading without path (system library)
        for lib_name in lib_names:
            try:
                return ctypes.CDLL(lib_name)
            except OSError:
                continue

        raise RuntimeError(
            "Could not find Stoffel-Lang library. "
            "Please build it with 'cargo build --release' in external/stoffel-lang "
            "or specify the library_path parameter."
        )

    def _setup_functions(self):
        """Set up C function signatures"""
        # stoffel_compile
        self._lib.stoffel_compile.argtypes = [
            c_char_p,  # source
            c_char_p,  # filename
            POINTER(CCompilerOptions),  # options (nullable)
        ]
        self._lib.stoffel_compile.restype = POINTER(CCompilationResult)

        # stoffel_get_version
        self._lib.stoffel_get_version.argtypes = []
        self._lib.stoffel_get_version.restype = c_char_p

        # stoffel_free_compilation_result
        self._lib.stoffel_free_compilation_result.argtypes = [POINTER(CCompilationResult)]
        self._lib.stoffel_free_compilation_result.restype = None

        # stoffel_free_compiled_program
        self._lib.stoffel_free_compiled_program.argtypes = [POINTER(CCompiledProgram)]
        self._lib.stoffel_free_compiled_program.restype = None

        # stoffel_compile_to_binary - compiles to VM-compatible binary format
        self._lib.stoffel_compile_to_binary.argtypes = [
            c_char_p,  # source
            c_char_p,  # filename
            POINTER(CCompilerOptions),  # options (nullable)
        ]
        self._lib.stoffel_compile_to_binary.restype = POINTER(CBinaryResult)

        # stoffel_free_binary_result
        self._lib.stoffel_free_binary_result.argtypes = [POINTER(CBinaryResult)]
        self._lib.stoffel_free_binary_result.restype = None

    def get_version(self) -> str:
        """Get the compiler version string"""
        version = self._lib.stoffel_get_version()
        return version.decode("utf-8") if version else "unknown"

    def compile(
        self,
        source: str,
        filename: str = "<stdin>",
        options: Optional[CompilerOptions] = None
    ) -> bytes:
        """
        Compile Stoffel source code to bytecode

        Args:
            source: The Stoffel source code
            filename: Filename for error reporting
            options: Compiler options

        Returns:
            Compiled bytecode as bytes (VM-compatible binary format)

        Raises:
            CompilationException: If compilation fails
        """
        # Prepare arguments
        source_bytes = source.encode("utf-8")
        filename_bytes = filename.encode("utf-8")

        c_options = None
        if options:
            c_options = options.to_c_options()
            c_options_ptr = ctypes.pointer(c_options)
        else:
            c_options_ptr = None

        # Use stoffel_compile_to_binary for VM-compatible output
        result_ptr = self._lib.stoffel_compile_to_binary(
            source_bytes, filename_bytes, c_options_ptr
        )

        if not result_ptr:
            raise RuntimeError("Compiler returned null result")

        try:
            result = result_ptr.contents

            # Check for error
            if result.error:
                error_msg = result.error.decode("utf-8")
                raise CompilationException(
                    f"Compilation failed: {error_msg}",
                    []
                )

            # Extract bytecode bytes
            if result.data and result.len > 0:
                bytecode = bytes(result.data[:result.len])
                return bytecode
            else:
                raise RuntimeError("Compiler produced empty bytecode")

        finally:
            # Free the result
            self._lib.stoffel_free_binary_result(result_ptr)

    def _extract_bytecode(self, program: CCompiledProgram) -> bytes:
        """
        Extract bytecode from a compiled program

        This serializes the program to a binary format compatible with the VM.
        """
        # For now, we create a simple serialization format
        # In practice, you would use the VM's binary format
        import struct

        bytecode = bytearray()

        # Magic header "STFL"
        bytecode.extend(b"STFL")

        # Version (u16)
        bytecode.extend(struct.pack("<H", 1))

        # Serialize main chunk constants
        main_chunk = program.main_chunk
        bytecode.extend(struct.pack("<I", main_chunk.constant_count))

        for i in range(main_chunk.constant_count):
            constant = main_chunk.constants[i]
            bytecode.extend(self._serialize_constant(constant))

        # Serialize functions
        bytecode.extend(struct.pack("<I", program.function_count + 1))  # +1 for main

        # Main function
        bytecode.extend(self._serialize_function("main", main_chunk))

        # Other functions
        for i in range(program.function_count):
            func_chunk = program.function_chunks[i]
            name = func_chunk.name.decode("utf-8") if func_chunk.name else f"func_{i}"
            bytecode.extend(self._serialize_function(name, func_chunk.chunk))

        return bytes(bytecode)

    def _serialize_constant(self, constant: CConstant) -> bytes:
        """Serialize a constant value"""
        import struct

        data = bytearray()
        data.append(constant.const_type)

        if constant.const_type == STOFFEL_CONST_I64:
            data.extend(struct.pack("<q", constant.data.i64_val))
        elif constant.const_type == STOFFEL_CONST_I32:
            data.extend(struct.pack("<i", constant.data.i32_val))
        elif constant.const_type == STOFFEL_CONST_I16:
            data.extend(struct.pack("<h", constant.data.i16_val))
        elif constant.const_type == STOFFEL_CONST_I8:
            data.extend(struct.pack("<b", constant.data.i8_val))
        elif constant.const_type == STOFFEL_CONST_U8:
            data.extend(struct.pack("<B", constant.data.u8_val))
        elif constant.const_type == STOFFEL_CONST_U16:
            data.extend(struct.pack("<H", constant.data.u16_val))
        elif constant.const_type == STOFFEL_CONST_U32:
            data.extend(struct.pack("<I", constant.data.u32_val))
        elif constant.const_type == STOFFEL_CONST_U64:
            data.extend(struct.pack("<Q", constant.data.u64_val))
        elif constant.const_type == STOFFEL_CONST_FLOAT:
            data.extend(struct.pack("<q", constant.data.float_val))
        elif constant.const_type == STOFFEL_CONST_BOOL:
            data.append(1 if constant.data.bool_val else 0)
        elif constant.const_type == STOFFEL_CONST_STRING:
            if constant.data.string_val:
                string_bytes = constant.data.string_val
                data.extend(struct.pack("<I", len(string_bytes)))
                data.extend(string_bytes)
            else:
                data.extend(struct.pack("<I", 0))
        elif constant.const_type == STOFFEL_CONST_UNIT:
            pass  # No additional data

        return bytes(data)

    def _serialize_function(self, name: str, chunk: CBytecodeChunk) -> bytes:
        """Serialize a function"""
        import struct

        data = bytearray()

        # Function name
        name_bytes = name.encode("utf-8")
        data.extend(struct.pack("<H", len(name_bytes)))
        data.extend(name_bytes)

        # Register count (estimate from instructions)
        data.extend(struct.pack("<H", 16))  # Default register count

        # Parameters (empty for now)
        data.extend(struct.pack("<H", 0))

        # Upvalues (empty for now)
        data.extend(struct.pack("<H", 0))

        # Parent (none)
        data.append(0)

        # Labels (empty for now - would need to extract from instructions)
        data.extend(struct.pack("<H", 0))

        # Instructions
        data.extend(struct.pack("<I", chunk.instruction_count))

        for i in range(chunk.instruction_count):
            instr = chunk.instructions[i]
            data.append(instr.opcode)
            data.extend(struct.pack("<I", instr.operand1))
            data.extend(struct.pack("<I", instr.operand2))
            data.extend(struct.pack("<I", instr.operand3))

        return bytes(data)

    def compile_file(
        self,
        path: str,
        options: Optional[CompilerOptions] = None
    ) -> bytes:
        """
        Compile a Stoffel source file

        Args:
            path: Path to the .stfl file
            options: Compiler options

        Returns:
            Compiled bytecode as bytes
        """
        with open(path, "r") as f:
            source = f.read()

        filename = os.path.basename(path)
        return self.compile(source, filename, options)

