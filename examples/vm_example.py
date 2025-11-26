"""
Example usage of StoffelVM Python bindings

This example demonstrates how to use the StoffelVM Python SDK to:
1. Create a VM instance
2. Register foreign functions
3. Execute VM functions
4. Handle different value types
"""

import sys
import os

# Add the parent directory to the path so we can import stoffel
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stoffel import VirtualMachine
from stoffel.vm.types import StoffelValue
from stoffel.vm.exceptions import VMError


def math_add(a: int, b: int) -> int:
    """Simple addition function to register as foreign function"""
    return a + b


def string_processor(s: str) -> str:
    """Process a string and return it uppercased"""
    return s.upper()


def main():
    """Main example function"""
    print("StoffelVM Python SDK Example")
    print("=" * 40)
    
    try:
        # Create a VM instance
        # In a real scenario, you would specify the path to libstoffel_vm.so
        print("Creating VM instance...")
        vm = VirtualMachine()  # library_path="path/to/libstoffel_vm.so"
        print("VM created successfully!")
        
        # Register foreign functions
        print("\nRegistering foreign functions...")
        vm.register_foreign_function("add", math_add)
        vm.register_foreign_function("process_string", string_processor)
        print("Foreign functions registered!")
        
        # Example 1: Execute function without arguments
        print("\nExample 1: Execute function without arguments")
        try:
            result = vm.execute("some_vm_function")
            print(f"Result: {result}")
        except VMError as e:
            print(f"Execution failed (expected in demo): {e}")
        
        # Example 2: Execute function with arguments
        print("\nExample 2: Execute function with arguments")
        try:
            args = [42, 58]
            result = vm.execute_with_args("add", args)
            print(f"add(42, 58) = {result}")
        except VMError as e:
            print(f"Execution failed (expected in demo): {e}")
        
        # Example 3: Work with different value types
        print("\nExample 3: Working with StoffelValue types")
        
        # Create different types of values
        unit_val = StoffelValue.unit()
        int_val = StoffelValue.integer(123)
        float_val = StoffelValue.float_value(3.14159)
        bool_val = StoffelValue.boolean(True)
        string_val = StoffelValue.string("Hello, StoffelVM!")
        
        print(f"Unit value: {unit_val}")
        print(f"Integer value: {int_val}")
        print(f"Float value: {float_val}")
        print(f"Boolean value: {bool_val}")
        print(f"String value: {string_val}")
        
        # Convert to Python values
        print(f"As Python values:")
        print(f"  Unit: {unit_val.to_python()}")
        print(f"  Integer: {int_val.to_python()}")
        print(f"  Float: {float_val.to_python()}")
        print(f"  Boolean: {bool_val.to_python()}")
        print(f"  String: {string_val.to_python()}")
        
        # Example 4: Create VM string
        print("\nExample 4: Create VM string")
        try:
            vm_string = vm.create_string("Created in VM!")
            print(f"VM string: {vm_string}")
        except VMError as e:
            print(f"String creation failed (expected in demo): {e}")
        
        # Example 5: Register foreign object
        print("\nExample 5: Register foreign object")
        try:
            my_object = {"key": "value", "number": 42}
            foreign_id = vm.register_foreign_object(my_object)
            print(f"Foreign object registered with ID: {foreign_id}")
        except VMError as e:
            print(f"Object registration failed (expected in demo): {e}")
        
        print("\nExample completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())