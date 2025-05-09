import io
import script
from datetime import datetime

from crypto import hash160
from crypto import hash256

from transaction import COutPoint
from transaction import CTxIn
from transaction import CTxOut
from transaction import CTransaction

from script import CScript
from script import OP_DUP
from script import OP_HASH160
from script import OP_PUSHBYTES_20
from script import OP_EQUALVERIFY
from script import OP_CHECKSIG


class CBlockHeader:
    def __init__(self, nVersion: int, hashPrevBlock: bytes, hashMerkleRoot: bytes,
                 nTime: int, nBits: int, nNonce: int):
        self.nVersion = nVersion
        self.hashPrevBlock = hashPrevBlock
        self.hashMerkleRoot = hashMerkleRoot
        self.nTime = nTime
        self.nBits = nBits
        self.nNonce = nNonce


class CBlock(CBlockHeader):
    def __init__(self, header: CBlockHeader, vtx: list[CTransaction]):
        super().__init__(header.nVersion, header.hashPrevBlock, header.hashMerkleRoot,
                         header.nTime, header.nBits, header.nNonce)
        self.vtx = vtx
        self.vMerkleTree = []

    def build_merkle_root(self) -> bytes:
        self.vMerkleTree.clear()
        for tx in self.vtx:
            self.vMerkleTree.append(tx.get_hash())

        if not self.vMerkleTree:
            return bytes(32)
        
        hashes = [h for h in self.vMerkleTree]  # Bitcoin's internal byte order
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            hashes = [hash256(h1 + h2)
                    for i in range(0, len(hashes), 2)
                    for h1, h2 in (hashes[i], hashes[i+1])]
        return hashes[0]

    def serialize_header(self):
        """Serializes the block header into a byte string"""
        stream = io.BytesIO()
        # Use original byte order without reversal
        stream.write(self.nVersion.to_bytes(4, 'little'))
        stream.write(self.hashPrevBlock)  # Already in correct byte order
        stream.write(self.hashMerkleRoot)
        stream.write(self.nTime.to_bytes(4, 'little'))
        stream.write(self.nBits.to_bytes(4, 'little'))
        stream.write(self.nNonce.to_bytes(4, 'little'))
        return stream.getvalue()

    def get_hash(self):
        """Calculate the block's hash"""
        header_data = self.serialize_header()
        _hash = hash256(header_data)
        return _hash

    def mine(self):
        """Mine the block by finding a valid nonce."""
        self.nTime = int(datetime.now().timestamp())
        target = (1 << (256 - self.nBits)) - 1  # Calculate target from nBits

        while int(self.get_hash().hex(), 16) > target:
            self.nNonce += 1

def create_coinbase_transaction(coinbase_data, miner_reward, miner_pubkey):
    """
    Creates a new coinbase transaction paying the miner.

    Args:
        coinbase_data (bytes, optional): Extra data included in the coinbase transaction. Defaults to an empty byte string.
        miner_reward (int): The amount of the miner reward in satoshis.
        miner_pubkey_bytes (bytes): The script public key of the miner's address.

    Returns:
        CTransaction: A new coinbase transaction instance.
    """
    # Generate pubkey hash
    pubkey_hash = hash160(miner_pubkey)

    # Build P2PKH scriptPubKey
    script_pubkey = CScript(
        bytes([OP_DUP, OP_HASH160, OP_PUSHBYTES_20]) +  # 0x14 pushes 20 bytes
        pubkey_hash +
        bytes([OP_EQUALVERIFY, OP_CHECKSIG])
    )

    # Create transaction
    tx = CTransaction(
        vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=CScript(b""))],
        vout=[CTxOut(nValue=miner_reward, scriptPubKey=script_pubkey)]
    )
    return tx


def main():
    pubkey = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    
    # Create a coinbase transaction
    coinbase = create_coinbase_transaction(
        coinbase_data=b'',
        miner_reward=5000000000,
        miner_pubkey=pubkey
    )

    # Serialize and hash the transaction
    raw_transaction = coinbase.serialize()
    tx_hash = coinbase.get_hash()
    print(f"Coinbase Hash: {tx_hash.hex()[::-1]}")

    # Create a block
    block_header = CBlockHeader(
        nVersion=1,
        hashPrevBlock=bytes(32),
        hashMerkleRoot="",
        nTime=int(datetime.now().timestamp()),
        nBits=16,  # Simplified difficulty for demonstration
        nNonce=0,

    )
    block = CBlock(header=block_header, vtx=[coinbase])
    block.hashMerkleRoot = block.build_merkle_root()  # Calculate Merkle root

    # Mine the block
    block.mine()

    print("Previous Block:", block.hashPrevBlock.hex()[::-1])
    print("Merkle Root:", block.hashMerkleRoot.hex()[::-1])
    print(f"Block Timestamp: {datetime.fromtimestamp(block.nTime)} ({block.nTime} seconds since January 1st, 1970)")
    print("Nonce:", block.nNonce)
    print("Block Header:", block.serialize_header().hex())
    print("Block Hash:", block.get_hash().hex()[::-1])

if __name__ == '__main__':
    main()
