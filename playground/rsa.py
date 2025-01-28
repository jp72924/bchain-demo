from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding

from cryptography.hazmat.primitives import serialization

import base64
import binascii

# Generate a new RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# Message to be signed
message = "Hello, world!"

# Hash the message
hash_object = hashes.Hash(hashes.SHA256())
hash_object.update(message.encode())
digest = hash_object.finalize()

# Sign the hash with the private key
signature = private_key.sign(
    digest,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    ),
    hashes.SHA256()
)

# Verify the signature with the public key
public_key.verify(
    signature,
    digest,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    ),
    hashes.SHA256()
)

# Print the private key in PEM format
print(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()).decode('utf-8'))

# Print the public key in PEM format
print(public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8'))

# Convert the signature to base64
base64_signature = base64.b64encode(signature).decode('ascii')
print(f"[ BASE64 SIGNATURE ]: {base64_signature}\n")

# Convert the signature to hexadecimal
hex_signature = binascii.hexlify(signature).decode('ascii')
print(f"[ HEXADECIMAL SIGNATURE ]: {hex_signature}\n")
