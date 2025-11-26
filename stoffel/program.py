"""
Stoffel Program Management

This module handles StoffelLang program compilation, VM setup, and execution parameters.
The VM is responsible for program compilation, loading, and defining execution parameters.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import uuid

from .compiler import StoffelCompiler, CompilerOptions
from .vm import VirtualMachine


class StoffelProgram:
    """
    Manages a StoffelLang program and its execution in the VM
    
    Handles:
    - Program compilation
    - VM setup and configuration  
    - Execution parameter definition
    - Program lifecycle management
    """
    
    def __init__(
        self,
        source_path: Optional[str] = None,
        vm_library_path: Optional[str] = None
    ):
        """
        Initialize program manager
        
        Args:
            source_path: Path to .stfl source file (optional, can compile later)
            vm_library_path: Path to StoffelVM shared library
        """
        self.compiler = StoffelCompiler()
        self.vm = VirtualMachine(vm_library_path)
        
        self.source_path = source_path
        self.binary_path = None
        self.program_id = None
        self.execution_params = {}
        self.program_loaded = False
        
        if source_path:
            self.program_id = self._generate_program_id(source_path)
    
    def compile(
        self, 
        source_path: Optional[str] = None,
        output_path: Optional[str] = None,
        optimize: bool = False
    ) -> str:
        """
        Compile StoffelLang source to VM bytecode
        
        Args:
            source_path: Path to .stfl source (uses initialized path if None)
            output_path: Output path for .stfb binary
            optimize: Enable compiler optimizations
            
        Returns:
            Path to compiled binary
        """
        if source_path:
            self.source_path = source_path
            self.program_id = self._generate_program_id(source_path)
        
        if not self.source_path:
            raise ValueError("No source path specified")
        
        if not os.path.exists(self.source_path):
            raise FileNotFoundError(f"Source file not found: {self.source_path}")
        
        # Determine output path
        if output_path is None:
            output_path = str(Path(self.source_path).with_suffix('.stfb'))
        
        # Compile with specified options
        options = CompilerOptions(optimize=optimize)
        compiled_program = self.compiler.compile_file(
            self.source_path, 
            output_path, 
            options
        )
        
        self.binary_path = output_path
        print(f"Compiled {self.source_path} -> {self.binary_path}")
        
        return output_path
    
    def load_program(self, binary_path: Optional[str] = None) -> None:
        """
        Load compiled program into VM
        
        Args:
            binary_path: Path to .stfb binary (uses compiled path if None)
        """
        if binary_path:
            self.binary_path = binary_path
        
        if not self.binary_path:
            raise ValueError("No binary path specified. Compile first or provide path.")
        
        if not os.path.exists(self.binary_path):
            raise FileNotFoundError(f"Binary file not found: {self.binary_path}")
        
        # Load into VM
        self.vm.load_binary(self.binary_path)
        self.program_loaded = True
        
        print(f"Loaded program {self.program_id} into VM")
    
    def set_execution_params(self, params: Dict[str, Any]) -> None:
        """
        Define parameters needed for MPC program execution
        
        Args:
            params: Execution parameters for the MPC program
                   {
                       "computation_id": "secure_addition",
                       "input_mapping": {
                           "param_a": "input1", 
                           "param_b": "input2"
                       },
                       "function_name": "main",
                       "expected_inputs": ["input1", "input2"],
                       "mpc_protocol": "honeybadger",
                       "threshold": 2,
                       "num_parties": 3
                   }
        """
        self.execution_params.update(params)
        print(f"Set execution parameters for {self.program_id}")
    
    def get_computation_id(self) -> str:
        """
        Get the computation ID for this program
        
        Returns:
            Computation ID for MPC network
        """
        return self.execution_params.get("computation_id", self.program_id or "unknown")
    
    def get_expected_inputs(self) -> List[str]:
        """
        Get list of expected private inputs for this program
        
        Returns:
            List of input parameter names
        """
        return self.execution_params.get("expected_inputs", [])
    
    def get_input_mapping(self) -> Dict[str, str]:
        """
        Get mapping from program parameters to client input names
        
        Returns:
            Dictionary mapping program params to input names
        """
        return self.execution_params.get("input_mapping", {})
    
    def execute_locally(self, inputs: Dict[str, Any]) -> Any:
        """
        Execute program locally in VM (for testing/debugging)
        
        Args:
            inputs: Input values for local execution
            
        Returns:
            Local execution result
        """
        if not self.program_loaded:
            raise RuntimeError("Program not loaded. Call load_program() first.")
        
        function_name = self.execution_params.get("function_name", "main")
        
        # Map inputs according to input_mapping if provided
        input_mapping = self.get_input_mapping()
        if input_mapping:
            mapped_inputs = []
            for param_name in self.get_expected_inputs():
                input_name = input_mapping.get(param_name, param_name)
                if input_name in inputs:
                    mapped_inputs.append(inputs[input_name])
                else:
                    raise ValueError(f"Missing input '{input_name}' for parameter '{param_name}'")
            
            if mapped_inputs:
                return self.vm.execute_with_args(function_name, mapped_inputs)
            else:
                return self.vm.execute(function_name)
        else:
            # Direct input passing
            input_values = list(inputs.values())
            if input_values:
                return self.vm.execute_with_args(function_name, input_values)
            else:
                return self.vm.execute(function_name)
    
    def get_program_info(self) -> Dict[str, Any]:
        """
        Get information about the program
        
        Returns:
            Program metadata and status
        """
        return {
            "program_id": self.program_id,
            "source_path": self.source_path,
            "binary_path": self.binary_path,
            "program_loaded": self.program_loaded,
            "computation_id": self.get_computation_id(),
            "expected_inputs": self.get_expected_inputs(),
            "execution_params": self.execution_params
        }
    
    def _generate_program_id(self, source_path: str) -> str:
        """
        Generate a unique program ID from source path
        
        Args:
            source_path: Path to source file
            
        Returns:
            Unique program identifier
        """
        filename = Path(source_path).stem
        return f"{filename}_{uuid.uuid4().hex[:8]}"


def compile_stoffel_program(
    source_path: str,
    output_path: Optional[str] = None,
    optimize: bool = False
) -> str:
    """
    Convenience function to compile a StoffelLang program
    
    Args:
        source_path: Path to .stfl source file
        output_path: Output path for .stfb binary
        optimize: Enable optimizations
        
    Returns:
        Path to compiled binary
    """
    program = StoffelProgram()
    return program.compile(source_path, output_path, optimize)