from datetime import datetime

from block import CBlock
from block import CBlockHeader
from block_index import CBlockIndex
from block_index import Chain
from crypto import hash160
from script import CScript
from script_utils import ScriptBuilder
from transaction import COutPoint
from transaction import CTransaction
from transaction import CTxIn
from transaction import CTxOut
from utxo import UTXO
from utxo import UTXOSet


def to_compact(target: int) -> int:
    """Convert 256-bit target integer to compact nBits representation"""
    # Get minimal big-endian representation
    data = target.to_bytes(32, 'big').lstrip(b'\x00')
    if not data:
        return 0
        
    n = len(data)
    
    # Take first 3 bytes for coefficient
    if n > 3:
        coefficient = int.from_bytes(data[:3], 'big')
    else:
        # Pad with zeros to 3 bytes
        coefficient = int.from_bytes(data, 'big') << (8 * (3 - n))
    
    return (n << 24) | coefficient


def from_compact(nBits: int) -> int:
    """Convert compact nBits to 256-bit target integer"""
    exponent = nBits >> 24
    coefficient = nBits & 0x007fffff
    
    if exponent <= 3:
        return coefficient >> (8 * (3 - exponent))
    else:
        return coefficient << (8 * (exponent - 3))


class Miner:
    BLOCK_REWARD = 5_000_000_000  # 50 BTC in satoshis
    TARGET_TIMESPAN = 14 * 24 * 60 * 60  # 14 days in seconds
    ADJUSTMENT_INTERVAL = 2016  # Blocks between adjustments

    def __init__(self, miner_pubkey):
        # self.blockchain = []
        self.chain = Chain()  # New chain index system
        self.mempool = {}
        self.utxo_set = UTXOSet()
        self.miner_pubkey = miner_pubkey
        
        # Genesis block difficulty
        self.genesis_bits = 0x1d00ffff
        self.genesis_target = from_compact(self.genesis_bits)

    def get_next_bits(self) -> int:
        """Calculate new nBits for next block"""
        if not self.chain.tip:
            return self.genesis_bits
            
        height = self.chain.tip.height
        
        # Only adjust every 2016 blocks
        if height % self.ADJUSTMENT_INTERVAL != 0:
            return self.chain.tip.header.nBits

        # Get reference blocks using chain structure
        first_block = self.chain.tip
        for _ in range(self.ADJUSTMENT_INTERVAL):
            first_block = first_block.pprev
            if not first_block:
                return self.genesis_bits

        last_block = self.chain.tip
        actual_timespan = last_block.header.nTime - first_block.header.nTime

        # Clamp timespan to 0.25x-4x of target
        min_timespan = self.TARGET_TIMESPAN // 4
        max_timespan = self.TARGET_TIMESPAN * 4
        actual_timespan = min(max(actual_timespan, min_timespan), max_timespan)

        # Calculate new target
        old_target = from_compact(last_block.header.nBits)
        new_target = old_target * actual_timespan // self.TARGET_TIMESPAN
        
        # Apply genesis target as upper limit
        new_target = min(new_target, self.genesis_target)
        
        return to_compact(new_target)

    def create_coinbase_transaction(self, coinbase_data, miner_reward, script_pubkey):
        """
        Creates a new coinbase transaction paying the miner.

        Args:
            coinbase_data (CSript, optional): Extra data included in the coinbase transaction. Defaults to an empty byte string.
            miner_reward (int): The amount of the miner reward in satoshis.
            script_pubkey (CSript): The script public key of the miner's address.

        Returns:
            CTransaction: A new coinbase transaction instance.
        """
        # Create transaction
        tx = CTransaction(
            vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=script_pubkey)],
            vout=[CTxOut(nValue=miner_reward, scriptPubKey=script_pubkey)]
        )
        return tx

    def create_candidate_block(self, prev_hash, transactions, coinbase_data, miner_reward, script_pubkey, time=None):
        if time is None:
            time = int(datetime.now().timestamp())

        # Calculate dynamic difficulty
        bits = self.get_next_bits()

        # Create coinbase transaction
        coinbase_tx = self.create_coinbase_transaction(
            coinbase_data=coinbase_data,
            miner_reward=miner_reward,
            script_pubkey=script_pubkey
        )

        transactions = [coinbase_tx] + transactions

        block_header = CBlockHeader(
            nVersion=1,
            hashPrevBlock=prev_hash,
            hashMerkleRoot=b'',
            nTime=time,
            nBits=bits,
            nNonce=0
        )
        block = CBlock(block_header, transactions)
        block.hashMerkleRoot = block.build_merkle_root()
        return block

    def update_local_state(self, block):
        """Adds the newly mined block to the blockchain index"""
        try:
            new_index = self.chain.add_block(block)
            
            # Update UTXO set based on new chain state
            if self.chain.tip == new_index:
                # Simple extension case
                self.utxo_set.update_from_block(block, new_index.height)
            else:
                # Handle chain reorganization
                self.handle_chain_reorg(new_index)
                
            # Clear mined transactions from mempool
            for tx in block.vtx[1:]:  # Skip coinbase
                txid = tx.get_hash()
                if txid in self.mempool:
                    del self.mempool[txid]
                    
        except ValueError as e:
            print(f"Block addition failed: {e}")

    def handle_chain_reorg(self, new_tip):
        """Update UTXO set during chain reorganization"""
        # 1. Find fork point
        fork_block = self.chain._find_fork_point(self.chain.tip, new_tip)
        
        # 2. Disconnect blocks from old chain
        current = self.chain.tip
        while current != fork_block:
            self.utxo_set.disconnect_block(current.header)
            current = current.pprev
        
        # 3. Connect blocks from new chain
        blocks_to_connect = []
        current = new_tip
        while current != fork_block:
            blocks_to_connect.append(current.header)
            current = current.pprev
        blocks_to_connect.reverse()  # Apply in order
        
        for block in blocks_to_connect:
            self.utxo_set.update_from_block(block, block.height)

    def mine_new_block(self):
        # Get previous block hash from chain tip
        if self.chain.tip:
            prev_hash = self.chain.tip.hash
        else:
            prev_hash = bytes(32)  # Genesis block

        candidate_block = self.create_candidate_block(
            prev_hash=prev_hash,
            transactions=list(self.mempool.values()),
            coinbase_data=b'' + (self.chain.tip.height + 1 if self.chain.tip else 0).to_bytes(4, 'little'),
            miner_reward=Miner.BLOCK_REWARD,
            script_pubkey=ScriptBuilder.p2pkh_script_pubkey(self.miner_pubkey),
            time=None
        )

        # Mine and add to chain
        candidate_block.mine()
        self.update_local_state(candidate_block)

    def run(self):
        """Continuously mines new blocks."""
        while True:
            self.mine_new_block()
            self.on_block_mine()

    def on_block_mine(self):
        ...


def main():
    # Recipient's public key (bytes)
    miner_pubkey = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    miner = Miner(miner_pubkey)
    miner.run()


if __name__ == '__main__':
    main()
