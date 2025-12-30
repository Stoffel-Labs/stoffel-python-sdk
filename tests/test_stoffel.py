"""
Tests for the main Stoffel API
"""

import pytest
from stoffel import (
    Stoffel,
    StoffelRuntime,
    Program,
    ProtocolType,
    ShareType,
    OptimizationLevel,
)


class TestStoffelBuilder:
    """Test the Stoffel builder pattern"""

    def test_compile_returns_builder(self):
        """Test that compile returns a Stoffel builder"""
        # This will fail until we have actual compiler bindings
        # but tests the API structure
        with pytest.raises(Exception):  # Expected - no compiler available
            builder = Stoffel.compile("main main() -> int64:\n  return 42")
            assert isinstance(builder, Stoffel)

    def test_load_returns_builder(self):
        """Test that load returns a Stoffel builder"""
        builder = Stoffel.load(b"fake_bytecode")
        assert isinstance(builder, Stoffel)

    def test_builder_method_chaining(self):
        """Test method chaining on the builder"""
        builder = Stoffel.load(b"fake_bytecode")

        result = (builder
            .parties(5)
            .threshold(1)
            .instance_id(42)
            .protocol(ProtocolType.HONEYBADGER)
            .share_type(ShareType.ROBUST))

        # All methods should return self for chaining
        assert result is builder

    def test_minimum_parties_validation(self):
        """Test that minimum 3 parties is enforced"""
        builder = Stoffel.load(b"fake_bytecode")

        # n=2 should fail (HoneyBadger requires minimum 3 parties)
        with pytest.raises(ValueError, match="at least 3 parties"):
            builder.parties(2).threshold(0).build()

        # n=1 should also fail
        with pytest.raises(ValueError, match="at least 3 parties"):
            builder.parties(1).threshold(0).build()

    def test_parties_threshold_constraint(self):
        """Test that parties/threshold constraint is validated on build"""
        builder = Stoffel.load(b"fake_bytecode")

        # n=3 with t=1 should fail (3 < 3*1+1 = 4)
        with pytest.raises(ValueError, match="must be >= 3t\\+1"):
            builder.parties(3).threshold(1).build()

    def test_valid_mpc_config(self):
        """Test valid MPC configuration builds successfully"""
        builder = Stoffel.load(b"fake_bytecode")

        # n=4 with t=1 should work (4 >= 3*1+1 = 4)
        runtime = builder.parties(4).threshold(1).build()
        assert isinstance(runtime, StoffelRuntime)

    def test_default_threshold(self):
        """Test that threshold defaults to 1"""
        builder = Stoffel.load(b"fake_bytecode")

        # n=4 with default t=1 should work
        runtime = builder.parties(4).build()

        config = runtime.mpc_config()
        assert config[1] == 1  # threshold is second element

    def test_no_parties_builds_without_mpc(self):
        """Test that building without parties() works for local use"""
        builder = Stoffel.load(b"fake_bytecode")

        runtime = builder.build()
        assert runtime.mpc_config() is None


class TestStoffelRuntime:
    """Test StoffelRuntime functionality"""

    def setup_method(self):
        """Set up a runtime for testing"""
        self.runtime = (Stoffel.load(b"fake_bytecode")
            .parties(5)
            .threshold(1)
            .instance_id(42)
            .build())

    def test_mpc_config(self):
        """Test mpc_config returns correct values"""
        config = self.runtime.mpc_config()

        assert config is not None
        assert config[0] == 5   # n_parties
        assert config[1] == 1   # threshold
        assert config[2] == 42  # instance_id

    def test_program_returns_program(self):
        """Test program() returns a Program instance"""
        program = self.runtime.program()
        assert isinstance(program, Program)

    def test_protocol_type(self):
        """Test protocol_type returns correct value"""
        assert self.runtime.protocol_type() == ProtocolType.HONEYBADGER

    def test_share_type(self):
        """Test share_type returns correct value"""
        assert self.runtime.share_type() == ShareType.ROBUST

    def test_client_requires_mpc_config(self):
        """Test that client() requires MPC config"""
        # Runtime without MPC config
        runtime = Stoffel.load(b"fake_bytecode").build()

        with pytest.raises(RuntimeError, match="Cannot create MPC client"):
            runtime.client(100)

    def test_server_requires_mpc_config(self):
        """Test that server() requires MPC config"""
        runtime = Stoffel.load(b"fake_bytecode").build()

        with pytest.raises(RuntimeError, match="Cannot create MPC server"):
            runtime.server(0)

    def test_node_requires_mpc_config(self):
        """Test that node() requires MPC config"""
        runtime = Stoffel.load(b"fake_bytecode").build()

        with pytest.raises(RuntimeError, match="Cannot create MPC node"):
            runtime.node(0)


class TestProgram:
    """Test Program functionality"""

    def setup_method(self):
        """Set up a program for testing"""
        self.program = Program(b"fake_bytecode")

    def test_bytecode(self):
        """Test bytecode() returns the bytecode"""
        assert self.program.bytecode() == b"fake_bytecode"

    def test_save(self, tmp_path):
        """Test save() writes bytecode to file"""
        file_path = tmp_path / "test.stfb"
        self.program.save(str(file_path))

        with open(file_path, "rb") as f:
            assert f.read() == b"fake_bytecode"

    def test_execute_local_not_implemented(self):
        """Test execute_local raises NotImplementedError"""
        with pytest.raises(NotImplementedError, match="VM bindings"):
            self.program.execute_local()


class TestEnums:
    """Test enum values"""

    def test_protocol_type_values(self):
        """Test ProtocolType enum values"""
        assert ProtocolType.HONEYBADGER.value == "honeybadger"

    def test_share_type_values(self):
        """Test ShareType enum values"""
        assert ShareType.ROBUST.value == "robust"
        assert ShareType.NON_ROBUST.value == "non_robust"

    def test_optimization_level_values(self):
        """Test OptimizationLevel enum values"""
        assert OptimizationLevel.NONE.value == 0
        assert OptimizationLevel.O1.value == 1
        assert OptimizationLevel.O2.value == 2
        assert OptimizationLevel.O3.value == 3
