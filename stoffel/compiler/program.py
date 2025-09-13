"""
Compiled StoffelLang program representation and loading

This module handles loading and representing compiled StoffelLang programs
(.stfb files) for execution on the VM.
"""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..vm import VirtualMachine
from .exceptions import LoadError


class CompiledProgram:
    """
    Represents a compiled StoffelLang program
    
    This class wraps a compiled .stfb binary and provides methods
    to execute functions and interact with the program.
    """
    
    def __init__(self, binary_path: str, vm: Optional[VirtualMachine] = None):
        """
        Initialize a compiled program
        
        Args:
            binary_path: Path to the .stfb binary file
            vm: VirtualMachine instance to use. If None, creates a new one.
        """
        self.binary_path = binary_path
        self.vm = vm or VirtualMachine()
        self._functions: Dict[str, Any] = {}
        self._loaded = False
    
    @classmethod
    def load_from_file(cls, binary_path: str) -> "CompiledProgram":
        """
        Load a compiled program from a .stfb file
        
        Args:
            binary_path: Path to the .stfb binary file
            
        Returns:
            CompiledProgram instance
            
        Raises:
            LoadError: If the file cannot be loaded
        """
        if not os.path.exists(binary_path):
            raise LoadError(f"Binary file not found: {binary_path}")
        
        program = cls(binary_path)
        program._load_binary()
        return program
    
    def _load_binary(self):
        """Load the binary into the VM"""
        try:
            # Load the compiled binary into the VM
            self.vm.load_binary(self.binary_path)
            self._loaded = True
            
        except Exception as e:
            raise LoadError(f"Failed to load binary {self.binary_path}: {e}")
    
    def execute_main(self, *args) -> Any:
        """
        Execute the main function of the program
        
        Args:
            *args: Arguments to pass to the main function
            
        Returns:
            The result of the main function execution
            
        Raises:
            LoadError: If the program is not loaded
        """
        if not self._loaded:
            raise LoadError("Program not loaded")
        
        try:
            if args:
                return self.vm.execute_with_args("main", list(args))
            else:
                return self.vm.execute("main")
        except Exception as e:
            raise LoadError(f"Failed to execute main function: {e}")
    
    def execute_function(self, function_name: str, *args) -> Any:
        """
        Execute a specific function in the program
        
        Args:
            function_name: Name of the function to execute
            *args: Arguments to pass to the function
            
        Returns:
            The result of the function execution
        """
        if not self._loaded:
            raise LoadError("Program not loaded")
        
        try:
            if args:
                return self.vm.execute_with_args(function_name, list(args))
            else:
                return self.vm.execute(function_name)
        except Exception as e:
            raise LoadError(f"Failed to execute function '{function_name}': {e}")
    
    def list_functions(self) -> List[str]:
        """
        Get a list of available functions in the program
        
        Returns:
            List of function names
        """
        # This would need to be implemented by parsing the binary
        # or having the VM expose function metadata
        return ["main"]  # Placeholder
    
    def get_program_info(self) -> Dict[str, Any]:
        """
        Get information about the compiled program
        
        Returns:
            Dictionary containing program metadata
        """
        return {
            "binary_path": self.binary_path,
            "loaded": self._loaded,
            "size": os.path.getsize(self.binary_path) if os.path.exists(self.binary_path) else 0,
            "functions": self.list_functions()
        }


class ProgramLoader:
    """
    Utility class for loading and managing multiple compiled programs
    """
    
    def __init__(self, vm: Optional[VirtualMachine] = None):
        """
        Initialize the program loader
        
        Args:
            vm: Shared VirtualMachine instance. If None, each program gets its own VM.
        """
        self.shared_vm = vm
        self.programs: Dict[str, CompiledProgram] = {}
    
    def load_program(self, name: str, binary_path: str) -> CompiledProgram:
        """
        Load a program and register it with a name
        
        Args:
            name: Name to register the program under
            binary_path: Path to the .stfb binary file
            
        Returns:
            The loaded CompiledProgram
        """
        vm = self.shared_vm or VirtualMachine()
        program = CompiledProgram(binary_path, vm)
        program._load_binary()
        
        self.programs[name] = program
        return program
    
    def get_program(self, name: str) -> Optional[CompiledProgram]:
        """Get a loaded program by name"""
        return self.programs.get(name)
    
    def list_programs(self) -> List[str]:
        """Get list of loaded program names"""
        return list(self.programs.keys())
    
    def unload_program(self, name: str) -> bool:
        """
        Unload a program
        
        Args:
            name: Name of the program to unload
            
        Returns:
            True if program was unloaded, False if not found
        """
        if name in self.programs:
            del self.programs[name]
            return True
        return False
    
    def execute_in_program(self, program_name: str, function_name: str, *args) -> Any:
        """
        Execute a function in a specific loaded program
        
        Args:
            program_name: Name of the program
            function_name: Name of the function to execute
            *args: Arguments to pass to the function
            
        Returns:
            The result of the function execution
            
        Raises:
            LoadError: If the program is not found
        """
        program = self.get_program(program_name)
        if not program:
            raise LoadError(f"Program '{program_name}' not found")
        
        return program.execute_function(function_name, *args)