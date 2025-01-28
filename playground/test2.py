import ecdsa
import hashlib

def generate_ecdsa_key_pair():
    """Generates an ECDSA key pair using the SECP256k1 curve."""

    # Generate a private key
    private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

    # Get the corresponding public key
    public_key = private_key.verifying_key

    # Return the keys in bytes format
    return private_key.to_string(), public_key.to_string()

def private_key_to_wif(private_key_bytes):
    """Converts a private key (bytes) to Wallet Import Format (WIF)."""
    extended_key = b"\x80" + private_key_bytes  # Add network byte (0x80 for Bitcoin mainnet)
    checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
    wif_key = extended_key + checksum
    return base58_encode(wif_key)

def base58_encode(data):
    """Encodes data to Base58."""
    alphabet = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    b58 = b""
    pad = 0
    for c in data:
        if c == 0:
            pad += 1
        else:
            break
    num = int.from_bytes(data, 'big')
    while num > 0:
        num, mod = divmod(num, 58)
        b58 = alphabet[mod:mod+1] + b58
    return alphabet[0:pad].decode() + b58.decode()

def public_key_to_address(public_key_bytes):
    """Converts a public key (bytes) to a Bitcoin address (P2PKH)."""
    sha256_hash = hashlib.sha256(public_key_bytes).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    extended_ripemd160 = b"\x00" + ripemd160_hash  # Add network byte (0x00 for Bitcoin mainnet)
    checksum = hashlib.sha256(hashlib.sha256(extended_ripemd160).digest()).digest()[:4]
    address = extended_ripemd160 + checksum
    return base58_encode(address)

# Example usage:
private_key, public_key = generate_ecdsa_key_pair()

print("Private Key (bytes):", private_key)
print("Public Key (bytes):", public_key)
print("Private Key (hex):", private_key.hex())
print("Public Key (hex):", public_key.hex())

wif_key = private_key_to_wif(private_key)
print("Private Key (WIF):", wif_key)

address = public_key_to_address(public_key)
print("Bitcoin Address:", address)


# Example of using the keys for signing and verification (as in previous examples)

message = b"Message to sign"

sk = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
signature = sk.sign(message)

vk = ecdsa.VerifyingKey.from_string(public_key, curve=ecdsa.SECP256k1)

try:
    if vk.verify(signature, message):
        print("Signature Verified!")
except ecdsa.BadSignatureError:
    print("Invalid Signature!")