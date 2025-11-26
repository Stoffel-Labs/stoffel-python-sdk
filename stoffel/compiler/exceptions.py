"""
Exceptions for StoffelLang compiler integration
"""

from typing import List, Optional


class CompilerError(Exception):
    """Base exception for compiler-related errors"""
    pass


class CompilationError(CompilerError):
    """Raised when StoffelLang compilation fails"""
    
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or []
        
    def __str__(self):
        if self.errors:
            error_details = '\n'.join(f"  - {error}" for error in self.errors)
            return f"{super().__str__()}\nCompilation errors:\n{error_details}"
        return super().__str__()


class LoadError(CompilerError):
    """Raised when loading a compiled binary fails"""
    pass