"""
Tests for MPC participant classes
"""

import pytest
from stoffel import (
    Stoffel,
    MPCClient,
    MPCClientBuilder,
    MPCServer,
    MPCServerBuilder,
    MPCNode,
    MPCNodeBuilder,
    ProtocolType,
    ShareType,
)


class TestMPCClientBuilder:
    """Test MPCClientBuilder functionality"""

    def setup_method(self):
        """Set up a runtime for testing"""
        self.runtime = (Stoffel.load(b"fake_bytecode")
            .parties(5)
            .threshold(1)
            .build())

    def test_client_builder_returns_builder(self):
        """Test that runtime.client() returns a builder"""
        builder = self.runtime.client(100)
        assert isinstance(builder, MPCClientBuilder)

    def test_with_inputs_chaining(self):
        """Test with_inputs method chaining"""
        builder = self.runtime.client(100)
        result = builder.with_inputs([10, 20, 30])
        assert result is builder

    def test_build_returns_client(self):
        """Test build() returns MPCClient"""
        client = self.runtime.client(100).with_inputs([10]).build()
        assert isinstance(client, MPCClient)


class TestMPCClient:
    """Test MPCClient functionality"""

    def setup_method(self):
        """Set up a client for testing"""
        runtime = (Stoffel.load(b"fake_bytecode")
            .parties(5)
            .threshold(1)
            .instance_id(42)
            .build())
        self.client = runtime.client(100).with_inputs([10, 20]).build()

    def test_client_id(self):
        """Test client_id property"""
        assert self.client.client_id == 100

    def test_inputs(self):
        """Test inputs property"""
        assert self.client.inputs == [10, 20]

    def test_instance_id(self):
        """Test instance_id property"""
        assert self.client.instance_id == 42

    def test_config(self):
        """Test config() method"""
        config = self.client.config()

        assert config["n_parties"] == 5
        assert config["threshold"] == 1
        assert config["instance_id"] == 42
        assert config["protocol_type"] == "honeybadger"

    def test_generate_input_shares_not_implemented(self):
        """Test generate_input_shares raises NotImplementedError"""
        with pytest.raises(NotImplementedError, match="MPC protocol bindings"):
            self.client.generate_input_shares()

    def test_generate_input_shares_robust_not_implemented(self):
        """Test generate_input_shares_robust raises NotImplementedError"""
        with pytest.raises(NotImplementedError, match="MPC protocol bindings"):
            self.client.generate_input_shares_robust()

    def test_generate_input_shares_non_robust_not_implemented(self):
        """Test generate_input_shares_non_robust raises NotImplementedError"""
        with pytest.raises(NotImplementedError, match="MPC protocol bindings"):
            self.client.generate_input_shares_non_robust()


class TestMPCServerBuilder:
    """Test MPCServerBuilder functionality"""

    def setup_method(self):
        """Set up a runtime for testing"""
        self.runtime = (Stoffel.load(b"fake_bytecode")
            .parties(5)
            .threshold(1)
            .build())

    def test_server_builder_returns_builder(self):
        """Test that runtime.server() returns a builder"""
        builder = self.runtime.server(0)
        assert isinstance(builder, MPCServerBuilder)

    def test_with_preprocessing_chaining(self):
        """Test with_preprocessing method chaining"""
        builder = self.runtime.server(0)
        result = builder.with_preprocessing(10, 25)
        assert result is builder

    def test_build_returns_server(self):
        """Test build() returns MPCServer"""
        server = self.runtime.server(0).build()
        assert isinstance(server, MPCServer)


class TestMPCServer:
    """Test MPCServer functionality"""

    def setup_method(self):
        """Set up a server for testing"""
        runtime = (Stoffel.load(b"fake_bytecode")
            .parties(5)
            .threshold(1)
            .instance_id(42)
            .build())
        self.server = runtime.server(0).with_preprocessing(10, 25).build()

    def test_party_id(self):
        """Test party_id property"""
        assert self.server.party_id == 0

    def test_instance_id(self):
        """Test instance_id property"""
        assert self.server.instance_id == 42

    def test_config(self):
        """Test config() method"""
        config = self.server.config()

        assert config["n_parties"] == 5
        assert config["threshold"] == 1
        assert config["instance_id"] == 42
        assert config["protocol_type"] == "honeybadger"

    def test_initialize_node(self):
        """Test initialize_node() method"""
        self.server.initialize_node()
        assert self.server._initialized is True

    def test_add_peer(self):
        """Test add_peer() method"""
        self.server.add_peer(1, "127.0.0.1:19201")
        assert self.server._peers[1] == "127.0.0.1:19201"

    def test_load_bytecode(self):
        """Test load_bytecode() method"""
        self.server.load_bytecode(b"new_bytecode")
        assert self.server._bytecode == b"new_bytecode"


class TestMPCNodeBuilder:
    """Test MPCNodeBuilder functionality"""

    def setup_method(self):
        """Set up a runtime for testing"""
        self.runtime = (Stoffel.load(b"fake_bytecode")
            .parties(5)
            .threshold(1)
            .build())

    def test_node_builder_returns_builder(self):
        """Test that runtime.node() returns a builder"""
        builder = self.runtime.node(0)
        assert isinstance(builder, MPCNodeBuilder)

    def test_with_inputs_chaining(self):
        """Test with_inputs method chaining"""
        builder = self.runtime.node(0)
        result = builder.with_inputs([10, 20])
        assert result is builder

    def test_with_preprocessing_chaining(self):
        """Test with_preprocessing method chaining"""
        builder = self.runtime.node(0)
        result = builder.with_preprocessing(3, 8)
        assert result is builder

    def test_build_returns_node(self):
        """Test build() returns MPCNode"""
        node = self.runtime.node(0).with_inputs([10]).build()
        assert isinstance(node, MPCNode)


class TestMPCNode:
    """Test MPCNode functionality"""

    def setup_method(self):
        """Set up a node for testing"""
        runtime = (Stoffel.load(b"fake_bytecode")
            .parties(5)
            .threshold(1)
            .instance_id(42)
            .build())
        self.node = (runtime.node(0)
            .with_inputs([10, 20])
            .with_preprocessing(3, 8)
            .build())

    def test_party_id(self):
        """Test party_id property"""
        assert self.node.party_id == 0

    def test_inputs(self):
        """Test inputs property"""
        assert self.node.inputs == [10, 20]

    def test_instance_id(self):
        """Test instance_id property"""
        assert self.node.instance_id == 42

    def test_config(self):
        """Test config() method"""
        config = self.node.config()

        assert config["n_parties"] == 5
        assert config["threshold"] == 1
        assert config["instance_id"] == 42
        assert config["protocol_type"] == "honeybadger"

    def test_run_not_implemented(self):
        """Test run() raises NotImplementedError"""
        with pytest.raises(NotImplementedError, match="MPC protocol bindings"):
            import asyncio
            asyncio.run(self.node.run(b"bytecode"))
