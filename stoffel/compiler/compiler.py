"""
StoffelLang compiler integration

This module provides a Python interface to the StoffelLang compiler,
allowing compilation of .stfl source files to VM bytecode.
"""

import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .exceptions import CompilationError, LoadError
from .program import CompiledProgram


@dataclass
class CompilerOptions:
    """Configuration options for StoffelLang compilation"""
    optimize: bool = False
    optimization_level: int = 0
    print_ir: bool = False
    output_path: Optional[str] = None


class StoffelCompiler:
    """
    Python interface to the StoffelLang compiler
    
    This class provides methods to compile StoffelLang source code
    to VM-compatible bytecode and load compiled programs.
    """
    
    def __init__(self, compiler_path: Optional[str] = None):
        """
        Initialize the StoffelLang compiler interface
        
        Args:
            compiler_path: Path to the stoffellang compiler binary.
                          If None, attempts to find it in standard locations.
        """
        self.compiler_path = self._find_compiler(compiler_path)
        if not self.compiler_path:
            raise CompilationError("StoffelLang compiler not found. Please ensure it's installed and accessible.")
    
    def _find_compiler(self, compiler_path: Optional[str]) -> Optional[str]:
        """Find the StoffelLang compiler binary"""
        if compiler_path and os.path.isfile(compiler_path):
            return compiler_path
        
        # Try common locations
        search_paths = [
            "./stoffellang",
            "./target/release/stoffellang",
            "./target/debug/stoffellang",
            shutil.which("stoffellang"),
            "/usr/local/bin/stoffellang",
        ]
        
        # Also check in the Stoffel-Lang directory if it exists
        stoffel_lang_path = os.path.expanduser("~/Documents/Stoffel-Labs/dev/Stoffel-Lang")
        if os.path.exists(stoffel_lang_path):
            search_paths.extend([
                os.path.join(stoffel_lang_path, "target/release/stoffellang"),
                os.path.join(stoffel_lang_path, "target/debug/stoffellang"),
            ])
        
        for path in search_paths:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return None
    
    def compile_source(
        self,
        source_code: str,
        filename: str = "main.stfl",
        options: Optional[CompilerOptions] = None
    ) -> CompiledProgram:
        """
        Compile StoffelLang source code to VM bytecode
        
        Args:
            source_code: The StoffelLang source code to compile
            filename: Name for the source file (used in error messages)
            options: Compilation options
            
        Returns:
            CompiledProgram object containing the bytecode
            
        Raises:
            CompilationError: If compilation fails
        """
        options = options or CompilerOptions()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write source to temporary file
            source_file = os.path.join(temp_dir, filename)
            with open(source_file, 'w') as f:
                f.write(source_code)
            
            # Compile to binary
            binary_file = os.path.join(temp_dir, f"{Path(filename).stem}.stfb")
            self._compile_file(source_file, binary_file, options)
            
            # Load the compiled binary
            return CompiledProgram.load_from_file(binary_file)
    
    def compile_file(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        options: Optional[CompilerOptions] = None
    ) -> CompiledProgram:
        """
        Compile a StoffelLang source file to VM bytecode
        
        Args:
            source_path: Path to the .stfl source file
            output_path: Path for the output .stfb file. If None, uses source path with .stfb extension
            options: Compilation options
            
        Returns:
            CompiledProgram object containing the bytecode
            
        Raises:
            CompilationError: If compilation fails
            FileNotFoundError: If source file doesn't exist
        """
        options = options or CompilerOptions()
        
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Determine output path
        if output_path is None:
            output_path = str(Path(source_path).with_suffix('.stfb'))
        elif options.output_path:
            output_path = options.output_path
        
        # Compile
        self._compile_file(source_path, output_path, options)
        
        # Load and return the compiled program
        return CompiledProgram.load_from_file(output_path)
    
    def _compile_file(self, source_path: str, output_path: str, options: CompilerOptions):
        """Internal method to run the compiler"""
        # Build compiler command
        cmd = [self.compiler_path, source_path, '-b']  # -b for binary output
        
        if options.output_path or output_path != str(Path(source_path).with_suffix('.stfb')):
            cmd.extend(['-o', output_path])
        
        if options.optimize:
            cmd.append('--optimize')
        elif options.optimization_level > 0:
            cmd.extend(['-O', str(options.optimization_level)])
        
        if options.print_ir:
            cmd.append('--print-ir')
        
        # Run compiler
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                error_lines = result.stderr.strip().split('\n') if result.stderr else []
                raise CompilationError(
                    f"Compilation failed with exit code {result.returncode}",
                    errors=error_lines
                )
            
            # Check that output file was created
            if not os.path.exists(output_path):
                raise CompilationError("Compiler succeeded but no output file was generated")
                
        except subprocess.SubprocessError as e:
            raise CompilationError(f"Failed to run compiler: {e}")
    
    def get_compiler_version(self) -> str:
        """Get the version of the StoffelLang compiler"""
        try:
            result = subprocess.run(
                [self.compiler_path, '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.SubprocessError:
            return "Unknown version"
    
    def validate_syntax(self, source_code: str, filename: str = "main.stfl") -> List[str]:
        """
        Validate StoffelLang syntax without generating bytecode
        
        Args:
            source_code: The StoffelLang source code to validate
            filename: Name for the source file (used in error messages)
            
        Returns:
            List of validation errors (empty if valid)
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                source_file = os.path.join(temp_dir, filename)
                with open(source_file, 'w') as f:
                    f.write(source_code)
                
                # Try to compile with print-ir flag (doesn't generate binary)
                options = CompilerOptions(print_ir=True)
                temp_output = os.path.join(temp_dir, "temp.stfb")
                self._compile_file(source_file, temp_output, options)
                
                return []  # No errors
                
        except CompilationError as e:
            return e.errors
        except Exception:
            return ["Unknown validation error"]