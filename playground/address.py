import os
import secrets
import hashlib
import base58

try:
    from ecdsa import SigningKey, SECP256k1
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
    wif = base58.b58encode(extended_key + checksum).decode()
    return wif

def private_key_to_public_key(private_key):
    """Derives the public key from the private key using ECDSA."""
    sk = SigningKey.from_secret_exponent(int.from_bytes(private_key, 'big'), curve=SECP256k1)
    vk = sk.verifying_key
    public_key = vk.to_string("compressed")  # Compressed public key
    return public_key

def public_key_to_address(public_key, testnet=False):
    """Converts a public key to a Bitcoin address."""
    prefix = b'\x6f' if testnet else b'\x00'
    sha256_hash = hashlib.sha256(public_key).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    extended_ripemd160 = prefix + ripemd160_hash
    checksum = hashlib.sha256(hashlib.sha256(extended_ripemd160).digest()).digest()[:4]
    address = base58.b58encode(extended_ripemd160 + checksum).decode()
    return address

if __name__ == "__main__":
    private_key = generate_private_key()
    wif = private_key_to_wif(private_key)
    u_wif = private_key_to_wif(private_key, compressed=False)
    public_key = private_key_to_public_key(private_key)
    address = public_key_to_address(public_key)

    print("Private Key (hex):", private_key.hex())
    print("Private Key (Compressed WIF):", wif)
    print("Private Key (WIF):", u_wif)
    print("Public Key (hex):", public_key.hex())
    print("Bitcoin Address:", address)

    # Example of using the keys:
    # (In a real application, NEVER print or store private keys directly like this)
    # You would typically use a hardware wallet or secure key management system.