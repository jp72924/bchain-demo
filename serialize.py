
def compact_size(value: int) -> bytes:
    """Convert an integer to Bitcoin-style compact size encoding (also known as "varint").
    
    Bitcoin uses a compact size format for storing integers in a space-efficient manner:
    - Values < 0xfd: 1 byte
    - Values <= 0xffff: 0xfd prefix + 2 bytes
    - Values <= 0xffffffff: 0xfe prefix + 4 bytes
    - Larger values: 0xff prefix + 8 bytes

    Args:
        value: Integer to be encoded (must be non-negative)

    Returns:
        bytes: Compact size encoded byte representation

    Raises:
        ValueError: If input is negative
    """
    if value < 0:
        raise ValueError("Compact size cannot encode negative values")
    if value < 0xfd:
        return value.to_bytes(1, 'little')
    elif value <= 0xffff:
        return b'\xfd' + value.to_bytes(2, 'little')
    elif value <= 0xffffffff:
        return b'\xfe' + value.to_bytes(4, 'little')
    else:
        return b'\xff' + value.to_bytes(8, 'little')

def read_compact_size(stream):
    """Deserialize a Bitcoin-style compact size integer from a stream."""
    prefix = stream.read(1)
    if not prefix:
        raise ValueError("Unexpected end of stream")
    size_byte = prefix[0]
    if size_byte < 0xfd:
        return size_byte
    elif size_byte == 0xfd:
        data = stream.read(2)
        if len(data) != 2:
            raise ValueError("Insufficient data for 2-byte compact size")
        return int.from_bytes(data, 'little')
    elif size_byte == 0xfe:
        data = stream.read(4)
        if len(data) != 4:
            raise ValueError("Insufficient data for 4-byte compact size")
        return int.from_bytes(data, 'little')
    elif size_byte == 0xff:
        data = stream.read(8)
        if len(data) != 8:
            raise ValueError("Insufficient data for 8-byte compact size")
        return int.from_bytes(data, 'little')
    else:
        raise ValueError("Invalid compact size prefix")