"""
NetworkBuilder - Fine-grained network configuration

This module provides detailed control over MPC network topology.
Most users should use the high-level Stoffel API with TOML config files instead.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ConnectionMode(Enum):
    """How nodes connect to each other"""
    FULL_MESH = "full_mesh"       # Every node connects to every other node
    STAR = "star"                  # All nodes connect through a central node
    CUSTOM = "custom"              # Manual connection specification


@dataclass
class NodeInfo:
    """
    Information about an MPC network node

    Attributes:
        party_id: The party ID for this node
        bind_address: Address the node listens on
        public_address: Address other nodes use to connect (may differ from bind)
        metadata: Optional additional node metadata
    """
    party_id: int
    bind_address: str
    public_address: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def effective_address(self) -> str:
        """Get the address others should use to connect"""
        return self.public_address or self.bind_address


@dataclass
class Connection:
    """
    A connection between two nodes

    Attributes:
        from_party: Source party ID
        to_party: Destination party ID
        address: Address to connect to
    """
    from_party: int
    to_party: int
    address: str


class NetworkTopology:
    """
    Represents the complete MPC network topology

    This is the result of building a NetworkBuilder.
    """

    def __init__(
        self,
        nodes: List[NodeInfo],
        connections: List[Connection],
        mode: ConnectionMode,
    ):
        self._nodes = {node.party_id: node for node in nodes}
        self._connections = connections
        self._mode = mode

    @property
    def n_parties(self) -> int:
        """Get the number of parties"""
        return len(self._nodes)

    @property
    def mode(self) -> ConnectionMode:
        """Get the connection mode"""
        return self._mode

    def get_node(self, party_id: int) -> Optional[NodeInfo]:
        """Get information about a specific node"""
        return self._nodes.get(party_id)

    def get_nodes(self) -> List[NodeInfo]:
        """Get all nodes in the network"""
        return list(self._nodes.values())

    def get_connections_for(self, party_id: int) -> List[Connection]:
        """Get all connections originating from a party"""
        return [c for c in self._connections if c.from_party == party_id]

    def get_peers_for(self, party_id: int) -> List[Tuple[int, str]]:
        """
        Get peer addresses for a party

        Returns:
            List of (peer_party_id, peer_address) tuples
        """
        connections = self.get_connections_for(party_id)
        return [(c.to_party, c.address) for c in connections]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "nodes": [
                {
                    "party_id": node.party_id,
                    "bind_address": node.bind_address,
                    "public_address": node.public_address,
                    "metadata": node.metadata,
                }
                for node in self._nodes.values()
            ],
            "connections": [
                {
                    "from_party": c.from_party,
                    "to_party": c.to_party,
                    "address": c.address,
                }
                for c in self._connections
            ],
            "mode": self._mode.value,
        }


class NetworkBuilder:
    """
    Builder for MPC network topologies

    NetworkBuilder provides fine-grained control over network configuration.
    Use this when you need:
    - Custom network topologies
    - Non-standard port configurations
    - Complex deployment scenarios

    For most use cases, use Stoffel.network_config_file() with a TOML file.

    Note:
        HoneyBadger MPC requires a minimum of 3 parties.

    Example::

        # Build a full mesh network on localhost (minimum 3 parties)
        network = (NetworkBuilder(n_parties=4)
            .add_node(0, "127.0.0.1:19200")
            .add_node(1, "127.0.0.1:19201")
            .add_node(2, "127.0.0.1:19202")
            .add_node(3, "127.0.0.1:19203")
            .full_mesh()
            .build())

        # Get peer connections for party 0
        peers = network.get_peers_for(0)

    Example with custom topology::

        # Build a star topology with node 0 as the hub
        network = (NetworkBuilder(n_parties=4)
            .add_node(0, "192.168.1.100:19200")
            .add_node(1, "192.168.1.101:19200")
            .add_node(2, "192.168.1.102:19200")
            .add_node(3, "192.168.1.103:19200")
            .star(hub_party_id=0)
            .build())
    """

    def __init__(self, n_parties: int):
        """
        Initialize a NetworkBuilder

        Args:
            n_parties: Total number of parties in the network (must be >= 3)

        Raises:
            ValueError: If n_parties < 3
        """
        # HoneyBadger MPC requires minimum 3 parties
        if n_parties < 3:
            raise ValueError(
                f"HoneyBadger MPC requires at least 3 parties, got n={n_parties}"
            )

        self._n_parties = n_parties
        self._nodes: Dict[int, NodeInfo] = {}
        self._connections: List[Connection] = []
        self._mode: ConnectionMode = ConnectionMode.CUSTOM

    def add_node(
        self,
        party_id: int,
        bind_address: str,
        public_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "NetworkBuilder":
        """
        Add a node to the network

        Args:
            party_id: The party ID for this node
            bind_address: Address the node listens on
            public_address: Address others use to connect (defaults to bind_address)
            metadata: Optional additional node metadata

        Returns:
            Self for method chaining

        Raises:
            ValueError: If party_id is invalid or already exists
        """
        if party_id < 0 or party_id >= self._n_parties:
            raise ValueError(f"party_id must be in range [0, {self._n_parties - 1}]")
        if party_id in self._nodes:
            raise ValueError(f"Node with party_id {party_id} already exists")

        self._nodes[party_id] = NodeInfo(
            party_id=party_id,
            bind_address=bind_address,
            public_address=public_address,
            metadata=metadata or {},
        )
        return self

    def add_connection(
        self,
        from_party: int,
        to_party: int,
        address: Optional[str] = None,
    ) -> "NetworkBuilder":
        """
        Add a connection between two nodes

        Args:
            from_party: Source party ID
            to_party: Destination party ID
            address: Address to connect to (defaults to target's public address)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If either party doesn't exist
        """
        if from_party not in self._nodes:
            raise ValueError(f"Source party {from_party} not found")
        if to_party not in self._nodes:
            raise ValueError(f"Destination party {to_party} not found")

        if address is None:
            address = self._nodes[to_party].effective_address()

        self._connections.append(Connection(
            from_party=from_party,
            to_party=to_party,
            address=address,
        ))
        self._mode = ConnectionMode.CUSTOM
        return self

    def full_mesh(self) -> "NetworkBuilder":
        """
        Create a full mesh topology (every node connects to every other)

        This clears any existing connections and creates bidirectional
        connections between all pairs of nodes.

        Returns:
            Self for method chaining

        Raises:
            ValueError: If not all nodes have been added
        """
        if len(self._nodes) != self._n_parties:
            raise ValueError(
                f"All {self._n_parties} nodes must be added before creating full mesh"
            )

        self._connections = []
        for from_id in range(self._n_parties):
            for to_id in range(self._n_parties):
                if from_id != to_id:
                    self._connections.append(Connection(
                        from_party=from_id,
                        to_party=to_id,
                        address=self._nodes[to_id].effective_address(),
                    ))

        self._mode = ConnectionMode.FULL_MESH
        return self

    def star(self, hub_party_id: int = 0) -> "NetworkBuilder":
        """
        Create a star topology with a central hub node

        All non-hub nodes connect only to the hub. The hub connects to all nodes.

        Args:
            hub_party_id: The party ID of the hub node

        Returns:
            Self for method chaining

        Raises:
            ValueError: If not all nodes have been added or hub doesn't exist
        """
        if len(self._nodes) != self._n_parties:
            raise ValueError(
                f"All {self._n_parties} nodes must be added before creating star topology"
            )
        if hub_party_id not in self._nodes:
            raise ValueError(f"Hub party {hub_party_id} not found")

        self._connections = []
        hub_address = self._nodes[hub_party_id].effective_address()

        for party_id in range(self._n_parties):
            if party_id != hub_party_id:
                # Non-hub connects to hub
                self._connections.append(Connection(
                    from_party=party_id,
                    to_party=hub_party_id,
                    address=hub_address,
                ))
                # Hub connects to non-hub
                self._connections.append(Connection(
                    from_party=hub_party_id,
                    to_party=party_id,
                    address=self._nodes[party_id].effective_address(),
                ))

        self._mode = ConnectionMode.STAR
        return self

    def localhost(self, base_port: int = 19200) -> "NetworkBuilder":
        """
        Configure all nodes on localhost with sequential ports

        Convenience method for local testing.

        Args:
            base_port: Starting port number (party 0 gets base_port, party 1 gets base_port+1, etc.)

        Returns:
            Self for method chaining
        """
        for party_id in range(self._n_parties):
            address = f"127.0.0.1:{base_port + party_id}"
            self._nodes[party_id] = NodeInfo(
                party_id=party_id,
                bind_address=address,
                public_address=None,
            )
        return self

    def build(self) -> NetworkTopology:
        """
        Build the network topology

        Returns:
            NetworkTopology instance

        Raises:
            ValueError: If configuration is incomplete
        """
        if len(self._nodes) != self._n_parties:
            raise ValueError(
                f"Expected {self._n_parties} nodes, got {len(self._nodes)}"
            )

        return NetworkTopology(
            nodes=list(self._nodes.values()),
            connections=self._connections,
            mode=self._mode,
        )

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "NetworkBuilder":
        """
        Create a NetworkBuilder from a configuration dictionary

        Args:
            config: Network configuration dictionary

        Returns:
            NetworkBuilder instance
        """
        nodes = config.get("nodes", [])
        n_parties = len(nodes)

        builder = cls(n_parties=n_parties)

        for node_config in nodes:
            builder.add_node(
                party_id=node_config["party_id"],
                bind_address=node_config["bind_address"],
                public_address=node_config.get("public_address"),
                metadata=node_config.get("metadata", {}),
            )

        for conn_config in config.get("connections", []):
            builder.add_connection(
                from_party=conn_config["from_party"],
                to_party=conn_config["to_party"],
                address=conn_config.get("address"),
            )

        return builder
