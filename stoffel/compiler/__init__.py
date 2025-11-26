"""
Stoffel compiler integration for Python SDK

This module provides Python bindings for the Stoffel compiler,
enabling compilation of .stfl source files to VM bytecode and
execution of compiled programs.
"""

from .compiler import StoffelCompiler, CompilerOptions
from .program import CompiledProgram, ProgramLoader
from .exceptions import CompilerError, CompilationError, LoadError

__all__ = [
    'StoffelCompiler',
    'CompilerOptions',
    'CompiledProgram',
    'ProgramLoader',
    'CompilerError',
    'CompilationError',
    'LoadError'
]