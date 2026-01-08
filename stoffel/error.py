"""
Stoffel SDK Error Hierarchy

Unified exception classes matching the Rust SDK error types.
These errors are raised by the high-level SDK API.
"""

from typing import Optional


class StoffelError(Exception):
    """Base error for all Stoffel SDK operations"""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message}: {self.cause}"
        return self.message


class CompilationError(StoffelError):
    """Error during StoffelLang compilation

    Raised when source code fails to compile due to syntax errors,
    type errors, or other compilation issues.
    """
    pass


class StoffelRuntimeError(StoffelError):
    """Error during VM execution

    Raised when bytecode execution fails in the StoffelVM.
    Note: Named StoffelRuntimeError to avoid shadowing built-in RuntimeError.
    """
    pass


class MPCError(StoffelError):
    """Error during MPC operations

    Raised when MPC protocol operations fail, including
    preprocessing, computation, and output reconstruction.
    """
    pass


class ConfigurationError(StoffelError):
    """Invalid SDK configuration

    Raised when MPC parameters violate constraints (e.g., n < 3t+1)
    or when required configuration is missing.
    """
    pass


class NetworkError(StoffelError):
    """Network communication error

    Raised when network operations fail, including connection
    errors, timeouts, and protocol errors.
    """
    pass


class InvalidInputError(StoffelError):
    """Invalid input provided

    Raised when inputs don't match expected types or constraints.
    """
    pass


class FunctionNotFoundError(StoffelError):
    """Function not found in program

    Raised when attempting to execute a function that doesn't
    exist in the compiled bytecode.
    """

    def __init__(self, function_name: str):
        super().__init__(f"Function '{function_name}' not found in program")
        self.function_name = function_name


class PreprocessingError(MPCError):
    """Error during MPC preprocessing

    Raised when Beaver triple generation or random share
    generation fails.
    """
    pass


class ComputationError(MPCError):
    """Error during MPC computation

    Raised when secure multiplication or other MPC operations fail.
    """
    pass


class IoError(StoffelError):
    """File I/O error

    Raised when file operations fail (reading source, saving bytecode, etc.)
    """
    pass
