"""
ShareManager - Low-level secret sharing operations

This module provides direct control over secret sharing for advanced use cases.
Most users should use the high-level MPCClient API instead.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ShareScheme(Enum):
    """Secret sharing scheme"""
    SHAMIR = "shamir"
    ROBUST_SHAMIR = "robust_shamir"


@dataclass
class Share:
    """
    A single share of a secret value

    Attributes:
        party_id: ID of the party this share belongs to
        value: The share value (serialized bytes)
        scheme: The sharing scheme used
    """
    party_id: int
    value: bytes
    scheme: ShareScheme


@dataclass
class ShareSet:
    """
    A complete set of shares for a secret

    Attributes:
        shares: List of individual shares
        threshold: Minimum shares needed for reconstruction
        n_parties: Total number of shares
        scheme: The sharing scheme used
    """
    shares: List[Share]
    threshold: int
    n_parties: int
    scheme: ShareScheme

    def get_share(self, party_id: int) -> Optional[Share]:
        """Get the share for a specific party"""
        for share in self.shares:
            if share.party_id == party_id:
                return share
        return None

    def to_bytes_list(self) -> List[bytes]:
        """Convert shares to a list of bytes for distribution"""
        return [share.value for share in self.shares]


class ShareManager:
    """
    Low-level secret sharing manager

    ShareManager provides direct control over secret sharing operations.
    Use this when you need:
    - Custom share distribution workflows
    - Integration with external systems
    - Manual share management

    For most use cases, use MPCClient.generate_input_shares() instead.

    Note:
        HoneyBadger MPC requires a minimum of 3 parties.

    Example::

        # Create a share manager (minimum 3 parties)
        manager = ShareManager(n_parties=4, threshold=1)

        # Create shares for a secret
        share_set = manager.create_shares(secret=42)

        # Get a specific party's share
        party_0_share = share_set.get_share(0)

        # Reconstruct from shares (requires threshold+1 shares)
        secret = manager.reconstruct([share_set.shares[0], share_set.shares[1]])
    """

    def __init__(
        self,
        n_parties: int,
        threshold: int,
        scheme: ShareScheme = ShareScheme.ROBUST_SHAMIR,
    ):
        """
        Initialize a ShareManager

        Args:
            n_parties: Total number of parties (shares to create)
            threshold: Reconstruction threshold (t shares can reconstruct)
            scheme: Secret sharing scheme to use

        Raises:
            ValueError: If n_parties < 3*threshold + 1 for robust schemes
        """
        # HoneyBadger MPC requires minimum 3 parties
        if n_parties < 3:
            raise ValueError(
                f"HoneyBadger MPC requires at least 3 parties, got n={n_parties}"
            )
        if threshold < 0:
            raise ValueError("threshold must be non-negative")

        # Validate HoneyBadger constraint for robust schemes
        if scheme == ShareScheme.ROBUST_SHAMIR and n_parties < 3 * threshold + 1:
            raise ValueError(
                f"For robust sharing, n_parties ({n_parties}) must be >= 3*threshold+1 ({3 * threshold + 1})"
            )

        self._n_parties = n_parties
        self._threshold = threshold
        self._scheme = scheme

    @property
    def n_parties(self) -> int:
        """Get the number of parties"""
        return self._n_parties

    @property
    def threshold(self) -> int:
        """Get the reconstruction threshold"""
        return self._threshold

    @property
    def scheme(self) -> ShareScheme:
        """Get the sharing scheme"""
        return self._scheme

    def create_shares(self, secret: int) -> ShareSet:
        """
        Create secret shares for a value

        Args:
            secret: The secret integer value to share

        Returns:
            ShareSet containing shares for all parties

        Raises:
            ValueError: If secret is out of field range
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Share creation requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def create_shares_batch(self, secrets: List[int]) -> List[ShareSet]:
        """
        Create shares for multiple secrets efficiently

        Args:
            secrets: List of secret integers to share

        Returns:
            List of ShareSets, one for each secret
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Batch share creation requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def reconstruct(self, shares: List[Share]) -> int:
        """
        Reconstruct a secret from shares

        Args:
            shares: List of shares (must have at least threshold+1)

        Returns:
            The reconstructed secret value

        Raises:
            ValueError: If not enough shares provided
        """
        if len(shares) < self._threshold + 1:
            raise ValueError(
                f"Need at least {self._threshold + 1} shares, got {len(shares)}"
            )

        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Share reconstruction requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def verify_share(self, share: Share, commitment: bytes) -> bool:
        """
        Verify a share against a commitment (for robust schemes)

        Args:
            share: The share to verify
            commitment: The commitment to verify against

        Returns:
            True if the share is valid
        """
        if self._scheme != ShareScheme.ROBUST_SHAMIR:
            raise ValueError("Share verification only supported for robust schemes")

        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Share verification requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def generate_random_shares(self) -> ShareSet:
        """
        Generate shares of a random value

        This is useful for generating preprocessing material.

        Returns:
            ShareSet containing shares of a random value
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Random share generation requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def add_shares(self, a: ShareSet, b: ShareSet) -> ShareSet:
        """
        Add two shared values (local operation)

        Secret sharing is additively homomorphic, so this can be done
        without communication.

        Args:
            a: First shared value
            b: Second shared value

        Returns:
            ShareSet containing shares of a + b
        """
        if a.n_parties != b.n_parties or a.threshold != b.threshold:
            raise ValueError("ShareSets must have matching parameters")

        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Share addition requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )

    def multiply_by_constant(self, shares: ShareSet, constant: int) -> ShareSet:
        """
        Multiply a shared value by a public constant (local operation)

        Args:
            shares: The shared value
            constant: The public constant to multiply by

        Returns:
            ShareSet containing shares of shares * constant
        """
        # TODO: Implement when MPC protocol bindings are available
        raise NotImplementedError(
            "Constant multiplication requires MPC protocol bindings. "
            "This will be implemented when PyO3 bindings are available."
        )
