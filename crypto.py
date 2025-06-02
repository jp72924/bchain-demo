"""
Cryptographic hash functions for blockchain applications.

Provides common hashing operations used in Bitcoin and other cryptocurrencies:
- SHA-256
- RIPEMD-160
- Bitcoin's HASH160 (SHA-256 followed by RIPEMD-160)
- Bitcoin's HASH256 (double SHA-256)
"""

import hashlib


def sha256(data: bytes) -> bytes:
    """Compute SHA-256 hash of the input data.

    Args:
        data: Input binary data to be hashed

    Returns:
        32-byte SHA-256 hash digest
    """
    return hashlib.sha256(data).digest()


def ripemd160(data: bytes) -> bytes:
    """Compute RIPEMD-160 hash of the input data.

    Args:
        data: Input binary data to be hashed

    Returns:
        20-byte RIPEMD-160 hash digest

    Raises:
        ValueError: If RIPEMD-160 is not available on the platform

    Note:
        Availability depends on the underlying OpenSSL implementation
    """
    try:
        return hashlib.new('ripemd160', data).digest()
    except ValueError as e:
        raise ValueError(
            "RIPEMD-160 not available. Requires OpenSSL with RIPEMD-160 support."
        ) from e


def hash160(data: bytes) -> bytes:
    """Compute Bitcoin-style HASH160 (SHA-256 followed by RIPEMD-160).

    Args:
        data: Input binary data to be hashed

    Returns:
        20-byte hash digest

    Note:
        Commonly used for Bitcoin address generation

    Raises:
        ValueError: If RIPEMD-160 is not available
    """
    return ripemd160(sha256(data))


def hash256(data: bytes) -> bytes:
    """Compute double SHA-256 hash (SHA-256 of SHA-256).

    Args:
        data: Input binary data to be hashed

    Returns:
        32-byte hash digest

    Note:
        Standard hashing method for Bitcoin transactions and blocks
    """
    return sha256(sha256(data))
