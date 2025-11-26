"""
Python bindings for StoffelVM

This module provides a high-level Python interface to StoffelVM through CFFI.
"""

import ctypes
from typing import Any, Callable, Dict, List, Optional, Union
from ctypes import Structure, Union as CUnion, c_void_p, c_char_p, c_int, c_int64, c_double, c_bool, c_size_t

from .types import StoffelValue, ValueType, ShareType
from .exceptions import VMError, ExecutionError, RegistrationError, ConversionError


# C structure definitions matching the C header
class ShareData(Structure):
    _fields_ = [
        ("share_type", c_int),
        ("share_bytes", c_void_p),
        ("share_len", c_size_t),
    ]

class StoffelValueData(CUnion):
    _fields_ = [
        ("int_val", c_int64),
        ("float_val", c_double),
        ("bool_val", c_bool),
        ("string_val", c_char_p),
        ("object_id", c_size_t),
        ("array_id", c_size_t),
        ("foreign_id", c_size_t),
        ("closure_id", c_size_t),
        ("share", ShareData),
    ]


class CStoffelValue(Structure):
    _fields_ = [
        ("value_type", c_int),
        ("data", StoffelValueData),
    ]


# C function pointer type for foreign functions
CForeignFunctionType = ctypes.CFUNCTYPE(
    c_int,                    # return type
    ctypes.POINTER(CStoffelValue),  # args
    c_int,                    # arg_count
    ctypes.POINTER(CStoffelValue),  # result
)


class VirtualMachine:
    """
    Python wrapper for StoffelVM
    
    This class provides a high-level interface to StoffelVM, handling
    VM creation, function execution, and foreign function registration.
    """
    
    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize a new StoffelVM instance
        
        Args:
            library_path: Path to the StoffelVM shared library.
                         If None, attempts to find it in standard locations.
        """
        self._load_library(library_path)
        self._vm_handle = self._lib.stoffel_create_vm()
        if not self._vm_handle:
            raise VMError("Failed to create VM instance")
        
        # Keep references to registered functions to prevent GC
        self._registered_functions: Dict[str, Callable] = {}
    
    def _load_library(self, library_path: Optional[str]):
        """Load the StoffelVM shared library"""
        if library_path:
            self._lib = ctypes.CDLL(library_path)
        else:
            # Try common library names/paths
            try:
                self._lib = ctypes.CDLL("./libstoffel_vm.so")
            except OSError:
                try:
                    self._lib = ctypes.CDLL("libstoffel_vm.so")
                except OSError:
                    try:
                        self._lib = ctypes.CDLL("./libstoffel_vm.dylib")
                    except OSError:
                        self._lib = ctypes.CDLL("libstoffel_vm.dylib")
        
        # Set up function signatures
        self._setup_function_signatures()
    
    def _setup_function_signatures(self):
        """Set up C function signatures"""
        # stoffel_create_vm
        self._lib.stoffel_create_vm.argtypes = []
        self._lib.stoffel_create_vm.restype = c_void_p
        
        # stoffel_destroy_vm
        self._lib.stoffel_destroy_vm.argtypes = [c_void_p]
        self._lib.stoffel_destroy_vm.restype = None
        
        # stoffel_execute
        self._lib.stoffel_execute.argtypes = [c_void_p, c_char_p, ctypes.POINTER(CStoffelValue)]
        self._lib.stoffel_execute.restype = c_int
        
        # stoffel_execute_with_args
        self._lib.stoffel_execute_with_args.argtypes = [
            c_void_p, c_char_p, ctypes.POINTER(CStoffelValue), c_int, ctypes.POINTER(CStoffelValue)
        ]
        self._lib.stoffel_execute_with_args.restype = c_int
        
        # stoffel_register_foreign_function
        self._lib.stoffel_register_foreign_function.argtypes = [c_void_p, c_char_p, CForeignFunctionType]
        self._lib.stoffel_register_foreign_function.restype = c_int
        
        # stoffel_register_foreign_object
        self._lib.stoffel_register_foreign_object.argtypes = [c_void_p, c_void_p, ctypes.POINTER(CStoffelValue)]
        self._lib.stoffel_register_foreign_object.restype = c_int
        
        # stoffel_create_string
        self._lib.stoffel_create_string.argtypes = [c_void_p, c_char_p, ctypes.POINTER(CStoffelValue)]
        self._lib.stoffel_create_string.restype = c_int
        
        # stoffel_free_string
        self._lib.stoffel_free_string.argtypes = [c_char_p]
        self._lib.stoffel_free_string.restype = None
        
        # MPC engine functions
        # stoffel_input_share
        self._lib.stoffel_input_share.argtypes = [c_void_p, c_int, ctypes.POINTER(CStoffelValue), ctypes.POINTER(CStoffelValue)]
        self._lib.stoffel_input_share.restype = c_int
        
        # stoffel_multiply_share
        self._lib.stoffel_multiply_share.argtypes = [c_void_p, c_int, c_void_p, c_size_t, c_void_p, c_size_t, ctypes.POINTER(CStoffelValue)]
        self._lib.stoffel_multiply_share.restype = c_int
        
        # stoffel_open_share
        self._lib.stoffel_open_share.argtypes = [c_void_p, c_int, c_void_p, c_size_t, ctypes.POINTER(CStoffelValue)]
        self._lib.stoffel_open_share.restype = c_int
        
        # stoffel_load_binary
        self._lib.stoffel_load_binary.argtypes = [c_void_p, c_char_p]
        self._lib.stoffel_load_binary.restype = c_int
    
    def __del__(self):
        """Cleanup VM instance"""
        if hasattr(self, '_vm_handle') and self._vm_handle:
            self._lib.stoffel_destroy_vm(self._vm_handle)
    
    def execute(self, function_name: str) -> Any:
        """
        Execute a VM function without arguments
        
        Args:
            function_name: Name of the function to execute
            
        Returns:
            The function's return value converted to Python type
            
        Raises:
            ExecutionError: If function execution fails
        """
        result = CStoffelValue()
        status = self._lib.stoffel_execute(
            self._vm_handle,
            function_name.encode('utf-8'),
            ctypes.byref(result)
        )
        
        if status != 0:
            raise ExecutionError(f"Function execution failed with status {status}")
        
        return self._c_value_to_python(result)
    
    def execute_with_args(self, function_name: str, args: List[Any]) -> Any:
        """
        Execute a VM function with arguments
        
        Args:
            function_name: Name of the function to execute
            args: List of arguments to pass to the function
            
        Returns:
            The function's return value converted to Python type
            
        Raises:
            ExecutionError: If function execution fails
        """
        # Convert Python args to C args
        c_args = (CStoffelValue * len(args))()
        for i, arg in enumerate(args):
            c_args[i] = self._python_value_to_c(arg)
        
        result = CStoffelValue()
        status = self._lib.stoffel_execute_with_args(
            self._vm_handle,
            function_name.encode('utf-8'),
            c_args,
            len(args),
            ctypes.byref(result)
        )
        
        if status != 0:
            raise ExecutionError(f"Function execution failed with status {status}")
        
        return self._c_value_to_python(result)
    
    def register_foreign_function(self, name: str, func: Callable) -> None:
        """
        Register a Python function as a foreign function in the VM
        
        Args:
            name: Name to register the function under
            func: Python function to register
            
        Raises:
            RegistrationError: If function registration fails
        """
        def c_wrapper(args_ptr, arg_count, result_ptr):
            try:
                # Convert C args to Python
                python_args = []
                for i in range(arg_count):
                    c_arg = args_ptr[i]
                    python_args.append(self._c_value_to_python(c_arg))
                
                # Call Python function
                python_result = func(*python_args)
                
                # Convert result back to C
                c_result = self._python_value_to_c(python_result)
                result_ptr.contents = c_result
                
                return 0
            except Exception:
                return -1
        
        c_func = CForeignFunctionType(c_wrapper)
        status = self._lib.stoffel_register_foreign_function(
            self._vm_handle,
            name.encode('utf-8'),
            c_func
        )
        
        if status != 0:
            raise RegistrationError(f"Failed to register function '{name}' with status {status}")
        
        # Keep reference to prevent GC
        self._registered_functions[name] = (func, c_func)
    
    def register_foreign_object(self, obj: Any) -> int:
        """
        Register a Python object as a foreign object in the VM
        
        Args:
            obj: Python object to register
            
        Returns:
            Foreign object ID
            
        Raises:
            RegistrationError: If object registration fails
        """
        # Create a pointer to the Python object
        obj_ptr = ctypes.cast(id(obj), c_void_p)
        
        result = CStoffelValue()
        status = self._lib.stoffel_register_foreign_object(
            self._vm_handle,
            obj_ptr,
            ctypes.byref(result)
        )
        
        if status != 0:
            raise RegistrationError(f"Failed to register foreign object with status {status}")
        
        return result.data.foreign_id
    
    def create_string(self, value: str) -> StoffelValue:
        """
        Create a VM string from a Python string
        
        Args:
            value: Python string to convert
            
        Returns:
            StoffelValue representing the string
            
        Raises:
            ConversionError: If string creation fails
        """
        result = CStoffelValue()
        status = self._lib.stoffel_create_string(
            self._vm_handle,
            value.encode('utf-8'),
            ctypes.byref(result)
        )
        
        if status != 0:
            raise ConversionError(f"Failed to create string with status {status}")
        
        return self._c_value_to_stoffel_value(result)
    
    def _python_value_to_c(self, value: Any) -> CStoffelValue:
        """Convert Python value to C StoffelValue"""
        c_value = CStoffelValue()
        
        if value is None:
            c_value.value_type = ValueType.UNIT
        elif isinstance(value, int):
            c_value.value_type = ValueType.INT
            c_value.data.int_val = value
        elif isinstance(value, float):
            c_value.value_type = ValueType.FLOAT
            c_value.data.float_val = value
        elif isinstance(value, bool):
            c_value.value_type = ValueType.BOOL
            c_value.data.bool_val = value
        elif isinstance(value, str):
            c_value.value_type = ValueType.STRING
            c_value.data.string_val = value.encode('utf-8')
        elif isinstance(value, StoffelValue):
            return self._stoffel_value_to_c(value)
        elif isinstance(value, tuple) and len(value) == 2:
            # Handle (ShareType, bytes) tuples directly
            share_type, share_bytes = value
            if isinstance(share_type, ShareType) and isinstance(share_bytes, bytes):
                c_value.value_type = ValueType.SHARE
                c_value.data.share.share_type = share_type
                c_value.data.share.share_bytes = ctypes.cast(ctypes.c_char_p(share_bytes), c_void_p)
                c_value.data.share.share_len = len(share_bytes)
            else:
                raise ConversionError(f"Invalid share tuple: ({type(share_type)}, {type(share_bytes)})")
        else:
            raise ConversionError(f"Cannot convert {type(value)} to StoffelValue")
        
        return c_value
    
    def _stoffel_value_to_c(self, value: StoffelValue) -> CStoffelValue:
        """Convert StoffelValue to C StoffelValue"""
        c_value = CStoffelValue()
        c_value.value_type = value.value_type
        
        if value.value_type == ValueType.UNIT:
            pass  # No data needed
        elif value.value_type == ValueType.INT:
            c_value.data.int_val = value.data
        elif value.value_type == ValueType.FLOAT:
            c_value.data.float_val = value.data
        elif value.value_type == ValueType.BOOL:
            c_value.data.bool_val = value.data
        elif value.value_type == ValueType.STRING:
            c_value.data.string_val = value.data.encode('utf-8')
        elif value.value_type == ValueType.OBJECT:
            c_value.data.object_id = value.data
        elif value.value_type == ValueType.ARRAY:
            c_value.data.array_id = value.data
        elif value.value_type == ValueType.FOREIGN:
            c_value.data.foreign_id = value.data
        elif value.value_type == ValueType.SHARE:
            share_type, share_bytes = value.data
            c_value.data.share.share_type = share_type
            c_value.data.share.share_bytes = ctypes.cast(ctypes.c_char_p(share_bytes), c_void_p)
            c_value.data.share.share_len = len(share_bytes)
        
        return c_value
    
    def _c_value_to_python(self, c_value: CStoffelValue) -> Any:
        """Convert C StoffelValue to Python value"""
        if c_value.value_type == ValueType.UNIT:
            return None
        elif c_value.value_type == ValueType.INT:
            return c_value.data.int_val
        elif c_value.value_type == ValueType.FLOAT:
            return c_value.data.float_val
        elif c_value.value_type == ValueType.BOOL:
            return c_value.data.bool_val
        elif c_value.value_type == ValueType.STRING:
            return c_value.data.string_val.decode('utf-8')
        elif c_value.value_type == ValueType.OBJECT:
            return c_value.data.object_id
        elif c_value.value_type == ValueType.ARRAY:
            return c_value.data.array_id
        elif c_value.value_type == ValueType.FOREIGN:
            return c_value.data.foreign_id
        elif c_value.value_type == ValueType.SHARE:
            share_type = ShareType(c_value.data.share.share_type)
            share_len = c_value.data.share.share_len
            share_bytes = ctypes.string_at(c_value.data.share.share_bytes, share_len)
            return (share_type, share_bytes)
        else:
            raise ConversionError(f"Unknown value type: {c_value.value_type}")
    
    def _c_value_to_stoffel_value(self, c_value: CStoffelValue) -> StoffelValue:
        """Convert C StoffelValue to StoffelValue"""
        value_type = ValueType(c_value.value_type)
        data = self._c_value_to_python(c_value)
        return StoffelValue(value_type, data)
    
    def input_share(self, share_type: ShareType, clear_value: Any) -> StoffelValue:
        """
        Convert a clear value into a secret share
        
        Args:
            share_type: Type of share to create
            clear_value: Clear value to convert to share
            
        Returns:
            StoffelValue representing the secret share
            
        Raises:
            ExecutionError: If share creation fails
        """
        c_clear = self._python_value_to_c(clear_value)
        result = CStoffelValue()
        
        status = self._lib.stoffel_input_share(
            self._vm_handle,
            share_type,
            ctypes.byref(c_clear),
            ctypes.byref(result)
        )
        
        if status != 0:
            raise ExecutionError(f"Input share failed with status {status}")
            
        return self._c_value_to_stoffel_value(result)
    
    def multiply_share(self, share_type: ShareType, left_share: bytes, right_share: bytes) -> StoffelValue:
        """
        Multiply two secret shares
        
        Args:
            share_type: Type of shares being multiplied
            left_share: First share bytes
            right_share: Second share bytes
            
        Returns:
            StoffelValue representing the result share
            
        Raises:
            ExecutionError: If multiplication fails
        """
        result = CStoffelValue()
        
        status = self._lib.stoffel_multiply_share(
            self._vm_handle,
            share_type,
            ctypes.c_char_p(left_share),
            len(left_share),
            ctypes.c_char_p(right_share),
            len(right_share),
            ctypes.byref(result)
        )
        
        if status != 0:
            raise ExecutionError(f"Multiply share failed with status {status}")
            
        return self._c_value_to_stoffel_value(result)
    
    def open_share(self, share_type: ShareType, share_bytes: bytes) -> Any:
        """
        Open (reveal) a secret share as a clear value
        
        Args:
            share_type: Type of share being opened
            share_bytes: Share bytes to reveal
            
        Returns:
            The revealed clear value
            
        Raises:
            ExecutionError: If opening fails
        """
        result = CStoffelValue()
        
        status = self._lib.stoffel_open_share(
            self._vm_handle,
            share_type,
            ctypes.c_char_p(share_bytes),
            len(share_bytes),
            ctypes.byref(result)
        )
        
        if status != 0:
            raise ExecutionError(f"Open share failed with status {status}")
            
        return self._c_value_to_python(result)
    
    def load_binary(self, binary_path: str) -> None:
        """
        Load a compiled StoffelLang binary into the VM
        
        Args:
            binary_path: Path to the .stfb binary file
            
        Raises:
            ExecutionError: If binary loading fails
        """
        status = self._lib.stoffel_load_binary(
            self._vm_handle,
            binary_path.encode('utf-8')
        )
        
        if status != 0:
            raise ExecutionError(f"Binary loading failed with status {status}")