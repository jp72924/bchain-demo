import os
import secrets
import hashlib
import base58

try:
    from ecdsa import SigningKey, SECP256k1, VerifyingKey
except ImportError:
    print("Please install the ecdsa library: pip install ecdsa")
    exit()

def generate_private_key():
    """Generates a cryptographically secure 256-bit private key."""
    # Method 1 (using secrets module - Python 3.6+):
    private_key = secrets.token_bytes(32)

    # Method 2 (using os.urandom for broader compatibility):
    # private_key = os.urandom(32)

    return private_key

def private_key_to_wif(private_key, compressed=True, testnet=False):
    """Converts a private key to WIF format."""
    prefix = b'\xef' if testnet else b'\x80'
    suffix = b'\x01' if compressed else b''
    extended_key = prefix + private_key + suffix
    checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
    return base58.b58encode(extended_key + checksum).decode()

def private_key_to_public_key(private_key, compressed=True):
    """Derives the public key from the private key using ECDSA."""
    sk = SigningKey.from_secret_exponent(int.from_bytes(private_key, 'big'), curve=SECP256k1)
    vk = sk.verifying_key

    if compressed:
        return vk.to_string("compressed")  # Compressed public key (33 bytes)
    else:
        # Uncompressed public key (65 bytes) with 0x04 prefix
        return b'\x04' + vk.to_string("uncompressed")[1:]  # Ensure proper format

def public_key_to_address(public_key, testnet=False):
    """Converts a public key to a Bitcoin address."""
    prefix = b'\x6f' if testnet else b'\x00'
    sha256_hash = hashlib.sha256(public_key).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    extended_ripemd160 = prefix + ripemd160_hash
    checksum = hashlib.sha256(hashlib.sha256(extended_ripemd160).digest()).digest()[:4]
    return base58.b58encode(extended_ripemd160 + checksum).decode()

def format_key_with_separators(key_hex, group_size=8):
    """Formats a hex key with spaces for better readability."""
    return ' '.join([key_hex[i:i+group_size] for i in range(0, len(key_hex), group_size)])

if __name__ == "__main__":
    print("=" * 60)
    print("BITCOIN WALLET ADDRESS GENERATION DEMONSTRATION")
    print("=" * 60)

    # Generate a private key
    private_key = generate_private_key()
    print("\n1. PRIVATE KEY (32 bytes, 256 bits):")
    print(f"   Hex: {format_key_with_separators(private_key.hex())}")

    # Show WIF formats
    wif_compressed = private_key_to_wif(private_key, compressed=True)
    wif_uncompressed = private_key_to_wif(private_key, compressed=False)

    print("\n2. WALLET IMPORT FORMAT (WIF):")
    print(f"   Compressed WIF (52 chars): {wif_compressed}")
    print(f"   Uncompressed WIF (51 chars): {wif_uncompressed}")
    print("   Note: The compressed WIF has a '01' suffix before encoding,")
    print("   which signals that derived public keys should be compressed.")

    # Generate both public key formats
    public_key_compressed = private_key_to_public_key(private_key, compressed=True)
    public_key_uncompressed = private_key_to_public_key(private_key, compressed=False)

    print("\n3. PUBLIC KEYS:")
    print(f"   Compressed (33 bytes): {format_key_with_separators(public_key_compressed.hex())}")
    print(f"   Uncompressed (65 bytes): {format_key_with_separators(public_key_uncompressed.hex())}")
    print("   Note: Compressed public keys use prefix 02/03 instead of 04,")
    print("   and only include the X coordinate + parity of Y.")

    # Generate addresses from both public key formats
    address_from_compressed = public_key_to_address(public_key_compressed)
    address_from_uncompressed = public_key_to_address(public_key_uncompressed)

    print("\n4. BITCOIN ADDRESSES:")
    print(f"   From compressed public key: {address_from_compressed}")
    print(f"   From uncompressed public key: {address_from_uncompressed}")
    print("   Note: These are different addresses! Funds sent to one")
    print("   cannot be accessed from the other, despite same private key.")

    # Demonstrate the technical differences
    print("\n5. TECHNICAL DETAILS:")
    print("   - Private key: Random 256-bit number")
    print("   - Public key: Derived via elliptic curve multiplication (secp256k1)")
    print("   - Compressed public key: 33 bytes (prefix 02/03 + X coordinate)")
    print("   - Uncompressed public key: 65 bytes (prefix 04 + X + Y coordinates)")
    print("   - Address: RIPEMD160(SHA256(public_key)) with version prefix and checksum")

    print("\n6. IMPORTANT SECURITY NOTES:")
    print("   - Never share your private key or WIF")
    print("   - In production, use hardware wallets or secure key management")
    print("   - This is a educational tool only")

    print("\n" + "=" * 60)
