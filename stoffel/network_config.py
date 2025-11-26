"""
Network Configuration for Stoffel MPC

This module provides network configuration types for Stoffel MPC,
supporting TOML configuration files for easy deployment configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from pathlib import Path


@dataclass
class NetworkSettings:
    """
    Network settings for an MPC party

    Attributes:
        party_id: This party's ID
        bind_address: Address to bind to (e.g., "127.0.0.1:19200")
        bootstrap_address: Address of the bootstrap node
        min_parties: Minimum parties required to start
    """
    party_id: int
    bind_address: str
    bootstrap_address: str
    min_parties: int


@dataclass
class MPCSettings:
    """
    MPC protocol settings

    Attributes:
        n_parties: Total number of parties in the MPC network
        threshold: Byzantine fault tolerance threshold (n >= 3t + 1)
        instance_id: Optional unique computation instance ID
    """
    n_parties: int
    threshold: int
    instance_id: Optional[int] = None


@dataclass
class NetworkConfig:
    """
    Complete network configuration for Stoffel MPC

    This configuration can be loaded from a TOML file or created programmatically.

    Example TOML file:
        [network]
        party_id = 0
        bind_address = "127.0.0.1:19200"
        bootstrap_address = "127.0.0.1:19200"
        min_parties = 5

        [mpc]
        n_parties = 5
        threshold = 1
        instance_id = 42

    Example usage:
        # Load from file
        config = NetworkConfig.from_file("stoffel.toml")

        # Create programmatically
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
    """
    network: NetworkSettings
    mpc: MPCSettings

    @classmethod
    def from_file(cls, path: str) -> "NetworkConfig":
        """
        Load network configuration from a TOML file

        Args:
            path: Path to the TOML configuration file

        Returns:
            NetworkConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        import tomllib  # Python 3.11+, use tomli for older versions

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NetworkConfig":
        """
        Create NetworkConfig from a dictionary

        Args:
            data: Configuration dictionary

        Returns:
            NetworkConfig instance

        Raises:
            ValueError: If required fields are missing
        """
        if "network" not in data:
            raise ValueError("Missing 'network' section in configuration")
        if "mpc" not in data:
            raise ValueError("Missing 'mpc' section in configuration")

        network_data = data["network"]
        mpc_data = data["mpc"]

        network = NetworkSettings(
            party_id=network_data.get("party_id", 0),
            bind_address=network_data.get("bind_address", "127.0.0.1:19200"),
            bootstrap_address=network_data.get("bootstrap_address", "127.0.0.1:19200"),
            min_parties=network_data.get("min_parties", 1),
        )

        mpc = MPCSettings(
            n_parties=mpc_data.get("n_parties", 5),
            threshold=mpc_data.get("threshold", 1),
            instance_id=mpc_data.get("instance_id"),
        )

        return cls(network=network, mpc=mpc)

    def validate(self) -> None:
        """
        Validate the network configuration

        Raises:
            ValueError: If configuration is invalid
        """
        # HoneyBadger MPC requires minimum 3 parties
        if self.mpc.n_parties < 3:
            raise ValueError(
                f"HoneyBadger MPC requires at least 3 parties, got n={self.mpc.n_parties}"
            )

        # Validate HoneyBadger constraint: n >= 3t + 1
        if self.mpc.n_parties < 3 * self.mpc.threshold + 1:
            raise ValueError(
                f"Invalid MPC configuration: n_parties ({self.mpc.n_parties}) "
                f"must be >= 3*threshold+1 ({3 * self.mpc.threshold + 1})"
            )

        # Validate party_id
        if self.network.party_id < 0 or self.network.party_id >= self.mpc.n_parties:
            raise ValueError(
                f"Invalid party_id ({self.network.party_id}): "
                f"must be in range [0, {self.mpc.n_parties - 1}]"
            )

        # Validate min_parties
        if self.network.min_parties < 1 or self.network.min_parties > self.mpc.n_parties:
            raise ValueError(
                f"Invalid min_parties ({self.network.min_parties}): "
                f"must be in range [1, {self.mpc.n_parties}]"
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization

        Returns:
            Configuration dictionary
        """
        return {
            "network": {
                "party_id": self.network.party_id,
                "bind_address": self.network.bind_address,
                "bootstrap_address": self.network.bootstrap_address,
                "min_parties": self.network.min_parties,
            },
            "mpc": {
                "n_parties": self.mpc.n_parties,
                "threshold": self.mpc.threshold,
                "instance_id": self.mpc.instance_id,
            },
        }

    def save(self, path: str) -> None:
        """
        Save configuration to a TOML file

        Args:
            path: Path to save the configuration to
        """
        # tomllib is read-only, so we need to write manually or use tomli-w
        lines = [
            "[network]",
            f"party_id = {self.network.party_id}",
            f'bind_address = "{self.network.bind_address}"',
            f'bootstrap_address = "{self.network.bootstrap_address}"',
            f"min_parties = {self.network.min_parties}",
            "",
            "[mpc]",
            f"n_parties = {self.mpc.n_parties}",
            f"threshold = {self.mpc.threshold}",
        ]

        if self.mpc.instance_id is not None:
            lines.append(f"instance_id = {self.mpc.instance_id}")

        with open(path, "w") as f:
            f.write("\n".join(lines))
