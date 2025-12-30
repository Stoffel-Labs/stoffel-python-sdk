"""
Tests for the advanced module
"""

import pytest
from stoffel.advanced import ShareManager, NetworkBuilder
from stoffel.advanced.share_manager import ShareScheme
from stoffel.advanced.network_builder import ConnectionMode


class TestShareManager:
    """Test ShareManager functionality"""

    def test_creation(self):
        """Test creating a ShareManager"""
        manager = ShareManager(n_parties=5, threshold=1)

        assert manager.n_parties == 5
        assert manager.threshold == 1
        assert manager.scheme == ShareScheme.ROBUST_SHAMIR

    def test_invalid_n_parties(self):
        """Test creation with invalid n_parties"""
        with pytest.raises(ValueError, match="n_parties must be at least 1"):
            ShareManager(n_parties=0, threshold=1)

    def test_invalid_threshold(self):
        """Test creation with invalid threshold"""
        with pytest.raises(ValueError, match="threshold must be at least 1"):
            ShareManager(n_parties=5, threshold=0)

    def test_honeybadger_constraint_robust(self):
        """Test HoneyBadger constraint for robust schemes"""
        # n=3 with t=1 should fail for robust (3 < 3*1+1 = 4)
        with pytest.raises(ValueError, match="must be >= 3\\*threshold\\+1"):
            ShareManager(n_parties=3, threshold=1, scheme=ShareScheme.ROBUST_SHAMIR)

    def test_non_robust_allows_smaller_n(self):
        """Test that non-robust scheme doesn't enforce HoneyBadger constraint"""
        # n=3 with t=1 should work for non-robust
        manager = ShareManager(n_parties=3, threshold=1, scheme=ShareScheme.SHAMIR)
        assert manager.n_parties == 3

    def test_create_shares_not_implemented(self):
        """Test create_shares raises NotImplementedError"""
        manager = ShareManager(n_parties=5, threshold=1)

        with pytest.raises(NotImplementedError, match="MPC protocol bindings"):
            manager.create_shares(42)

    def test_reconstruct_validates_share_count(self):
        """Test reconstruct validates minimum shares"""
        manager = ShareManager(n_parties=5, threshold=2)

        # Threshold is 2, so need at least 3 shares
        with pytest.raises(ValueError, match="Need at least 3 shares"):
            manager.reconstruct([])


class TestNetworkBuilder:
    """Test NetworkBuilder functionality"""

    def test_creation(self):
        """Test creating a NetworkBuilder"""
        builder = NetworkBuilder(n_parties=5)
        assert builder._n_parties == 5

    def test_invalid_n_parties(self):
        """Test creation with invalid n_parties"""
        with pytest.raises(ValueError, match="n_parties must be at least 1"):
            NetworkBuilder(n_parties=0)

    def test_add_node(self):
        """Test adding nodes"""
        builder = NetworkBuilder(n_parties=5)

        builder.add_node(0, "127.0.0.1:19200")
        builder.add_node(1, "127.0.0.1:19201")

        assert 0 in builder._nodes
        assert 1 in builder._nodes
        assert builder._nodes[0].bind_address == "127.0.0.1:19200"

    def test_add_node_chaining(self):
        """Test add_node method chaining"""
        builder = NetworkBuilder(n_parties=5)

        result = builder.add_node(0, "127.0.0.1:19200")
        assert result is builder

    def test_add_node_invalid_party_id(self):
        """Test add_node with invalid party_id"""
        builder = NetworkBuilder(n_parties=5)

        with pytest.raises(ValueError, match="party_id must be in range"):
            builder.add_node(10, "127.0.0.1:19200")

    def test_add_node_duplicate(self):
        """Test add_node with duplicate party_id"""
        builder = NetworkBuilder(n_parties=5)
        builder.add_node(0, "127.0.0.1:19200")

        with pytest.raises(ValueError, match="already exists"):
            builder.add_node(0, "127.0.0.1:19201")

    def test_localhost_convenience(self):
        """Test localhost() convenience method"""
        builder = NetworkBuilder(n_parties=5)
        builder.localhost(base_port=20000)

        assert len(builder._nodes) == 5
        assert builder._nodes[0].bind_address == "127.0.0.1:20000"
        assert builder._nodes[4].bind_address == "127.0.0.1:20004"

    def test_full_mesh(self):
        """Test full_mesh topology"""
        builder = NetworkBuilder(n_parties=3)
        builder.localhost()
        builder.full_mesh()

        topology = builder.build()

        assert topology.mode == ConnectionMode.FULL_MESH
        assert topology.n_parties == 3

        # Each party should connect to all others
        for party_id in range(3):
            peers = topology.get_peers_for(party_id)
            assert len(peers) == 2

    def test_full_mesh_requires_all_nodes(self):
        """Test full_mesh requires all nodes to be added"""
        builder = NetworkBuilder(n_parties=5)
        builder.add_node(0, "127.0.0.1:19200")

        with pytest.raises(ValueError, match="All 5 nodes must be added"):
            builder.full_mesh()

    def test_star_topology(self):
        """Test star topology"""
        builder = NetworkBuilder(n_parties=5)
        builder.localhost()
        builder.star(hub_party_id=0)

        topology = builder.build()

        assert topology.mode == ConnectionMode.STAR

        # Hub connects to all others
        hub_peers = topology.get_peers_for(0)
        assert len(hub_peers) == 4

        # Others only connect to hub
        for party_id in range(1, 5):
            peers = topology.get_peers_for(party_id)
            assert len(peers) == 1
            assert peers[0][0] == 0  # Connected to hub

    def test_build_validates_node_count(self):
        """Test build validates all nodes are added"""
        builder = NetworkBuilder(n_parties=5)
        builder.add_node(0, "127.0.0.1:19200")

        with pytest.raises(ValueError, match="Expected 5 nodes"):
            builder.build()

    def test_to_dict(self):
        """Test topology serialization"""
        builder = NetworkBuilder(n_parties=3)
        builder.localhost()
        builder.full_mesh()

        topology = builder.build()
        result = topology.to_dict()

        assert "nodes" in result
        assert "connections" in result
        assert "mode" in result
        assert len(result["nodes"]) == 3
        assert result["mode"] == "full_mesh"

    def test_from_config(self):
        """Test creating builder from config"""
        config = {
            "nodes": [
                {"party_id": 0, "bind_address": "127.0.0.1:19200"},
                {"party_id": 1, "bind_address": "127.0.0.1:19201"},
            ],
            "connections": [],
        }

        builder = NetworkBuilder.from_config(config)

        assert builder._n_parties == 2
        assert 0 in builder._nodes
        assert 1 in builder._nodes
