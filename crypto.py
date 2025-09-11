"""
Cryptographic hash functions for blockchain applications.

Provides common hashing operations used in Bitcoin and other cryptocurrencies:
- SHA-256
- RIPEMD-160
- Bitcoin's HASH160 (SHA-256 followed by RIPEMD-160)
- Bitcoin's HASH256 (double SHA-256)
- ECDSA signature verification
"""

import hashlib
from typing import Tuple

try:
    import base58
except ImportError:
    print("Please install the base58 library: pip install base58")
    exit()


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


def verify_ecdsa(pubkey: bytes, sig: bytes, data: bytes) -> bool:
    """Verify an ECDSA signature using secp256k1.

    Args:
        pubkey: The public key bytes (33 or 65 bytes)
        sig: The signature in DER format
        data: The data that was signed (32-byte hash)

    Returns:
        bool: True if signature is valid, False otherwise

    Note:
        This function uses the ecdsa library for verification.
    """
    try:
        from ecdsa import VerifyingKey, SECP256k1
        vk = VerifyingKey.from_string(pubkey, curve=SECP256k1)
        return vk.verify(sig, data, hashfunc=hashlib.sha256)
    except:
        return False


def sign_ecdsa(private_key_bytes: bytes, data: bytes) -> Tuple[bytes, int]:
    """Sign data using ECDSA with secp256k1.

    Args:
        private_key_bytes: 32-byte private key
        data: 32-byte hash to sign

    Returns:
        Tuple of (signature_bytes, recovery_id)
    """
    try:
        from ecdsa import SigningKey, SECP256k1
        from ecdsa.util import sigencode_der_canonize

        sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
        signature = sk.sign(data, hashfunc=hashlib.sha256,
                          sigencode=sigencode_der_canonize)

        # For Bitcoin, we need to add SIGHASH type later
        return signature, 0  # recovery_id not used in Bitcoin currently

    except Exception as e:
        raise ValueError(f"Signing failed: {str(e)}")


def private_key_to_public_key(private_key_bytes: bytes, compressed: bool = True) -> bytes:
    """Convert private key to public key.

    Args:
        private_key_bytes: 32-byte private key
        compressed: Whether to return compressed public key

    Returns:
        Public key bytes (33 bytes for compressed, 65 for uncompressed)
    """
    try:
        from ecdsa import SigningKey, SECP256k1

        sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
        vk = sk.get_verifying_key()

        if compressed:
            # Compressed public key: 0x02/0x03 prefix + x-coordinate
            x = vk.to_string()[:32]
            y = vk.to_string()[32:]
            prefix = b'\x02' if y[-1] % 2 == 0 else b'\x03'
            return prefix + x
        else:
            # Uncompressed public key: 0x04 prefix + x + y
            return b'\x04' + vk.to_string()

    except Exception as e:
        raise ValueError(f"Public key derivation failed: {str(e)}")



def wif_to_private_key(wif_key: str) -> Tuple[bytes, bool, bool]:
    """Convert WIF private key to raw bytes.

    Args:
        wif_key: Wallet Import Format private key

    Returns:
        Tuple of (private_key_bytes, is_compressed, is_testnet)
    """
    try:
        # Decode base58
        decoded = base58.b58decode(wif_key)

        # Check checksum
        checksum = decoded[-4:]
        payload = decoded[:-4]
        computed_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]

        if checksum != computed_checksum:
            raise ValueError("Invalid WIF checksum")

        # Determine network and compression
        version = payload[0]
        is_testnet = version == 0xef  # testnet WIF prefix
        is_mainnet = version == 0x80  # mainnet WIF prefix

        if not (is_testnet or is_mainnet):
            raise ValueError("Invalid WIF version byte")

        # Check if compressed
        is_compressed = len(payload) == 34 and payload[-1] == 0x01

        if is_compressed:
            private_key = payload[1:-1]  # Remove version and compression flag
        else:
            private_key = payload[1:]  # Remove version only

        if len(private_key) != 32:
            raise ValueError("Invalid private key length")

        return private_key, is_compressed, is_testnet

    except Exception as e:
        raise ValueError(f"WIF decoding failed: {str(e)}")
