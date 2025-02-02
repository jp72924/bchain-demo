from hashlib import sha256
import io
from datetime import datetime

from transaction import Outpoint
from transaction import TxIn
from transaction import TxOut
from transaction import Transaction


class Block:
    def __init__(self, version, prev_block, merkle_root, time, bits, nonce):
        """
        Initializes a Block instance.

        Args:
            version (int): The block version number.
            prev_block (bytes): The hash of the previous block in the blockchain.
            merkle_root (bytes): The Merkle root hash of the block's transactions.
            time (int): The Unix epoch time when the miner started hashing the header.
            bits (int): The difficulty target for block hash.
            nonce (int): The nonce value used in the block header hashing.
        """
        self.version = version
        self.prev_block = prev_block
        self.merkle_root = merkle_root
        self.time = time  # Unix epoch time when the miner started hashing the header
        self.bits = bits
        self.nonce = nonce
        self.vtx = []

    def add_transaction(self, transaction):
        self.vtx.append(transaction)

    def _merkle_root(self):
        """Calculate the Merkle root for the block's transactions"""
        tx_hashes = [tx.hash() for tx in self.vtx]

        # If a block only has a coinbase transaction, the TXID is used as merkle root hash
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:  # Ensure even number of hashes
                tx_hashes.append(tx_hashes[-1])

            tx_hashes = [
                sha256((tx_hashes[i] + tx_hashes[i + 1])).digest()
                for i in range(0, len(tx_hashes), 2)
            ]

        self.merkle_root = tx_hashes[0] if tx_hashes else b''
        return self.merkle_root

    def serialize(self):
        """Serializes the block header into a byte string"""
        stream = io.BytesIO()
        stream.write(self.prev_block)
        stream.write(self.merkle_root)
        stream.write(self.time.to_bytes(4, 'little'))
        stream.write(self.nonce.to_bytes(4, 'little'))
        return stream.getvalue()

    def hash(self):
        """Calculate the block's hash"""
        raw_block = self.serialize()
        return sha256(sha256(raw_block).digest()).digest()

    def mine(self):
        """Mine the block by finding a valid nonce."""
        self.time = int(datetime.now().timestamp())
        target = (1 << (256 - self.bits)) - 1  # Calculate target from bits

        while int(self.hash().hex(), 16) > target:
            self.nonce += 1


def create_coinbase_transaction(coinbase_data, miner_reward, miner_script_pubkey):
    """
    Creates a new coinbase transaction paying the miner.

    Args:
        coinbase_data (bytes, optional): Extra data included in the coinbase transaction. Defaults to an empty byte string.
        miner_reward (int): The amount of the miner reward in satoshis.
        miner_script_pubkey (bytes): The script public key of the miner's address.

    Returns:
        Transaction: A new coinbase transaction instance.
    """
    coinbase_input = TxIn(
        prevout=Outpoint(hash=b'\x00' * 32, index=0xffffffff),  # Special prevout for coinbase
        script_sig=coinbase_data
    )
    coinbase_output = TxOut(value=miner_reward, script_pubkey=miner_script_pubkey)

    return Transaction(vin=[coinbase_input], vout=[coinbase_output])


def main():
    public_key = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    
    # Create a coinbase transaction
    coinbase = create_coinbase_transaction(
        block_height=0,
        coinbase_data=b'',
        miner_reward=5000000000,
        miner_script_pubkey=public_key
    )

    # Serialize and hash the transaction
    raw_transaction = coinbase.serialize()
    tx_hash = coinbase.hash()
    print(f"Coinbase Hash: {tx_hash.hex()}")

    # Create a block
    block = Block(
        version=1,
        prev_block=b'\x00' * 32,
        merkle_root="",
        time=int(datetime.now().timestamp()),
        bits=20,  # Simplified difficulty for demonstration
        nonce=0,
    )

    block.add_transaction(coinbase)
    block.merkle_root = block._merkle_root()  # Calculate Merkle root

    # Mine the block
    block.mine()

    print("Previous Block:", block.prev_block.hex())
    print("Merkle Root:", block.merkle_root.hex())
    print(f"Block Timestamp: {datetime.fromtimestamp(block.time)} ({block.time} seconds since January 1st, 1970)")
    print("Nonce:", block.nonce)
    print("Block Data:", block.serialize().hex())
    print("Block Hash:", block.hash().hex())

if __name__ == '__main__':
    main()
