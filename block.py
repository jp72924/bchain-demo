from hashlib import sha256
import io
from datetime import datetime

from transaction import Outpoint, TxIn, TxOut, Transaction


class Block:
    def __init__(self, prev_block, bits, txns=[]):
        # Block header
        self.prev_block = prev_block
        self.merkle_root = b''
        self.time = 0  # Unix epoch time when the miner started hashing the header
        self.bits = bits
        self.nonce = 0

        # Block content
        self.txns = txns
        self.tx_count = len(self.txns)

        self._merkle_root()

    def add(self, tx):
        self.txns.append(tx)

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

    def _merkle_root(self):
        """Calculate the Merkle root for the block's transactions"""
        tx_hashes = [tx.hash() for tx in self.txns]

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

    def mine(self):
        """Mine the block by finding a valid nonce."""
        self.time = int(datetime.now().timestamp())
        target = (1 << (256 - self.bits)) - 1  # Calculate target from bits

        while int(self.hash().hex(), 16) > target:
            self.nonce += 1


def create_coinbase(miner_public_key, block_subsidy=5000000000):
    # Create sample UTXOs
    prevout = Outpoint(
        hash=bytes.fromhex("0" * 64),
        index=int('0xffffffff', 16),  # 2 ^ 32 (maximun value)
    )

    tx_in = TxIn(
        prevout=prevout,
        script_sig=b''  # Sender's signature (signs transaction hash using the private key)
    )

    tx_out = TxOut(
        value=5000000000,  # 50 Bitcoins (5,000,000,000 sats)
        script_pubkey=bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")  # Recipient's public key (bytes)
    )

    # Create a transaction
    coinbase = Transaction(vin=[tx_in], vout=[tx_out])
    return coinbase


def main():
    public_key = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    coinbase = create_coinbase(public_key)

    # Serialize and hash the transaction
    raw_transaction = coinbase.serialize()
    tx_hash = coinbase.hash()
    print(f"Coinbase Hash: {tx_hash.hex()}")

    zero64 = bytes.fromhex("0" * 64)

    block = Block(prev_block=zero64, bits=16)
    block.add(coinbase)

    block._merkle_root()
    block.mine()

    print("Previous Hash:", block.prev_block.hex())
    print("Merkle Root:", block.merkle_root.hex())
    print(f"Block Timestamp: {datetime.fromtimestamp(block.time)} ({block.time} seconds since January 1st, 1970)")
    print("Nonce:", block.nonce)
    print("Block Data:", block.serialize().hex())
    print("Block Hash:", block.hash().hex())

if __name__ == '__main__':
    main()
