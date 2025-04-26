import hashlib


def sha256(data: bytes) -> bytes:
    """Compute SHA-256 hash of the input data.
    
    Args:
        data: Input binary data to be hashed
        
    Returns:
        bytes: 32-byte SHA-256 hash digest
    """
    return hashlib.sha256(data).digest()


def ripemd160(data: bytes) -> bytes:
    """Compute RIPEMD-160 hash of the input data.
    
    Args:
        data: Input binary data to be hashed
        
    Returns:
        bytes: 20-byte RIPEMD-160 hash digest
        
    Note:
        RIPEMD-160 may not be available on all platforms (depends on OpenSSL)
    """
    return hashlib.new('ripemd160', data).digest()


def hash160(data: bytes) -> bytes:
    """Compute Bitcoin-style HASH160 (SHA-256 followed by RIPEMD-160).
    
    Args:
        data: Input binary data to be hashed
        
    Returns:
        bytes: 20-byte hash digest
        
    Note:
        Commonly used for Bitcoin addresses
    """
    return ripemd160(sha256(data))


def hash256(data: bytes) -> bytes:
    """Compute double SHA-256 hash (SHA-256 of SHA-256).
    
    Args:
        data: Input binary data to be hashed
        
    Returns:
        bytes: 32-byte hash digest
        
    Note:
        Commonly used in Bitcoin's transaction and block hashing
    """
    return sha256(sha256(data))
