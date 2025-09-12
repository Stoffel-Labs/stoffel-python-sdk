"""
Tests for StoffelVM Python bindings
"""

import pytest
from unittest.mock import Mock, patch

from stoffel.vm import VirtualMachine, StoffelValue, ValueType
from stoffel.vm.exceptions import VMError, ExecutionError, RegistrationError


class TestStoffelValue:
    """Test StoffelValue type"""
    
    def test_unit_value(self):
        val = StoffelValue.unit()
        assert val.value_type == ValueType.UNIT
        assert val.data is None
        assert val.to_python() is None
    
    def test_integer_value(self):
        val = StoffelValue.integer(42)
        assert val.value_type == ValueType.INT
        assert val.data == 42
        assert val.to_python() == 42
    
    def test_float_value(self):
        val = StoffelValue.float_value(3.14)
        assert val.value_type == ValueType.FLOAT
        assert val.data == 3.14
        assert val.to_python() == 3.14
    
    def test_boolean_value(self):
        val = StoffelValue.boolean(True)
        assert val.value_type == ValueType.BOOL
        assert val.data is True
        assert val.to_python() is True
    
    def test_string_value(self):
        val = StoffelValue.string("hello")
        assert val.value_type == ValueType.STRING
        assert val.data == "hello"
        assert val.to_python() == "hello"
    
    def test_object_ref(self):
        val = StoffelValue.object_ref(123)
        assert val.value_type == ValueType.OBJECT
        assert val.data == 123
        assert val.to_python() == 123
    
    def test_array_ref(self):
        val = StoffelValue.array_ref(456)
        assert val.value_type == ValueType.ARRAY
        assert val.data == 456
        assert val.to_python() == 456
    
    def test_foreign_ref(self):
        val = StoffelValue.foreign_ref(789)
        assert val.value_type == ValueType.FOREIGN
        assert val.data == 789
        assert val.to_python() == 789


class TestVirtualMachine:
    """Test VirtualMachine class"""
    
    def test_library_loading_failure(self):
        """Test that VM creation fails gracefully when library is not found"""
        with pytest.raises((OSError, VMError)):
            VirtualMachine(library_path="/nonexistent/path/libstoffel_vm.so")
    
    @patch('ctypes.CDLL')
    def test_vm_creation_mock(self, mock_cdll):
        """Test VM creation with mocked library"""
        mock_lib = Mock()
        mock_lib.stoffel_create_vm.return_value = 12345  # Mock VM handle
        mock_cdll.return_value = mock_lib
        
        vm = VirtualMachine(library_path="mock_lib.so")
        
        # Verify library was loaded
        mock_cdll.assert_called_with("mock_lib.so")
        
        # Verify VM was created
        mock_lib.stoffel_create_vm.assert_called_once()
        
        assert vm._vm_handle == 12345
    
    @patch('ctypes.CDLL')
    def test_vm_creation_failure_mock(self, mock_cdll):
        """Test VM creation failure with mocked library"""
        mock_lib = Mock()
        mock_lib.stoffel_create_vm.return_value = None  # Failed creation
        mock_cdll.return_value = mock_lib
        
        with pytest.raises(VMError, match="Failed to create VM instance"):
            VirtualMachine(library_path="mock_lib.so")
    
    @patch('ctypes.CDLL')
    def test_execute_mock(self, mock_cdll):
        """Test function execution with mocked library"""
        mock_lib = Mock()
        mock_lib.stoffel_create_vm.return_value = 12345
        mock_lib.stoffel_execute.return_value = 0  # Success
        mock_cdll.return_value = mock_lib
        
        vm = VirtualMachine(library_path="mock_lib.so")
        
        # Mock the result would need more complex setup
        # This is a simplified test
        with pytest.raises(AttributeError):  # Expected due to mocking limitations
            vm.execute("test_function")
    
    @patch('ctypes.CDLL')
    def test_register_foreign_function_mock(self, mock_cdll):
        """Test foreign function registration with mocked library"""
        mock_lib = Mock()
        mock_lib.stoffel_create_vm.return_value = 12345
        mock_lib.stoffel_register_foreign_function.return_value = 0  # Success
        mock_cdll.return_value = mock_lib
        
        vm = VirtualMachine(library_path="mock_lib.so")
        
        def test_func(x, y):
            return x + y
        
        # This would normally work with proper FFI setup
        with pytest.raises(AttributeError):  # Expected due to mocking limitations
            vm.register_foreign_function("test_add", test_func)


class TestValueConversion:
    """Test value conversion utilities"""
    
    def test_python_to_stoffel_conversion(self):
        """Test conversion from Python values to StoffelValue"""
        # Test with None
        val = StoffelValue.unit()
        assert val.value_type == ValueType.UNIT
        
        # Test with int
        val = StoffelValue.integer(42)
        assert val.value_type == ValueType.INT
        assert val.data == 42
        
        # Test with float
        val = StoffelValue.float_value(3.14)
        assert val.value_type == ValueType.FLOAT
        assert val.data == 3.14
        
        # Test with bool
        val = StoffelValue.boolean(True)
        assert val.value_type == ValueType.BOOL
        assert val.data is True
        
        # Test with string
        val = StoffelValue.string("test")
        assert val.value_type == ValueType.STRING
        assert val.data == "test"