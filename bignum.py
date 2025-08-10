def set_compact(n_compact: int) -> int:
    """
    Convert nBits to 256-bit target integer (Bitcoin Core compatible)
    Follows arith_uint256::SetCompact() from Bitcoin Core
    """
    n_size = n_compact >> 24
    coefficient = n_compact & 0x007fffff

    if n_size <= 3:
        target = coefficient >> (8 * (3 - n_size))
    else:
        target = coefficient << (8 * (n_size - 3))

    # Cap to 256 bits (prevent overflow)
    return target & ((1 << 256) - 1)


def get_compact(target: int) -> int:
    """
    Converts a full 256-bit integer to Bitcoin's compact representation (nBits).
    Equivalent to CBigNum::GetCompact() in Bitcoin Core.
    """
    if target == 0:
        return 0

    n_size = (target.bit_length() + 7) // 8
    if n_size <= 3:
        coefficient = target << (8 * (3 - n_size))
    else:
        coefficient = target >> (8 * (n_size - 3))

    # The compact format only uses the lower 23 bits for the mantissa
    if coefficient >= 0x00800000:
        coefficient >>= 8
        n_size += 1

    n_compact = (n_size << 24) | (coefficient & 0x007fffff)
    return n_compact
