"""
Tests for exception types
"""

import pytest
from stoffel import (
    StoffelError,
    MPCError,
    ComputationError,
    NetworkError,
    ConfigurationError,
    ProtocolError,
    PreprocessingError,
    IoError,
    InvalidInputError,
    FunctionNotFoundError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy"""

    def test_stoffel_error_is_base(self):
        """Test StoffelError is the base exception"""
        assert issubclass(StoffelError, Exception)

    def test_mpc_error_inherits_stoffel_error(self):
        """Test MPCError inherits from StoffelError"""
        assert issubclass(MPCError, StoffelError)

    def test_computation_error_inherits_mpc_error(self):
        """Test ComputationError inherits from MPCError"""
        assert issubclass(ComputationError, MPCError)

    def test_network_error_inherits_mpc_error(self):
        """Test NetworkError inherits from MPCError"""
        assert issubclass(NetworkError, MPCError)

    def test_configuration_error_inherits_mpc_error(self):
        """Test ConfigurationError inherits from MPCError"""
        assert issubclass(ConfigurationError, MPCError)

    def test_protocol_error_inherits_mpc_error(self):
        """Test ProtocolError inherits from MPCError"""
        assert issubclass(ProtocolError, MPCError)

    def test_preprocessing_error_inherits_mpc_error(self):
        """Test PreprocessingError inherits from MPCError"""
        assert issubclass(PreprocessingError, MPCError)

    def test_io_error_inherits_stoffel_error(self):
        """Test IoError inherits from StoffelError"""
        assert issubclass(IoError, StoffelError)
        # But not from MPCError
        assert not issubclass(IoError, MPCError)

    def test_invalid_input_error_inherits_stoffel_error(self):
        """Test InvalidInputError inherits from StoffelError"""
        assert issubclass(InvalidInputError, StoffelError)
        assert not issubclass(InvalidInputError, MPCError)

    def test_function_not_found_error_inherits_stoffel_error(self):
        """Test FunctionNotFoundError inherits from StoffelError"""
        assert issubclass(FunctionNotFoundError, StoffelError)
        assert not issubclass(FunctionNotFoundError, MPCError)


class TestExceptionRaising:
    """Test that exceptions can be raised and caught correctly"""

    def test_raise_stoffel_error(self):
        """Test raising StoffelError"""
        with pytest.raises(StoffelError, match="Test error"):
            raise StoffelError("Test error")

    def test_raise_mpc_error(self):
        """Test raising MPCError"""
        with pytest.raises(MPCError, match="MPC failed"):
            raise MPCError("MPC failed")

    def test_catch_mpc_error_as_stoffel_error(self):
        """Test catching MPCError as StoffelError"""
        with pytest.raises(StoffelError):
            raise MPCError("MPC failed")

    def test_raise_computation_error(self):
        """Test raising ComputationError"""
        with pytest.raises(ComputationError, match="Computation failed"):
            raise ComputationError("Computation failed")

    def test_catch_computation_error_as_mpc_error(self):
        """Test catching ComputationError as MPCError"""
        with pytest.raises(MPCError):
            raise ComputationError("Computation failed")

    def test_raise_network_error(self):
        """Test raising NetworkError"""
        with pytest.raises(NetworkError, match="Connection refused"):
            raise NetworkError("Connection refused")

    def test_raise_configuration_error(self):
        """Test raising ConfigurationError"""
        with pytest.raises(ConfigurationError, match="Invalid config"):
            raise ConfigurationError("Invalid config")

    def test_raise_protocol_error(self):
        """Test raising ProtocolError"""
        with pytest.raises(ProtocolError, match="Protocol violation"):
            raise ProtocolError("Protocol violation")

    def test_raise_preprocessing_error(self):
        """Test raising PreprocessingError"""
        with pytest.raises(PreprocessingError, match="Preprocessing failed"):
            raise PreprocessingError("Preprocessing failed")

    def test_raise_io_error(self):
        """Test raising IoError"""
        with pytest.raises(IoError, match="File not found"):
            raise IoError("File not found")

    def test_raise_invalid_input_error(self):
        """Test raising InvalidInputError"""
        with pytest.raises(InvalidInputError, match="Invalid input"):
            raise InvalidInputError("Invalid input value")

    def test_raise_function_not_found_error(self):
        """Test raising FunctionNotFoundError"""
        with pytest.raises(FunctionNotFoundError, match="not found"):
            raise FunctionNotFoundError("Function 'foo' not found")
