"""
Tests for Stoffel builder pattern and configuration

Tests the Stoffel entry point, StoffelBuilder, StoffelRuntime,
and MPC configuration validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path

from stoffel.stoffel import Stoffel, StoffelBuilder
from stoffel.runtime import StoffelRuntime, MPCConfig
from stoffel.enums import ProtocolType, ShareType, OptimizationLevel
from stoffel.error import (
    ConfigurationError,
    CompilationError,
    IoError,
)


class TestMPCConfig:
    """Test MPCConfig dataclass and validation"""

    def test_config_creation_defaults(self):
        """Test creating config with default values"""
        config = MPCConfig(
            parties=5,
            threshold=1,
            instance_id=0
        )

        assert config.parties == 5
        assert config.threshold == 1
        assert config.instance_id == 0
        assert config.protocol_type == ProtocolType.HONEYBADGER
        assert config.share_type == ShareType.ROBUST

    def test_config_creation_custom(self):
        """Test creating config with custom values"""
        config = MPCConfig(
            parties=7,
            threshold=2,
            instance_id=12345,
            protocol_type=ProtocolType.HONEYBADGER,
            share_type=ShareType.ROBUST
        )

        assert config.parties == 7
        assert config.threshold == 2
        assert config.instance_id == 12345

    def test_config_validation_parties_zero(self):
        """Test that parties < 1 raises error"""
        with pytest.raises(ValueError, match="parties must be at least 1"):
            MPCConfig(parties=0, threshold=0, instance_id=0)

    def test_config_validation_negative_threshold(self):
        """Test that negative threshold raises error"""
        with pytest.raises(ValueError, match="threshold cannot be negative"):
            MPCConfig(parties=5, threshold=-1, instance_id=0)

    def test_config_validation_negative_instance_id(self):
        """Test that negative instance_id raises error"""
        with pytest.raises(ValueError, match="instance_id cannot be negative"):
            MPCConfig(parties=5, threshold=1, instance_id=-1)


class TestStoffelRuntime:
    """Test StoffelRuntime class"""

    def test_runtime_creation(self):
        """Test creating a runtime"""
        program = b"test bytecode"
        config = MPCConfig(parties=5, threshold=1, instance_id=0)

        runtime = StoffelRuntime(program, config)

        assert runtime.program == b"test bytecode"
        assert runtime.mpc_config == config
        assert runtime.parties == 5
        assert runtime.threshold == 1
        assert runtime.instance_id == 0
        assert runtime.protocol_type == ProtocolType.HONEYBADGER
        assert runtime.share_type == ShareType.ROBUST

    def test_runtime_save_program(self):
        """Test saving program to file"""
        program = b"test bytecode content"
        config = MPCConfig(parties=5, threshold=1, instance_id=0)
        runtime = StoffelRuntime(program, config)

        with tempfile.NamedTemporaryFile(suffix='.stfb', delete=False) as f:
            temp_path = f.name

        try:
            runtime.save_program(temp_path)

            saved_content = Path(temp_path).read_bytes()
            assert saved_content == b"test bytecode content"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_runtime_repr(self):
        """Test runtime string representation"""
        program = b"test"
        config = MPCConfig(parties=5, threshold=1, instance_id=123)
        runtime = StoffelRuntime(program, config)

        repr_str = repr(runtime)

        assert "StoffelRuntime" in repr_str
        assert "4 bytes" in repr_str
        assert "parties=5" in repr_str
        assert "threshold=1" in repr_str
        assert "instance_id=123" in repr_str


class TestStoffelBuilder:
    """Test StoffelBuilder fluent interface"""

    def test_builder_from_bytecode(self):
        """Test creating builder from bytecode"""
        bytecode = b"test bytecode"
        builder = StoffelBuilder._from_bytecode(bytecode)

        assert builder._program == bytecode
        assert builder._compiled is True

    def test_builder_parties(self):
        """Test setting parties"""
        builder = StoffelBuilder._from_bytecode(b"test")
        result = builder.parties(7)

        assert result is builder  # Chaining
        assert builder._parties == 7

    def test_builder_parties_invalid(self):
        """Test that invalid parties raises error"""
        builder = StoffelBuilder._from_bytecode(b"test")

        with pytest.raises(ConfigurationError, match="parties must be at least 1"):
            builder.parties(0)

    def test_builder_threshold(self):
        """Test setting threshold"""
        builder = StoffelBuilder._from_bytecode(b"test")
        result = builder.threshold(2)

        assert result is builder
        assert builder._threshold == 2

    def test_builder_threshold_invalid(self):
        """Test that negative threshold raises error"""
        builder = StoffelBuilder._from_bytecode(b"test")

        with pytest.raises(ConfigurationError, match="threshold cannot be negative"):
            builder.threshold(-1)

    def test_builder_instance_id(self):
        """Test setting instance_id"""
        builder = StoffelBuilder._from_bytecode(b"test")
        result = builder.instance_id(12345)

        assert result is builder
        assert builder._instance_id == 12345

    def test_builder_instance_id_invalid(self):
        """Test that negative instance_id raises error"""
        builder = StoffelBuilder._from_bytecode(b"test")

        with pytest.raises(ConfigurationError, match="instance_id cannot be negative"):
            builder.instance_id(-1)

    def test_builder_protocol(self):
        """Test setting protocol"""
        builder = StoffelBuilder._from_bytecode(b"test")
        result = builder.protocol(ProtocolType.HONEYBADGER)

        assert result is builder
        assert builder._protocol_type == ProtocolType.HONEYBADGER

    def test_builder_share_type(self):
        """Test setting share type"""
        builder = StoffelBuilder._from_bytecode(b"test")
        result = builder.share_type(ShareType.ROBUST)

        assert result is builder
        assert builder._share_type == ShareType.ROBUST

    def test_builder_optimize_int(self):
        """Test setting optimization level as int"""
        builder = StoffelBuilder._from_bytecode(b"test")
        result = builder.optimize(2)

        assert result is builder
        assert builder._optimization_level == OptimizationLevel.O2

    def test_builder_optimize_enum(self):
        """Test setting optimization level as enum"""
        builder = StoffelBuilder._from_bytecode(b"test")
        result = builder.optimize(OptimizationLevel.O3)

        assert result is builder
        assert builder._optimization_level == OptimizationLevel.O3

    def test_builder_optimize_invalid(self):
        """Test that invalid optimization level raises error"""
        builder = StoffelBuilder._from_bytecode(b"test")

        with pytest.raises(ConfigurationError, match="Invalid optimization level"):
            builder.optimize(5)

    def test_builder_chaining(self):
        """Test method chaining"""
        builder = StoffelBuilder._from_bytecode(b"test")

        result = builder \
            .parties(7) \
            .threshold(2) \
            .instance_id(100) \
            .protocol(ProtocolType.HONEYBADGER) \
            .share_type(ShareType.ROBUST) \
            .optimize(1)

        assert result is builder
        assert builder._parties == 7
        assert builder._threshold == 2
        assert builder._instance_id == 100


class TestConfigValidation:
    """Test MPC configuration validation"""

    def test_honeybadger_constraint_valid_minimum(self):
        """Test valid minimum HoneyBadger config: n=4, t=1 (4 >= 3*1+1)"""
        builder = StoffelBuilder._from_bytecode(b"test")
        builder.parties(4).threshold(1)

        # Should not raise
        builder._validate_config()

    def test_honeybadger_constraint_valid_standard(self):
        """Test valid standard HoneyBadger config: n=5, t=1 (5 >= 4)"""
        builder = StoffelBuilder._from_bytecode(b"test")
        builder.parties(5).threshold(1)

        # Should not raise
        builder._validate_config()

    def test_honeybadger_constraint_valid_higher(self):
        """Test valid higher tolerance config: n=7, t=2 (7 >= 7)"""
        builder = StoffelBuilder._from_bytecode(b"test")
        builder.parties(7).threshold(2)

        # Should not raise
        builder._validate_config()

    def test_honeybadger_constraint_invalid(self):
        """Test invalid HoneyBadger config: n=3, t=1 (3 < 4)"""
        builder = StoffelBuilder._from_bytecode(b"test")
        builder.parties(3).threshold(1)

        with pytest.raises(ConfigurationError, match="HoneyBadger requires n >= 3t \\+ 1"):
            builder._validate_config()

    def test_honeybadger_constraint_invalid_higher(self):
        """Test invalid config: n=6, t=2 (6 < 7)"""
        builder = StoffelBuilder._from_bytecode(b"test")
        builder.parties(6).threshold(2)

        with pytest.raises(ConfigurationError, match="HoneyBadger requires n >= 3t \\+ 1"):
            builder._validate_config()

    def test_honeybadger_requires_robust_shares(self):
        """Test that HoneyBadger requires ROBUST shares"""
        builder = StoffelBuilder._from_bytecode(b"test")
        builder.parties(5).threshold(1).share_type(ShareType.NON_ROBUST)

        with pytest.raises(ConfigurationError, match="ROBUST share type"):
            builder._validate_config()

    def test_build_validates_config(self):
        """Test that build() validates configuration"""
        builder = StoffelBuilder._from_bytecode(b"test")
        builder.parties(3).threshold(1)

        with pytest.raises(ConfigurationError):
            builder.build()

    def test_build_creates_runtime(self):
        """Test that build() creates StoffelRuntime"""
        builder = StoffelBuilder._from_bytecode(b"test bytecode")
        builder.parties(5).threshold(1).instance_id(42)

        runtime = builder.build()

        assert isinstance(runtime, StoffelRuntime)
        assert runtime.program == b"test bytecode"
        assert runtime.parties == 5
        assert runtime.threshold == 1
        assert runtime.instance_id == 42


class TestStoffelEntryPoint:
    """Test Stoffel static entry point"""

    def test_load_bytecode(self):
        """Test Stoffel.load() with bytecode"""
        bytecode = b"test bytecode"

        builder = Stoffel.load(bytecode)

        assert isinstance(builder, StoffelBuilder)
        assert builder._program == bytecode

    def test_load_file(self):
        """Test Stoffel.load_file() with bytecode file"""
        bytecode = b"test bytecode from file"

        with tempfile.NamedTemporaryFile(suffix='.stfb', delete=False) as f:
            f.write(bytecode)
            temp_path = f.name

        try:
            builder = Stoffel.load_file(temp_path)

            assert isinstance(builder, StoffelBuilder)
            assert builder._program == bytecode
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_file_not_found(self):
        """Test Stoffel.load_file() with missing file"""
        with pytest.raises(IoError, match="Failed to read bytecode file"):
            Stoffel.load_file("/nonexistent/file.stfb")

    def test_compile_sets_source(self):
        """Test Stoffel.compile() sets source"""
        source = "fn main() { return 42; }"

        builder = Stoffel.compile(source)

        assert isinstance(builder, StoffelBuilder)
        assert builder._source == source
        assert builder._compiled is False

    def test_compile_file_not_found(self):
        """Test Stoffel.compile_file() with missing file"""
        with pytest.raises(IoError, match="Source file not found"):
            Stoffel.compile_file("/nonexistent/file.stfl")


class TestEnums:
    """Test enum values"""

    def test_protocol_type_values(self):
        """Test ProtocolType enum values"""
        assert ProtocolType.HONEYBADGER == 0

    def test_share_type_values(self):
        """Test ShareType enum values"""
        assert ShareType.ROBUST == 0
        assert ShareType.NON_ROBUST == 1

    def test_optimization_level_values(self):
        """Test OptimizationLevel enum values"""
        assert OptimizationLevel.NONE == 0
        assert OptimizationLevel.O1 == 1
        assert OptimizationLevel.O2 == 2
        assert OptimizationLevel.O3 == 3


class TestIntegration:
    """Integration tests for full builder workflow"""

    def test_full_builder_workflow_with_bytecode(self):
        """Test complete builder workflow with pre-compiled bytecode"""
        bytecode = b"compiled program bytecode"

        runtime = Stoffel.load(bytecode) \
            .parties(5) \
            .threshold(1) \
            .instance_id(12345) \
            .protocol(ProtocolType.HONEYBADGER) \
            .share_type(ShareType.ROBUST) \
            .build()

        assert isinstance(runtime, StoffelRuntime)
        assert runtime.program == bytecode
        assert runtime.parties == 5
        assert runtime.threshold == 1
        assert runtime.instance_id == 12345
        assert runtime.protocol_type == ProtocolType.HONEYBADGER
        assert runtime.share_type == ShareType.ROBUST

    def test_builder_with_default_config(self):
        """Test builder with default configuration"""
        bytecode = b"test"

        runtime = Stoffel.load(bytecode).build()

        # Defaults: parties=5, threshold=1, instance_id=0
        assert runtime.parties == 5
        assert runtime.threshold == 1
        assert runtime.instance_id == 0
        assert runtime.protocol_type == ProtocolType.HONEYBADGER
        assert runtime.share_type == ShareType.ROBUST
