"""
StoffelVM FFI bindings

Raw ctypes bindings for StoffelVM execution.
Based on: StoffelVM/crates/stoffel-vm/src/cffi.rs

This module provides:
- VM lifecycle management (create/destroy)
- Bytecode loading
- Function execution with/without arguments
- Foreign function registration
- Value type conversions
"""

import ctypes
from ctypes import (
    POINTER, CFUNCTYPE, Structure, Union,
    c_void_p, c_char_p, c_int, c_int64, c_double, c_bool, c_size_t, c_uint8
)
from enum import IntEnum
from typing import Optional, List, Union as TypeUnion, Callable, Any

from ._lib_loader import get_vm_library, LibraryLoadError


# ==============================================================================
# Type Definitions
# ==============================================================================

# Opaque pointer type for the VM
VMHandle = c_void_p


class StoffelValueType(IntEnum):
    """Value types in StoffelVM exposed to C

    Must match: StoffelVM/crates/stoffel-vm/src/cffi.rs StoffelValueType enum
    """
    UNIT = 0     # Unit/void value
    INT = 1      # Integer value
    FLOAT = 2    # Float value
    BOOL = 3     # Boolean value
    STRING = 4   # String value
    OBJECT = 5   # Object reference
    ARRAY = 6    # Array reference
    FOREIGN = 7  # Foreign object reference
    CLOSURE = 8  # Function closure


class StoffelValueData(Union):
    """Union to hold actual value data

    Must match: StoffelVM/crates/stoffel-vm/src/cffi.rs StoffelValueData union
    """
    _fields_ = [
        ("int_val", c_int64),
        ("float_val", c_double),
        ("bool_val", c_bool),
        ("string_val", c_char_p),
        ("object_id", c_size_t),
        ("array_id", c_size_t),
        ("foreign_id", c_size_t),
        ("closure_id", c_size_t),
    ]


class StoffelValue(Structure):
    """C-compatible representation of a StoffelVM value

    Must match: StoffelVM/crates/stoffel-vm/src/cffi.rs StoffelValue struct
    """
    _fields_ = [
        ("value_type", c_int),  # StoffelValueType
        ("data", StoffelValueData),
    ]

    @classmethod
    def from_python(cls, value: Any) -> "StoffelValue":
        """Create a StoffelValue from a Python value"""
        result = cls()

        if value is None:
            result.value_type = StoffelValueType.UNIT
            result.data.int_val = 0
        elif isinstance(value, bool):
            result.value_type = StoffelValueType.BOOL
            result.data.bool_val = value
        elif isinstance(value, int):
            result.value_type = StoffelValueType.INT
            result.data.int_val = value
        elif isinstance(value, float):
            result.value_type = StoffelValueType.FLOAT
            result.data.float_val = value
        elif isinstance(value, str):
            result.value_type = StoffelValueType.STRING
            result.data.string_val = value.encode('utf-8')
        else:
            raise ValueError(f"Cannot convert {type(value)} to StoffelValue")

        return result

    def to_python(self) -> Any:
        """Convert StoffelValue to Python value"""
        if self.value_type == StoffelValueType.UNIT:
            return None
        elif self.value_type == StoffelValueType.INT:
            return self.data.int_val
        elif self.value_type == StoffelValueType.FLOAT:
            return self.data.float_val
        elif self.value_type == StoffelValueType.BOOL:
            return self.data.bool_val
        elif self.value_type == StoffelValueType.STRING:
            if self.data.string_val:
                return self.data.string_val.decode('utf-8')
            return ""
        elif self.value_type == StoffelValueType.OBJECT:
            return ("object", self.data.object_id)
        elif self.value_type == StoffelValueType.ARRAY:
            return ("array", self.data.array_id)
        elif self.value_type == StoffelValueType.FOREIGN:
            return ("foreign", self.data.foreign_id)
        elif self.value_type == StoffelValueType.CLOSURE:
            return ("closure", self.data.closure_id)
        else:
            raise ValueError(f"Unknown value type: {self.value_type}")


# Type for C callback functions
# extern "C" fn(args: *const StoffelValue, arg_count: c_int, result: *mut StoffelValue) -> c_int
CForeignFunction = CFUNCTYPE(c_int, POINTER(StoffelValue), c_int, POINTER(StoffelValue))


# ==============================================================================
# Error Codes
# ==============================================================================

class VMErrorCode(IntEnum):
    """Error codes returned by StoffelVM FFI functions"""
    SUCCESS = 0
    NULL_POINTER = -1
    INVALID_UTF8 = -2
    EXECUTION_ERROR = -3
    ARGUMENT_ERROR = -4


class VMError(Exception):
    """Error from StoffelVM FFI operation"""

    def __init__(self, message: str, code: int = -1):
        super().__init__(message)
        self.code = code


def check_vm_error(code: int, context: str = "") -> None:
    """Check VM error code and raise exception if not success"""
    if code == VMErrorCode.SUCCESS:
        return

    error_messages = {
        VMErrorCode.NULL_POINTER: "Null pointer error",
        VMErrorCode.INVALID_UTF8: "Invalid UTF-8 string",
        VMErrorCode.EXECUTION_ERROR: "Execution failed",
        VMErrorCode.ARGUMENT_ERROR: "Invalid arguments",
    }

    message = error_messages.get(code, f"Unknown error {code}")
    if context:
        message = f"{context}: {message}"

    raise VMError(message, code)


# ==============================================================================
# FFI Function Wrappers
# ==============================================================================

class VMFunctions:
    """
    Raw StoffelVM FFI function bindings

    This class provides direct access to the C FFI functions for
    StoffelVM operations. Functions are lazily initialized on first use.
    """

    _instance: Optional["VMFunctions"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self._lib = get_vm_library()
            self._setup_functions()
            self._initialized = True
        except LibraryLoadError:
            self._lib = None
            self._initialized = True

    @property
    def available(self) -> bool:
        """Check if StoffelVM FFI functions are available"""
        return self._lib is not None

    def _setup_functions(self):
        """Set up C function signatures"""
        lib = self._lib

        # ======================================================================
        # VM Lifecycle
        # ======================================================================

        # stoffel_create_vm - Create a new VM instance
        lib.stoffel_create_vm.argtypes = []
        lib.stoffel_create_vm.restype = VMHandle

        # stoffel_destroy_vm - Destroy a VM instance
        lib.stoffel_destroy_vm.argtypes = [VMHandle]
        lib.stoffel_destroy_vm.restype = None

        # ======================================================================
        # Bytecode Loading
        # ======================================================================

        # stoffel_load_bytecode - Load bytecode into the VM
        lib.stoffel_load_bytecode.argtypes = [
            VMHandle,           # handle
            POINTER(c_uint8),   # bytecode
            c_size_t,           # bytecode_len
        ]
        lib.stoffel_load_bytecode.restype = c_int

        # ======================================================================
        # Execution
        # ======================================================================

        # stoffel_execute - Execute a function and return result
        lib.stoffel_execute.argtypes = [
            VMHandle,               # handle
            c_char_p,               # function_name
            POINTER(StoffelValue),  # result
        ]
        lib.stoffel_execute.restype = c_int

        # stoffel_execute_with_args - Execute a function with arguments
        lib.stoffel_execute_with_args.argtypes = [
            VMHandle,               # handle
            c_char_p,               # function_name
            POINTER(StoffelValue),  # args
            c_int,                  # arg_count
            POINTER(StoffelValue),  # result
        ]
        lib.stoffel_execute_with_args.restype = c_int

        # ======================================================================
        # Foreign Functions
        # ======================================================================

        # stoffel_register_foreign_function - Register a C function with the VM
        lib.stoffel_register_foreign_function.argtypes = [
            VMHandle,           # handle
            c_char_p,           # name
            CForeignFunction,   # func
        ]
        lib.stoffel_register_foreign_function.restype = c_int

        # stoffel_register_foreign_object - Register a foreign object
        lib.stoffel_register_foreign_object.argtypes = [
            VMHandle,               # handle
            c_void_p,               # object
            POINTER(StoffelValue),  # result
        ]
        lib.stoffel_register_foreign_object.restype = c_int

        # ======================================================================
        # String Handling
        # ======================================================================

        # stoffel_create_string - Create a string in the VM
        lib.stoffel_create_string.argtypes = [
            VMHandle,               # handle
            c_char_p,               # str
            POINTER(StoffelValue),  # result
        ]
        lib.stoffel_create_string.restype = c_int

        # stoffel_free_string - Free a string created by the VM
        lib.stoffel_free_string.argtypes = [c_char_p]
        lib.stoffel_free_string.restype = None

    # ==========================================================================
    # VM Lifecycle Methods
    # ==========================================================================

    def create_vm(self) -> VMHandle:
        """
        Create a new VM instance

        Returns:
            Handle to the new VM instance

        Raises:
            LibraryLoadError: If VM library not available
            VMError: If VM creation fails
        """
        if not self.available:
            raise LibraryLoadError("VM library not available")

        handle = self._lib.stoffel_create_vm()
        if not handle:
            raise VMError("Failed to create VM instance")

        return handle

    def destroy_vm(self, handle: VMHandle) -> None:
        """
        Destroy a VM instance

        Args:
            handle: Handle to the VM instance
        """
        if self.available and handle:
            self._lib.stoffel_destroy_vm(handle)

    # ==========================================================================
    # Bytecode Loading Methods
    # ==========================================================================

    def load_bytecode(self, handle: VMHandle, bytecode: bytes) -> None:
        """
        Load bytecode into the VM

        Args:
            handle: Handle to the VM instance
            bytecode: Compiled bytecode bytes

        Raises:
            LibraryLoadError: If VM library not available
            VMError: If bytecode loading fails
        """
        if not self.available:
            raise LibraryLoadError("VM library not available")

        bytecode_array = (c_uint8 * len(bytecode))(*bytecode)

        result = self._lib.stoffel_load_bytecode(
            handle,
            ctypes.cast(bytecode_array, POINTER(c_uint8)),
            len(bytecode)
        )
        check_vm_error(result, "stoffel_load_bytecode")

    # ==========================================================================
    # Execution Methods
    # ==========================================================================

    def execute(self, handle: VMHandle, function_name: str) -> Any:
        """
        Execute a function and return the result

        Args:
            handle: Handle to the VM instance
            function_name: Name of the function to execute

        Returns:
            The execution result as a Python value

        Raises:
            LibraryLoadError: If VM library not available
            VMError: If execution fails
        """
        if not self.available:
            raise LibraryLoadError("VM library not available")

        result = StoffelValue()

        err = self._lib.stoffel_execute(
            handle,
            function_name.encode('utf-8'),
            ctypes.byref(result)
        )
        check_vm_error(err, f"stoffel_execute({function_name})")

        return result.to_python()

    def execute_with_args(
        self,
        handle: VMHandle,
        function_name: str,
        args: List[Any]
    ) -> Any:
        """
        Execute a function with arguments and return the result

        Args:
            handle: Handle to the VM instance
            function_name: Name of the function to execute
            args: List of arguments to pass to the function

        Returns:
            The execution result as a Python value

        Raises:
            LibraryLoadError: If VM library not available
            VMError: If execution fails
        """
        if not self.available:
            raise LibraryLoadError("VM library not available")

        # Convert Python args to StoffelValue array
        if args:
            args_array = (StoffelValue * len(args))()
            for i, arg in enumerate(args):
                args_array[i] = StoffelValue.from_python(arg)
            args_ptr = ctypes.cast(args_array, POINTER(StoffelValue))
        else:
            args_ptr = None

        result = StoffelValue()

        err = self._lib.stoffel_execute_with_args(
            handle,
            function_name.encode('utf-8'),
            args_ptr,
            len(args),
            ctypes.byref(result)
        )
        check_vm_error(err, f"stoffel_execute_with_args({function_name})")

        return result.to_python()

    # ==========================================================================
    # Foreign Function Methods
    # ==========================================================================

    def register_foreign_function(
        self,
        handle: VMHandle,
        name: str,
        callback: Callable[[List[Any]], Any]
    ) -> None:
        """
        Register a Python function as a foreign function in the VM

        Args:
            handle: Handle to the VM instance
            name: Name to register the function under
            callback: Python function to call

        Raises:
            LibraryLoadError: If VM library not available
            VMError: If registration fails
        """
        if not self.available:
            raise LibraryLoadError("VM library not available")

        # Wrapper to convert between C types and Python
        @CForeignFunction
        def wrapper(args: POINTER(StoffelValue), arg_count: int, result: POINTER(StoffelValue)) -> int:
            try:
                # Convert C args to Python
                py_args = []
                for i in range(arg_count):
                    py_args.append(args[i].to_python())

                # Call Python function
                py_result = callback(py_args)

                # Convert result back to C
                result[0] = StoffelValue.from_python(py_result)
                return 0
            except Exception as e:
                # Return error code on failure
                return -1

        # Keep wrapper alive
        if not hasattr(self, '_callbacks'):
            self._callbacks = {}
        self._callbacks[name] = wrapper

        err = self._lib.stoffel_register_foreign_function(
            handle,
            name.encode('utf-8'),
            wrapper
        )
        check_vm_error(err, f"stoffel_register_foreign_function({name})")

    def register_foreign_object(
        self,
        handle: VMHandle,
        obj: Any
    ) -> Any:
        """
        Register a foreign object with the VM

        Args:
            handle: Handle to the VM instance
            obj: Python object to register (must be a ctypes pointer)

        Returns:
            The StoffelValue representing the foreign object

        Raises:
            LibraryLoadError: If VM library not available
            VMError: If registration fails
        """
        if not self.available:
            raise LibraryLoadError("VM library not available")

        result = StoffelValue()

        err = self._lib.stoffel_register_foreign_object(
            handle,
            obj,
            ctypes.byref(result)
        )
        check_vm_error(err, "stoffel_register_foreign_object")

        return result.to_python()

    # ==========================================================================
    # String Methods
    # ==========================================================================

    def create_string(self, handle: VMHandle, s: str) -> Any:
        """
        Create a string in the VM

        Args:
            handle: Handle to the VM instance
            s: String to create

        Returns:
            The StoffelValue representing the string

        Raises:
            LibraryLoadError: If VM library not available
            VMError: If creation fails
        """
        if not self.available:
            raise LibraryLoadError("VM library not available")

        result = StoffelValue()

        err = self._lib.stoffel_create_string(
            handle,
            s.encode('utf-8'),
            ctypes.byref(result)
        )
        check_vm_error(err, "stoffel_create_string")

        return result.to_python()

    def free_string(self, s: c_char_p) -> None:
        """
        Free a string created by the VM

        Args:
            s: Pointer to the string to free
        """
        if self.available and s:
            self._lib.stoffel_free_string(s)


# ==============================================================================
# High-Level VM Wrapper
# ==============================================================================

class VirtualMachine:
    """
    High-level wrapper around StoffelVM FFI

    Provides a Pythonic interface with automatic resource management.

    Usage:
        with VirtualMachine() as vm:
            vm.load_bytecode(bytecode)
            result = vm.execute("main")
    """

    def __init__(self):
        self._ffi = get_vm_ffi()
        if not self._ffi.available:
            raise LibraryLoadError("StoffelVM library not available")

        self._handle = self._ffi.create_vm()

    def __enter__(self) -> "VirtualMachine":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Destroy the VM instance"""
        if self._handle:
            self._ffi.destroy_vm(self._handle)
            self._handle = None

    def load_bytecode(self, bytecode: bytes) -> None:
        """Load compiled bytecode into the VM"""
        if not self._handle:
            raise VMError("VM has been closed")
        self._ffi.load_bytecode(self._handle, bytecode)

    def execute(self, function_name: str) -> Any:
        """Execute a function and return the result"""
        if not self._handle:
            raise VMError("VM has been closed")
        return self._ffi.execute(self._handle, function_name)

    def execute_with_args(self, function_name: str, args: List[Any]) -> Any:
        """Execute a function with arguments and return the result"""
        if not self._handle:
            raise VMError("VM has been closed")
        return self._ffi.execute_with_args(self._handle, function_name, args)

    def register_function(self, name: str, callback: Callable[[List[Any]], Any]) -> None:
        """Register a Python function as a foreign function"""
        if not self._handle:
            raise VMError("VM has been closed")
        self._ffi.register_foreign_function(self._handle, name, callback)


# ==============================================================================
# Global Singleton Access
# ==============================================================================

_vm_ffi: Optional[VMFunctions] = None


def get_vm_ffi() -> VMFunctions:
    """Get the StoffelVM FFI singleton"""
    global _vm_ffi
    if _vm_ffi is None:
        _vm_ffi = VMFunctions()
    return _vm_ffi


def is_vm_available() -> bool:
    """Check if StoffelVM FFI is available"""
    return get_vm_ffi().available
