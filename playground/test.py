from Crypto.Hash import RIPEMD160
from Crypto.Hash import SHA256

def calculate_ripemd160(data):
    # Create a new RIPEMD-160 hash object
    h = RIPEMD160.new()
    # Update the hash object with the input data
    h.update(data.encode('utf-8'))
    # Return the hexadecimal digest of the hash
    return h.hexdigest()

# Example usage:
input_data = "Hello, World!"
hash_value = calculate_ripemd160(input_data)
print("RIPEMD-160 Hash:", hash_value)

def calculate_sha256(data):
    # Create a new SHA-256 hash object
    hash_object = SHA256.new()
    # Update the hash object with the data (must be in bytes)
    hash_object.update(data.encode('utf-8'))
    # Return the hexadecimal digest of the hash
    return hash_object.hexdigest()

# Example usage:
input_data = "Hello, World!"
hash_value = calculate_sha256(input_data)
print("SHA-256 Hash:", hash_value)
