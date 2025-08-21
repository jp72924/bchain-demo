import time

from bignum import set_compact
from block import CBlock
from block import CBlockHeader
from crypto import hash256
from transaction import CTransaction
from tx_validator import validate_transaction
from utxo import UTXOSet


class BlockValidationError(Exception):
    pass


def validate_block(block: CBlock, utxo_set: UTXOSet, prev_block_hash: bytes, block_height: int) -> bool:
    """
    Comprehensive block validation pipeline
    Returns True if valid, raises BlockValidationError otherwise
    """
    # 1. Header Validation
    validate_block_header(block, prev_block_hash)

    # 2. Proof-of-Work Validation
    validate_pow(block)

    # 3. Transaction Validation
    validate_block_transactions(block, utxo_set, block_height)

    # 4. Merkle Root Validation
    validate_merkle_root(block)

    return True


def validate_block_header(block: CBlock, prev_block_hash: bytes):
    """Validate block header structure and context"""
    # Check previous block hash
    if block.hashPrevBlock != prev_block_hash:
        raise BlockValidationError(f"Invalid previous block hash. Expected: {prev_block_hash.hex()}, Actual: {block.hashPrevBlock.hex()}")
    
    # Check timestamp (not too far in future)
    current_time = int(time.time())
    MAX_FUTURE_BLOCK_TIME = 2 * 60 * 60  # 2 hours
    if block.nTime > current_time + MAX_FUTURE_BLOCK_TIME:
        raise BlockValidationError(f"Block timestamp {block.nTime} is too far in future")
    
    # Version check
    if block.nVersion < 1:
        raise BlockValidationError("Invalid block version")


def validate_pow(block: CBlock):
    """Validate Proof-of-Work meets target difficulty"""
    # Calculate current block hash
    block_hash = block.get_hash()
    
    # Convert nBits to target
    target = set_compact(block.nBits)

    # Check if hash meets target
    if int.from_bytes(block_hash, 'big') > target:
        raise BlockValidationError("Block hash does not meet target difficulty")


def validate_merkle_root(block: CBlock):
    """Validate computed Merkle root matches header value"""
    computed_root = block.build_merkle_root()
    if computed_root != block.hashMerkleRoot:
        raise BlockValidationError(f"Merkle root mismatch. Computed: {computed_root.hex()}, Header: {block.hashMerkleRoot.hex()}")


def validate_block_transactions(block: CBlock, utxo_set: UTXOSet, block_height: int):
    """Validate all transactions in the block"""
    # Must have at least coinbase transaction
    if len(block.vtx) == 0:
        raise BlockValidationError("Block contains no transactions")
    
    # First transaction must be coinbase
    coinbase = block.vtx[0]
    if not coinbase.is_coinbase():
        raise BlockValidationError("First transaction is not coinbase")
    
    # Validate coinbase structure
    if not (2 <= len(coinbase.vin[0].scriptSig.data) <= 100):
        raise BlockValidationError("Invalid coinbase scriptSig size")
    
    # Process all transactions
    for tx_index, tx in enumerate(block.vtx):
        try:
            if tx_index == 0:  # Coinbase
                # Skip UTXO checks for coinbase
                if len(tx.vout) == 0 or tx.vout[0].nValue <= 0:
                    raise BlockValidationError("Invalid coinbase output")
            else:
                # Full transaction validation
                validate_transaction(tx, utxo_set, block_height)
        except Exception as e:
            raise BlockValidationError(f"Transaction {tx.get_hash().hex()} validation failed: {str(e)}")
