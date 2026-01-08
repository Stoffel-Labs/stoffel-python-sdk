"""
Native VM bindings using ctypes

Provides direct access to the Stoffel VM via C FFI.
"""

import ctypes
from ctypes import (
    Structure, Union as CUnion, POINTER, CFUNCTYPE,
    c_int, c_int64, c_double, c_char_p, c_size_t, c_void_p, c_uint8
)
from typing import Any, Callable, Dict, List, Optional, Union
from enum import IntEnum
import os
import platform


class ValueType(IntEnum):
    """Value types in Stoffel VM"""
    UNIT = 0
    INT = 1
    FLOAT = 2
    BOOL = 3
    STRING = 4
    OBJECT = 5
    ARRAY = 6
    FOREIGN = 7
    CLOSURE = 8


class StoffelValueData(CUnion):
    """Union to hold actual value data"""
    _fields_ = [
        ("int_val", c_int64),
        ("float_val", c_double),
        ("bool_val", c_int),
        ("string_val", c_char_p),
        ("object_id", c_size_t),
        ("array_id", c_size_t),
        ("foreign_id", c_size_t),
        ("closure_id", c_size_t),
    ]


class CStoffelValue(Structure):
    """C-compatible Stoffel value"""
    _fields_ = [
        ("value_type", c_int),
        ("data", StoffelValueData),
    ]


# C function pointer type for foreign functions
CForeignFunctionType = CFUNCTYPE(
    c_int,  # return type
    POINTER(CStoffelValue),  # args
    c_int,  # arg_count
    POINTER(CStoffelValue),  # result
)


class VMError(Exception):
    """Exception raised for VM errors"""
    pass


class ExecutionError(VMError):
    """Exception raised for execution errors"""
    pass


class VMFFINotAvailable(VMError):
    """Exception raised when VM C FFI is not available in the library"""
    pass


def is_vm_ffi_available(library_path: Optional[str] = None) -> bool:
    """
    Check if the VM C FFI is available.

    Args:
        library_path: Optional path to the VM library

    Returns:
        True if the C FFI functions are available, False otherwise
    """
    try:
        # Try to load the library
        if library_path:
            lib = ctypes.CDLL(library_path)
        else:
            # Try common locations
            system = platform.system()
            if system == "Darwin":
                lib_name = "libstoffel_vm.dylib"
            elif system == "Windows":
                lib_name = "stoffel_vm.dll"
            else:
                lib_name = "libstoffel_vm.so"

            search_paths = [
                ".",
                "./target/release",
                "./external/stoffel-vm/target/release",
            ]

            lib = None
            for path in search_paths:
                full_path = os.path.join(path, lib_name)
                if os.path.exists(full_path):
                    try:
                        lib = ctypes.CDLL(full_path)
                        break
                    except OSError:
                        continue

            if lib is None:
                return False

        # Check if stoffel_create_vm exists
        _ = lib.stoffel_create_vm
        return True
    except (OSError, AttributeError):
        return False


class NativeVM:
    """
    Native Stoffel VM using C FFI

    Provides direct access to the Stoffel VM library.
    """

    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize the native VM

        Args:
            library_path: Path to the libstoffel_vm shared library.
                         If None, attempts to find it in standard locations.

        Raises:
            VMError: If the library cannot be loaded or VM creation fails
            RuntimeError: If the VM C FFI is not available in the library
        """
        self._lib = self._load_library(library_path)

        # Check if the C FFI functions are available
        if not self._check_ffi_available():
            raise RuntimeError(
                "The Stoffel VM library was loaded but the C FFI functions are not available. "
                "The 'cffi' module needs to be exported in stoffel-vm/crates/stoffel-vm/src/lib.rs. "
                "Add 'pub mod cffi;' to lib.rs and rebuild with 'cargo build --release'."
            )

        self._setup_functions()
        self._handle = self._lib.stoffel_create_vm()

        if not self._handle:
            raise VMError("Failed to create VM instance")

        # Keep references to prevent GC of callbacks
        self._foreign_functions: Dict[str, Any] = {}

    def __del__(self):
        """Clean up VM instance"""
        if hasattr(self, "_handle") and self._handle:
            self._lib.stoffel_destroy_vm(self._handle)
            self._handle = None

    def _load_library(self, library_path: Optional[str]) -> ctypes.CDLL:
        """Load the Stoffel VM shared library"""
        if library_path:
            return ctypes.CDLL(library_path)

        # Try common locations
        system = platform.system()
        if system == "Darwin":
            lib_names = ["libstoffel_vm.dylib"]
        elif system == "Windows":
            lib_names = ["stoffel_vm.dll", "libstoffel_vm.dll"]
        else:
            lib_names = ["libstoffel_vm.so"]

        search_paths = [
            ".",
            "./target/release",
            "./target/debug",
            "./external/stoffel-vm/target/release",
            "./external/stoffel-vm/target/debug",
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
            "Could not find Stoffel VM library. "
            "Please build it with 'cargo build --release' in external/stoffel-vm "
            "or specify the library_path parameter."
        )

    def _check_ffi_available(self) -> bool:
        """Check if the VM C FFI functions are available in the library."""
        try:
            # Try to get the stoffel_create_vm symbol
            _ = self._lib.stoffel_create_vm
            return True
        except AttributeError:
            return False

    def _setup_functions(self):
        """Set up C function signatures"""
        # stoffel_create_vm
        self._lib.stoffel_create_vm.argtypes = []
        self._lib.stoffel_create_vm.restype = c_void_p

        # stoffel_destroy_vm
        self._lib.stoffel_destroy_vm.argtypes = [c_void_p]
        self._lib.stoffel_destroy_vm.restype = None

        # stoffel_execute
        self._lib.stoffel_execute.argtypes = [
            c_void_p,  # handle
            c_char_p,  # function_name
            POINTER(CStoffelValue),  # result
        ]
        self._lib.stoffel_execute.restype = c_int

        # stoffel_execute_with_args
        self._lib.stoffel_execute_with_args.argtypes = [
            c_void_p,  # handle
            c_char_p,  # function_name
            POINTER(CStoffelValue),  # args
            c_int,  # arg_count
            POINTER(CStoffelValue),  # result
        ]
        self._lib.stoffel_execute_with_args.restype = c_int

        # stoffel_register_foreign_function
        self._lib.stoffel_register_foreign_function.argtypes = [
            c_void_p,  # handle
            c_char_p,  # name
            CForeignFunctionType,  # func
        ]
        self._lib.stoffel_register_foreign_function.restype = c_int

        # stoffel_register_foreign_object
        self._lib.stoffel_register_foreign_object.argtypes = [
            c_void_p,  # handle
            c_void_p,  # object
            POINTER(CStoffelValue),  # result
        ]
        self._lib.stoffel_register_foreign_object.restype = c_int

        # stoffel_create_string
        self._lib.stoffel_create_string.argtypes = [
            c_void_p,  # handle
            c_char_p,  # str
            POINTER(CStoffelValue),  # result
        ]
        self._lib.stoffel_create_string.restype = c_int

        # stoffel_free_string
        self._lib.stoffel_free_string.argtypes = [c_char_p]
        self._lib.stoffel_free_string.restype = None

        # stoffel_load_bytecode
        self._lib.stoffel_load_bytecode.argtypes = [
            c_void_p,  # handle
            POINTER(c_uint8),  # bytecode
            c_size_t,  # bytecode_len
        ]
        self._lib.stoffel_load_bytecode.restype = c_int

    def load(self, bytecode: bytes) -> None:
        """
        Load bytecode into the VM

        Args:
            bytecode: Compiled bytecode bytes

        Raises:
            VMError: If loading fails
        """
        if not bytecode:
            raise VMError("Cannot load empty bytecode")

        # Convert bytes to ctypes array
        bytecode_array = (c_uint8 * len(bytecode)).from_buffer_copy(bytecode)

        ret = self._lib.stoffel_load_bytecode(
            self._handle,
            bytecode_array,
            len(bytecode)
        )

        if ret != 0:
            error_messages = {
                -1: "Invalid VM handle or null bytecode pointer",
                -2: "Failed to deserialize bytecode (invalid format or corrupted data)",
                -3: "Failed to register functions from bytecode",
            }
            msg = error_messages.get(ret, f"Unknown error code: {ret}")
            raise VMError(f"Failed to load bytecode: {msg}")

    def execute(self, function_name: str) -> Any:
        """
        Execute a VM function

        Args:
            function_name: Name of the function to execute

        Returns:
            The function result

        Raises:
            ExecutionError: If execution fails
        """
        result = CStoffelValue()
        ret = self._lib.stoffel_execute(
            self._handle,
            function_name.encode("utf-8"),
            ctypes.byref(result)
        )

        if ret != 0:
            raise ExecutionError(f"Failed to execute function '{function_name}'")

        return self._convert_from_stoffel(result)

    def execute_with_args(
        self,
        function_name: str,
        args: List[Any]
    ) -> Any:
        """
        Execute a VM function with arguments

        Args:
            function_name: Name of the function to execute
            args: List of arguments to pass

        Returns:
            The function result

        Raises:
            ExecutionError: If execution fails
        """
        # Convert arguments
        c_args = (CStoffelValue * len(args))()
        for i, arg in enumerate(args):
            c_args[i] = self._convert_to_stoffel(arg)

        result = CStoffelValue()
        ret = self._lib.stoffel_execute_with_args(
            self._handle,
            function_name.encode("utf-8"),
            c_args,
            len(args),
            ctypes.byref(result)
        )

        if ret != 0:
            raise ExecutionError(f"Failed to execute function '{function_name}'")

        return self._convert_from_stoffel(result)

    def register_function(
        self,
        name: str,
        func: Callable[..., Any]
    ) -> None:
        """
        Register a Python function with the VM

        Args:
            name: Name to register the function under
            func: Python callable to register

        Raises:
            VMError: If registration fails
        """
        def wrapper(args_ptr, arg_count, result_ptr):
            try:
                # Convert arguments
                args = []
                for i in range(arg_count):
                    args.append(self._convert_from_stoffel(args_ptr[i]))

                # Call the Python function
                py_result = func(*args)

                # Convert result
                result_ptr[0] = self._convert_to_stoffel(py_result)
                return 0

            except Exception as e:
                print(f"Error in foreign function '{name}': {e}")
                return 1

        c_func = CForeignFunctionType(wrapper)
        # Keep reference to prevent GC
        self._foreign_functions[name] = (c_func, wrapper)

        ret = self._lib.stoffel_register_foreign_function(
            self._handle,
            name.encode("utf-8"),
            c_func
        )

        if ret != 0:
            raise VMError(f"Failed to register function '{name}'")

    def _convert_to_stoffel(self, value: Any) -> CStoffelValue:
        """Convert a Python value to a Stoffel value"""
        result = CStoffelValue()

        if value is None:
            result.value_type = ValueType.UNIT
        elif isinstance(value, bool):
            result.value_type = ValueType.BOOL
            result.data.bool_val = 1 if value else 0
        elif isinstance(value, int):
            result.value_type = ValueType.INT
            result.data.int_val = value
        elif isinstance(value, float):
            result.value_type = ValueType.FLOAT
            result.data.float_val = value
        elif isinstance(value, str):
            result.value_type = ValueType.STRING
            result.data.string_val = value.encode("utf-8")
        else:
            raise ValueError(f"Cannot convert Python type {type(value)} to Stoffel value")

        return result

    def _convert_from_stoffel(self, value: CStoffelValue) -> Any:
        """Convert a Stoffel value to a Python value"""
        vtype = value.value_type

        if vtype == ValueType.UNIT:
            return None
        elif vtype == ValueType.INT:
            return value.data.int_val
        elif vtype == ValueType.FLOAT:
            return value.data.float_val
        elif vtype == ValueType.BOOL:
            return bool(value.data.bool_val)
        elif vtype == ValueType.STRING:
            if value.data.string_val:
                return value.data.string_val.decode("utf-8")
            return ""
        elif vtype == ValueType.OBJECT:
            return {"__type": "object", "id": value.data.object_id}
        elif vtype == ValueType.ARRAY:
            return {"__type": "array", "id": value.data.array_id}
        elif vtype == ValueType.FOREIGN:
            return {"__type": "foreign", "id": value.data.foreign_id}
        elif vtype == ValueType.CLOSURE:
            return {"__type": "closure", "id": value.data.closure_id}
        else:
            raise ValueError(f"Unknown Stoffel value type: {vtype}")
