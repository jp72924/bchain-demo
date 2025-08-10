import io
import time
from typing import List

from bignum import set_compact
from crypto import hash256
from serialize import compact_size
from serialize import read_compact_size
from script import CScript
from script_utils import ScriptBuilder
from transaction import COutPoint
from transaction import CTxIn
from transaction import CTxOut
from transaction import CTransaction


def mine(block: 'CBlock', max_attempts=10) -> bool:
        """
        Proof-of-Work mining implementation mirroring Satoshi's original logic
        from Bitcoin Core 0.1.0. Follows the same nonce iteration and timestamp
        update behavior.

        Args:
            max_attempts: Maximum timestamp updates before failing

        Returns:
            True if block mined, False if failed
        """
        # Calculate target from nBits
        target = set_compact(block.nBits)
        if target == 0:
            raise ValueError("Invalid target (nBits too low)")

        # Ensure merkle root is current
        block.hashMerkleRoot = block.build_merkle_root()

        start_time = time.time()
        last_print = start_time
        hashes_processed = 0
        attempts = 0

        print(f"Mining started (Target: {target:064x})")

        while attempts < max_attempts:
            # Iterate through full 32-bit nonce space (0 to 2^32-1)
            for nonce in range(0, 0x100000000):
                block.nNonce = nonce
                block_hash = block.get_hash()
                hashes_processed += 1

                # Convert hash to integer (big-endian)
                hash_int = int.from_bytes(block_hash, 'big')

                # Check if block hash meets target
                if hash_int <= target:
                    elapsed = time.time() - start_time
                    hashrate = hashes_processed / max(elapsed, 0.001)
                    print(f"\nBlock mined! Nonce: {nonce}")
                    print(f"Hash (LE): {block_hash[::-1].hex()}")  # Standard display format
                    print(f"Elapsed: {elapsed:.2f}s | Hashrate: {hashrate:.2f} H/s")
                    return True

                # Periodic status update every 5 seconds
                current_time = time.time()
                if current_time - last_print >= 5:
                    elapsed = current_time - start_time
                    hashrate = hashes_processed / max(elapsed, 0.001)
                    print(f"Hashrate: {hashrate:.2f} H/s | Nonce: {nonce}/4294967295 | "
                          f"Time: {int(elapsed)}s", end='\r')
                    last_print = current_time

            # Nonce space exhausted - update timestamp
            attempts += 1
            block.nTime += 1  # Minimal timestamp increment
            print(f"\nNonce range exhausted. Updated time to {block.nTime} (Attempt {attempts}/{max_attempts})")

        print("Mining failed: Maximum attempts reached")
        return False


class CBlockHeader:
    def __init__(self, nVersion: int, hashPrevBlock: bytes, hashMerkleRoot: bytes,
                 nTime: int, nBits: int, nNonce: int):
        self.nVersion = nVersion
        self.hashPrevBlock = hashPrevBlock
        self.hashMerkleRoot = hashMerkleRoot
        self.nTime = nTime
        self.nBits = nBits
        self.nNonce = nNonce

    def serialize(self):
        """Serializes the block header into a byte string"""
        stream = io.BytesIO()
        # Version (little-endian)
        stream.write(self.nVersion.to_bytes(4, 'little'))

        # Hashes in internal byte order (no reversal)
        stream.write(self.hashPrevBlock)
        stream.write(self.hashMerkleRoot)

        # Time, Bits, Nonce (little-endian)
        stream.write(self.nTime.to_bytes(4, 'little'))
        stream.write(self.nBits.to_bytes(4, 'little'))
        stream.write(self.nNonce.to_bytes(4, 'little'))
        return stream.getvalue()

    @classmethod
    def deserialize(cls, stream) -> 'CBlockHeader':
        """Deserialize a block header from a byte stream."""
        version = int.from_bytes(stream.read(4), 'little')
        hash_prev_block = stream.read(32)
        if len(hash_prev_block) != 32:
            raise ValueError("Invalid hashPrevBlock length (must be 32 bytes)")
        hash_merkle_root = stream.read(32)
        if len(hash_merkle_root) != 32:
            raise ValueError("Invalid hashMerkleRoot length (must be 32 bytes)")
        n_time = int.from_bytes(stream.read(4), 'little')
        n_bits = int.from_bytes(stream.read(4), 'little')
        n_nonce = int.from_bytes(stream.read(4), 'little')
        return cls(version, hash_prev_block, hash_merkle_root, n_time, n_bits, n_nonce)


class CBlock(CBlockHeader):
    def __init__(self, header: CBlockHeader, vtx: list[CTransaction]):
        super().__init__(header.nVersion, header.hashPrevBlock, header.hashMerkleRoot,
                         header.nTime, header.nBits, header.nNonce)
        self.vtx = vtx
        self.vMerkleTree = []

    def _compute_merkle_root(self, hashes: List[bytes]) -> bytes:
        """Compute merkle root from transaction hashes."""
        if not hashes:
            return bytes(32)

        while len(hashes) > 1:
            if len(hashes) % 2:
                hashes.append(hashes[-1])
            hashes = [hash256(hashes[i] + hashes[i+1])
                     for i in range(0, len(hashes), 2)]
        return hashes[0]

    def build_merkle_root(self) -> bytes:
        """Calculate the merkle root for the block's transactions."""
        hashes = [tx.get_hash() for tx in self.vtx]
        return self._compute_merkle_root(hashes)

    def serialize(self):
        """Serializes the full block (header + transactions)"""
        stream = io.BytesIO()
        # Serialize header
        stream.write(super().serialize())  # Use CBlockHeader's logic
        # Serialize transactions
        stream.write(compact_size(len(self.vtx)))
        for tx in self.vtx:
            stream.write(tx.serialize())
        return stream.getvalue()

    @classmethod
    def deserialize(cls, data: bytes) -> 'CBlock':
        """Deserialize a full block from bytes (header + transactions)"""
        stream = io.BytesIO(data)
        # Deserialize header
        header = CBlockHeader.deserialize(stream)
        # Deserialize transactions
        tx_count = read_compact_size(stream)
        vtx = [CTransaction.deserialize(stream) for _ in range(tx_count)]
        # Validate no extra data remains
        if stream.read():
            raise ValueError("Extra data after transactions in block")
        return cls(header, vtx)

    def get_hash(self) -> bytes:
        header_data = super().serialize()  # Only serialize header (80 bytes)
        return hash256(header_data)


def create_coinbase_transaction(coinbase_data: CScript, miner_reward: int, script_pubkey: CScript):
    """
    Creates a new coinbase transaction paying the miner.

    Args:
        coinbase_data (CScript, optional): Extra data included in the coinbase transaction. Defaults to an empty byte string.
        miner_reward (int): The amount of the miner reward in satoshis.
        script_pubkey (CScript): The script public key of the miner's address.

    Returns:
        CTransaction: A new coinbase transaction instance.
    """
    # Create transaction
    tx = CTransaction(
        vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=coinbase_data)],
        vout=[CTxOut(nValue=miner_reward, scriptPubKey=script_pubkey)]
    )
    return tx


def main():
    pubkey_bytes = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    p2pkh_script = ScriptBuilder.p2pkh_script_pubkey(pubkey_bytes)

    # Create a coinbase transaction
    coinbase = create_coinbase_transaction(
        coinbase_data=CScript(b""),
        miner_reward=5000000000,
        script_pubkey=p2pkh_script
    )

    # Create a block
    block_header = CBlockHeader(
        nVersion=1,
        hashPrevBlock=bytes(32),
        hashMerkleRoot=bytes(32),
        nTime=int(time.time()),
        nBits=0x1d00ffff,  # Simplified difficulty for demonstration
        nNonce=0,

    )
    block = CBlock(header=block_header, vtx=[coinbase])
    block.hashMerkleRoot = block.build_merkle_root()  # Calculate Merkle root

    # Mine the block
    mine(block)


if __name__ == '__main__':
    main()
