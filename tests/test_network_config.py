"""
Tests for NetworkConfig
"""

import pytest
from stoffel import NetworkConfig, NetworkSettings, MPCSettings


class TestNetworkSettings:
    """Test NetworkSettings dataclass"""

    def test_creation(self):
        """Test creating NetworkSettings"""
        settings = NetworkSettings(
            party_id=0,
            bind_address="127.0.0.1:19200",
            bootstrap_address="127.0.0.1:19200",
            min_parties=5,
        )

        assert settings.party_id == 0
        assert settings.bind_address == "127.0.0.1:19200"
        assert settings.bootstrap_address == "127.0.0.1:19200"
        assert settings.min_parties == 5


class TestMPCSettings:
    """Test MPCSettings dataclass"""

    def test_creation(self):
        """Test creating MPCSettings"""
        settings = MPCSettings(
            n_parties=5,
            threshold=1,
            instance_id=42,
        )

        assert settings.n_parties == 5
        assert settings.threshold == 1
        assert settings.instance_id == 42

    def test_optional_instance_id(self):
        """Test instance_id is optional"""
        settings = MPCSettings(n_parties=5, threshold=1)
        assert settings.instance_id is None


class TestNetworkConfig:
    """Test NetworkConfig functionality"""

    def test_creation(self):
        """Test creating NetworkConfig"""
        config = NetworkConfig(
            network=NetworkSettings(
                party_id=0,
                bind_address="127.0.0.1:19200",
                bootstrap_address="127.0.0.1:19200",
                min_parties=5,
            ),
            mpc=MPCSettings(
                n_parties=5,
                threshold=1,
                instance_id=42,
            ),
        )

        assert config.network.party_id == 0
        assert config.mpc.n_parties == 5

    def test_from_dict(self):
        """Test creating from dictionary"""
        data = {
            "network": {
                "party_id": 1,
                "bind_address": "127.0.0.1:19201",
                "bootstrap_address": "127.0.0.1:19200",
                "min_parties": 5,
            },
            "mpc": {
                "n_parties": 5,
                "threshold": 1,
                "instance_id": 100,
            },
        }

        config = NetworkConfig.from_dict(data)

        assert config.network.party_id == 1
        assert config.network.bind_address == "127.0.0.1:19201"
        assert config.mpc.n_parties == 5
        assert config.mpc.instance_id == 100

    def test_from_dict_missing_network(self):
        """Test from_dict with missing network section"""
        with pytest.raises(ValueError, match="Missing 'network' section"):
            NetworkConfig.from_dict({"mpc": {"n_parties": 5, "threshold": 1}})

    def test_from_dict_missing_mpc(self):
        """Test from_dict with missing mpc section"""
        with pytest.raises(ValueError, match="Missing 'mpc' section"):
            NetworkConfig.from_dict({
                "network": {
                    "party_id": 0,
                    "bind_address": "127.0.0.1:19200",
                    "bootstrap_address": "127.0.0.1:19200",
                    "min_parties": 5,
                }
            })

    def test_validate_valid_config(self):
        """Test validate passes for valid config"""
        config = NetworkConfig(
            network=NetworkSettings(
                party_id=0,
                bind_address="127.0.0.1:19200",
                bootstrap_address="127.0.0.1:19200",
                min_parties=5,
            ),
            mpc=MPCSettings(n_parties=5, threshold=1),
        )

        # Should not raise
        config.validate()

    def test_validate_honeybadger_constraint(self):
        """Test validate enforces n >= 3t + 1"""
        config = NetworkConfig(
            network=NetworkSettings(
                party_id=0,
                bind_address="127.0.0.1:19200",
                bootstrap_address="127.0.0.1:19200",
                min_parties=3,
            ),
            mpc=MPCSettings(n_parties=3, threshold=1),  # 3 < 3*1+1 = 4
        )

        with pytest.raises(ValueError, match="must be >= 3\\*threshold\\+1"):
            config.validate()

    def test_validate_party_id_range(self):
        """Test validate checks party_id is in valid range"""
        config = NetworkConfig(
            network=NetworkSettings(
                party_id=10,  # Out of range for n_parties=5
                bind_address="127.0.0.1:19200",
                bootstrap_address="127.0.0.1:19200",
                min_parties=5,
            ),
            mpc=MPCSettings(n_parties=5, threshold=1),
        )

        with pytest.raises(ValueError, match="Invalid party_id"):
            config.validate()

    def test_validate_min_parties_range(self):
        """Test validate checks min_parties is in valid range"""
        config = NetworkConfig(
            network=NetworkSettings(
                party_id=0,
                bind_address="127.0.0.1:19200",
                bootstrap_address="127.0.0.1:19200",
                min_parties=10,  # Out of range for n_parties=5
            ),
            mpc=MPCSettings(n_parties=5, threshold=1),
        )

        with pytest.raises(ValueError, match="Invalid min_parties"):
            config.validate()

    def test_to_dict(self):
        """Test conversion to dictionary"""
        config = NetworkConfig(
            network=NetworkSettings(
                party_id=0,
                bind_address="127.0.0.1:19200",
                bootstrap_address="127.0.0.1:19200",
                min_parties=5,
            ),
            mpc=MPCSettings(n_parties=5, threshold=1, instance_id=42),
        )

        result = config.to_dict()

        assert result["network"]["party_id"] == 0
        assert result["mpc"]["n_parties"] == 5
        assert result["mpc"]["instance_id"] == 42

    def test_save_and_load(self, tmp_path):
        """Test saving and loading from file"""
        config = NetworkConfig(
            network=NetworkSettings(
                party_id=0,
                bind_address="127.0.0.1:19200",
                bootstrap_address="127.0.0.1:19200",
                min_parties=5,
            ),
            mpc=MPCSettings(n_parties=5, threshold=1, instance_id=42),
        )

        file_path = tmp_path / "test_config.toml"
        config.save(str(file_path))

        # Load and verify
        loaded = NetworkConfig.from_file(str(file_path))

        assert loaded.network.party_id == 0
        assert loaded.network.bind_address == "127.0.0.1:19200"
        assert loaded.mpc.n_parties == 5
        assert loaded.mpc.threshold == 1
        assert loaded.mpc.instance_id == 42

    def test_from_file_not_found(self):
        """Test from_file with non-existent file"""
        with pytest.raises(FileNotFoundError):
            NetworkConfig.from_file("/nonexistent/path/config.toml")
