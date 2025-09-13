from datetime import datetime
from typing import List, Dict

from bignum import set_compact
from bignum import get_compact
from block import mine
from block import CBlock
from block import CBlockHeader
from chainstate import ChainState
from script import CScript
from script_utils import ScriptBuilder
from transaction import COutPoint
from transaction import CTransaction
from transaction import CTxIn
from transaction import CTxOut

max_uint256 = (1 << 256) - 1
PROOF_OF_WORK_LIMIT = max_uint256 >> 20  # Target: 0x1d00ffff


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

    def __init__(self, chain_state: ChainState, miner_pubkey: bytes):
        self.chain_state = chain_state
        self.miner_pubkey = miner_pubkey

        if miner_pubkey:
            self.miner_script = ScriptBuilder.p2pkh_script_pubkey(miner_pubkey)

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

    def calculate_fee(self, transactions: List[CTransaction]) -> int:
        """Calculate total fees from all transactions in the mempool"""
        fee = 0

        for tx in transactions:
            # Skip coinbase transactions (they don't have inputs to spend)
            if tx.is_coinbase():
                continue

            # Calculate input values
            input_sum = 0
            for txin in tx.vin:
                # Find the UTXO being spent
                prevout = txin.prevout
                if prevout in self.chain_state.utxo_set.utxos:
                    utxo = self.chain_state.utxo_set.utxos[prevout]
                    input_sum += utxo.tx_out.nValue

            # Calculate output values
            output_sum = sum(txout.nValue for txout in tx.vout)

            # Fee is input_sum - output_sum
            fee += (input_sum - output_sum)

        return fee

    def create_candidate_block(self, prev_block, transactions, coinbase_data, miner_reward, script_pubkey):
        time = max(prev_block.get_median_time_past() if prev_block else 0, int(datetime.now().timestamp()))

        # Calculate dynamic difficulty
        bits = get_next_work_required(prev_block)

        # Calculate total fees from all transactions
        total_fee = self.calculate_fee(transactions)

        # Create coinbase transaction with block reward + fees
        coinbase_tx = self.create_coinbase_transaction(
            coinbase_data=coinbase_data,
            miner_reward=miner_reward + total_fee,  # Add fees to reward
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

    def mine_new_block(self):
        # Get previous block hash from chain tip
        if self.chain_state.chain.tip:
            prev_block = self.chain_state.chain.tip
        else:
            prev_block = None  # Genesis block

        coinbase_data = (self.chain_state.chain.tip.height + 1 if self.chain_state.chain.tip else 0).to_bytes(4, 'little')
        script_bytes = ScriptBuilder._push_data(coinbase_data)

        candidate_block = self.create_candidate_block(
            prev_block=prev_block,
            transactions=list(self.chain_state.mempool.values()),
            coinbase_data=CScript(script_bytes),
            miner_reward=Miner.BLOCK_REWARD,
            script_pubkey=self.miner_script,
        )

        # Mine and add to chain
        mine(candidate_block)
        return candidate_block

    def run(self):
        """Continuously mines new blocks."""
        while True:
            block = self.mine_new_block()
            self.chain_state.update(block)


def main():
    import time
    from random import random

    # Recipient's public key (bytes)
    miner1_pubkey = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    miner2_pubkey = bytes.fromhex("026e21e332324f8634ef47584ef130dd97828e2f626a5f2d7d7a1a33e32a26ac20")

    miner1_script = ScriptBuilder.p2pkh_script_pubkey(miner1_pubkey)
    miner2_script = ScriptBuilder.p2pkh_script_pubkey(miner2_pubkey)

    shared_state = ChainState()

    miner1 = Miner(shared_state, miner1_pubkey)
    miner2 = Miner(shared_state, miner2_pubkey)

    while True:
        miner = (miner1 if random() >= 0.5 else miner2)

        block = miner.mine_new_block()
        shared_state.update(block)
        shared_state.chain.print_tree()

        balance = shared_state.utxo_set.get_balance() / (10 ** 8)
        miner1_balance = shared_state.utxo_set.get_balance(miner1_script) / (10 ** 8)
        miner2_balance = shared_state.utxo_set.get_balance(miner2_script) / (10 ** 8)
        print(f"Chain Balance: {balance}    Miner A: {miner1_balance}   Miner B: {miner2_balance}")

        epoch_time = shared_state.chain.tip.header.nTime
        dt = datetime.fromtimestamp(epoch_time)
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Median Time: {formatted_time}")

        time.sleep(3)


if __name__ == '__main__':
    main()
