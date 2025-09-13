"""
Exception classes for StoffelVM Python bindings
"""


class VMError(Exception):
    """Base exception class for StoffelVM errors"""
    pass


class ExecutionError(VMError):
    """Exception raised when VM function execution fails"""
    pass


class RegistrationError(VMError):
    """Exception raised when foreign function registration fails"""
    pass


class MemoryError(VMError):
    """Exception raised when VM memory operations fail"""
    pass


class ConversionError(VMError):
    """Exception raised when type conversion fails"""
    pass