import hashlib

def sha256(data):
    """
    Generate a SHA-256 hash of the given data.

    Parameters:
        data (str, bytes, or int): The input data to hash.
            - If a string is provided, it will be encoded to bytes.
            - If an integer is provided, it will be converted to bytes.

    Returns:
        str: The SHA-256 hash in hexadecimal format.
    """
    # Ensure the input data is in bytes
    if isinstance(data, str):
        # Convert string to bytes using UTF-8 encoding
        data = data.encode('utf-8')
    elif isinstance(data, int):
        # Convert integer to bytes using big-endian byte order
        # Calculate the number of bytes needed to represent the integer
        byte_length = (data.bit_length() + 7) // 8 or 1
        data = data.to_bytes(byte_length, byteorder='big', signed=False)
    elif not isinstance(data, bytes):
        raise TypeError("Unsupported data type. Expected str, bytes, or int.")

    # Create a new SHA-256 hash object
    sha256_obj = hashlib.sha256()
    
    # Update the hash object with the input data
    sha256_obj.update(data)
    
    # Return the hexadecimal digest of the hash
    return sha256_obj.hexdigest()

# Example usage
if __name__ == "__main__":
    # Hash a string
    input_string = "Hello, World!"
    hashed_string = sha256(input_string)
    print(f"SHA-256 Hash of '{input_string}': {hashed_string}")

    # Hash bytes
    input_bytes = b"Hello, World!"
    hashed_bytes = sha256(input_bytes)
    print(f"SHA-256 Hash of {input_bytes}: {hashed_bytes}")

    # Hash an integer
    input_int = 123456789
    hashed_int = sha256(input_int)
    print(f"SHA-256 Hash of {input_int}: {hashed_int}")