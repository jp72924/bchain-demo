from datetime import datetime
from typing import Dict

from bignum import set_compact
from bignum import get_compact
from block import mine
from block import CBlock
from block import CBlockHeader
from block_index import Chain
from script import CScript
from script_utils import ScriptBuilder
from transaction import COutPoint
from transaction import CTransaction
from transaction import CTxIn
from transaction import CTxOut
from utxo import UTXO
from utxo import UTXOSet

max_uint256 = (1 << 256) - 1
PROOF_OF_WORK_LIMIT = max_uint256 >> 32  # Target: 0x1f00ffff


def get_next_work_required(tip: CBlock) -> int:
    TARGET_TIMESPAN = 14 * 24 * 60 * 60  # 14 days in seconds
    TARGET_SPACING = 10 * 60
    INTERVAL = TARGET_TIMESPAN // TARGET_SPACING # Blocks between adjustments

    """Calculate new nBits for next block"""
    if not tip:
        return get_compact(PROOF_OF_WORK_LIMIT)

    height = tip.height

    # Only adjust every 2016 blocks
    if height % INTERVAL != 0:
        return tip.header.nBits

    # Get reference blocks using chain structure
    first_block = tip
    for _ in range(INTERVAL):
        first_block = first_block.pprev
        if not first_block:
            return get_compact(PROOF_OF_WORK_LIMIT)

    last_block = tip
    actual_timespan = last_block.header.nTime - first_block.header.nTime

    # Clamp timespan to 0.25x-4x of target
    min_timespan = TARGET_TIMESPAN // 4
    max_timespan = TARGET_TIMESPAN * 4
    actual_timespan = min(max(actual_timespan, min_timespan), max_timespan)

    # Calculate new target
    old_target = set_compact(last_block.header.nBits)
    new_target = old_target * actual_timespan // TARGET_TIMESPAN

    # Apply genesis target as upper limit
    new_target = min(new_target, PROOF_OF_WORK_LIMIT)

    return get_compact(new_target)


class Miner:
    BLOCK_REWARD = 5_000_000_000  # 50 BTC in satoshis

    def __init__(self, miner_pubkey):
        self.chain = Chain()  # New chain index system
        self.utxo_set = UTXOSet()
        self.mempool: Dict[bytes, CTransaction] = {}
        self.miner_pubkey = miner_pubkey

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
            vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=coinbase_data)],
            vout=[CTxOut(nValue=miner_reward, scriptPubKey=script_pubkey)]
        )
        return tx

    def create_candidate_block(self, prev_block, transactions, coinbase_data, miner_reward, script_pubkey):
        time = max(prev_block.get_median_time_past() if prev_block else 0, int(datetime.now().timestamp()))

        # Calculate dynamic difficulty
        bits = get_next_work_required(prev_block)

        # Create coinbase transaction
        coinbase_tx = self.create_coinbase_transaction(
            coinbase_data=coinbase_data,
            miner_reward=miner_reward,
            script_pubkey=script_pubkey
        )

        transactions = [coinbase_tx] + transactions

        prev_hash = prev_block.hash if prev_block else bytes(32)
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
            blocks_to_connect.append(current)
            current = current.pprev
        blocks_to_connect.reverse()  # Apply in order
        
        for block in blocks_to_connect:
            self.utxo_set.update_from_block(block.header, block.height)

    def mine_new_block(self):
        # Get previous block hash from chain tip
        if self.chain.tip:
            prev_block = self.chain.tip
        else:
            prev_block = None  # Genesis block

        coinbase_data = (self.chain.tip.height + 1 if self.chain.tip else 0).to_bytes(4, 'little')
        script_bytes = ScriptBuilder._push_data(coinbase_data)

        candidate_block = self.create_candidate_block(
            prev_block=prev_block,
            transactions=list(self.mempool.values()),
            coinbase_data=CScript(script_bytes),
            miner_reward=Miner.BLOCK_REWARD,
            script_pubkey=ScriptBuilder.p2pkh_script_pubkey(self.miner_pubkey),
        )

        # Mine and add to chain
        mine(candidate_block)
        return candidate_block

    def run(self):
        """Continuously mines new blocks."""
        while True:
            block = self.mine_new_block()
            self.update_local_state(block)


def main():
    import time
    from random import random

    # Recipient's public key (bytes)
    miner1_pubkey = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    miner2_pubkey = bytes.fromhex("026e21e332324f8634ef47584ef130dd97828e2f626a5f2d7d7a1a33e32a26ac20")

    miner1_script = ScriptBuilder.p2pkh_script_pubkey(miner1_pubkey)
    miner2_script = ScriptBuilder.p2pkh_script_pubkey(miner2_pubkey)

    miner1 = Miner(miner1_pubkey)
    miner2 = Miner(miner2_pubkey)

    while True:
        r1 = random()
        r2 = random()

        miner = (miner1 if r1 <= 0.375 else miner2)

        block = miner.mine_new_block()
        miner1.update_local_state(block)
        miner2.update_local_state(block)

        if r2 <= 0.165:
            miner2.chain.tip = miner2.chain.tip.pprev
            input("Fork found! Press any key to continue")

        miner.chain.print_tree()

        balance = miner1.utxo_set.get_balance() / (10 ** 8)
        miner1_balance = miner1.utxo_set.get_balance(miner1_script) / (10 ** 8)
        miner2_balance = miner1.utxo_set.get_balance(miner2_script) / (10 ** 8)
        print(f"Chain Balance: {balance}    Miner A: {miner1_balance}   Miner B: {miner2_balance}")

        epoch_time = miner1.chain.tip.header.nTime
        dt = datetime.fromtimestamp(epoch_time)
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Median Time: {formatted_time}")

        time.sleep(3)


if __name__ == '__main__':
    main()
