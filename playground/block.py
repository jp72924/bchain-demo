import hashlib
import time
import struct

class Transaction:
    def __init__(self, inputs, outputs):
        """
        :param inputs: List of tuples [(prev_txid, output_index, scriptSig)]
        :param outputs: List of tuples [(amount, scriptPubKey)]
        """
        self.inputs = inputs
        self.outputs = outputs

    def serialize(self):
        serialized_inputs = "".join(
            f"{txid}{output_index:08x}{scriptSig}" for txid, output_index, scriptSig in self.inputs
        )
        serialized_outputs = "".join(
            f"{amount:016x}{scriptPubKey}" for amount, scriptPubKey in self.outputs
        )
        return serialized_inputs + serialized_outputs

    def hash(self):
        return hashlib.sha256(self.serialize().encode()).hexdigest()

class Block:
    def __init__(self, version, prev_block_hash, merkle_root, timestamp, bits, nonce):
        """
        :param version: Block version number
        :param prev_block_hash: Hash of the previous block
        :param merkle_root: Merkle root hash of the transactions
        :param timestamp: Unix timestamp when the block was created
        :param bits: Difficulty target in compact format
        :param nonce: Value for miners to adjust to meet the target hash
        """
        self.version = version
        self.prev_block_hash = prev_block_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.bits = bits
        self.nonce = nonce
        self.transactions = []

    def add_transaction(self, transaction):
        self.transactions.append(transaction)

    def _merkle_root(self):
        """Calculate the Merkle root for the block's transactions."""
        tx_hashes = [tx.hash() for tx in self.transactions]

        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:  # Ensure even number of hashes
                tx_hashes.append(tx_hashes[-1])

            tx_hashes = [
                hashlib.sha256((tx_hashes[i] + tx_hashes[i + 1]).encode()).hexdigest()
                for i in range(0, len(tx_hashes), 2)
            ]

        return tx_hashes[0] if tx_hashes else ""

    def serialize_header(self):
        """Serialize the block header."""
        return (
            f"{self.version:08x}{self.prev_block_hash}{self._merkle_root()}{int(self.timestamp):08x}{self.bits:08x}{self.nonce:08x}"
        )

    def hash(self):
        """Calculate the block's hash."""
        return hashlib.sha256(hashlib.sha256(self.serialize_header().encode()).digest()).hexdigest()

    def mine(self):
        """Mine the block by finding a valid nonce."""
        target = (1 << (256 - self.bits)) - 1  # Calculate target from bits

        while int(self.hash(), 16) > target:
            self.nonce += 1
            
        print(f"Block mined! Nonce: {self.nonce}, Hash: {self.hash()}")

# Example Usage
if __name__ == "__main__":
    # Create a coinbase transaction
    coinbase_tx = Transaction(
        inputs=[("0" * 64, 0, "coinbase")],  # Coinbase transactions have no previous input
        outputs=[(50, "recipient_pubkey_hash")]
    )

    # Create a block
    genesis_block = Block(
        version=1,
        prev_block_hash="0" * 64,
        merkle_root="",
        timestamp=int(time.time()),
        bits=32,  # Simplified difficulty for demonstration
        nonce=0,
    )

    genesis_block.add_transaction(coinbase_tx)
    genesis_block.merkle_root = genesis_block._merkle_root()  # Calculate Merkle root

    # Mine the block
    genesis_block.mine()

    print("Genesis Block Hash:", genesis_block.hash())
