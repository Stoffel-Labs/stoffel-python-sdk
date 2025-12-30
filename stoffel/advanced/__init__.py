"""
Advanced Stoffel SDK Components

This module provides lower-level components for advanced use cases:
- ShareManager: Direct control over secret sharing operations
- NetworkBuilder: Fine-grained network configuration

Most users should use the high-level Stoffel API instead.
These components are for advanced users who need:
- Custom secret sharing workflows
- Complex network topologies
- Integration with existing systems

Usage::

    from stoffel.advanced import ShareManager, NetworkBuilder

    # Low-level share management
    manager = ShareManager(n_parties=5, threshold=1)
    shares = manager.create_shares(secret=42)

    # Custom network setup
    network = NetworkBuilder(n_parties=5).add_node(0, "127.0.0.1:19200").build()
"""

from .share_manager import ShareManager
from .network_builder import NetworkBuilder

__all__ = [
    "ShareManager",
    "NetworkBuilder",
]
