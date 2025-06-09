from datetime import datetime

from block import CBlock
from block import CBlockHeader
from crypto import hash160
from script import CScript
from script_utils import ScriptBuilder
from transaction import COutPoint
from transaction import CTransaction
from transaction import CTxIn
from transaction import CTxOut
from utxo import UTXO
from utxo import UTXOSet


class Miner:
    BLOCK_HEIGHT = 0
    BLOCK_REWARD = 5_000_000_000  # 50 Bitcoins (5,000,000,000 sats)
    DIFFICULTY_BITS = 0x1f00ffff

    def __init__(self, miner_pubkey):
        self.blockchain = []
        self.mempool = {}
        self.utxo_set = UTXOSet()

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
            vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=script_pubkey)],
            vout=[CTxOut(nValue=miner_reward, scriptPubKey=script_pubkey)]
        )
        return tx

    def create_candidate_block(self, prev_block, transactions, bits, coinbase_data, miner_reward, script_pubkey, time=None):
        """
        Creates a new candidate block with a coinbase transaction.

        Args:
            prev_block (bytes): The hash of the previous block.
            transactions (list[CTransaction]): A list of transactions to include in the block.
            bits (int): The difficulty target for block hash.
            coinbase_data (CSript, optional): Extra data for the coinbase transaction. Defaults to an empty byte string.
            miner_reward (int): The miner reward in satoshis.
            script_pubkey (CSript): The script public key of the miner.
            time (int, optional): The Unix epoch time for the block. Defaults to current time.

        Returns:
            CBlock: A new block instance.
        """
        if time is None:
            time = int(datetime.now().timestamp())

        # Create the coinbase transaction
        coinbase_tx = self.create_coinbase_transaction(
            coinbase_data=coinbase_data,
            miner_reward=miner_reward,
            script_pubkey=script_pubkey
        )

        # Add coinbase transaction to the list of transactions
        transactions = [coinbase_tx] + transactions

        block_header = CBlockHeader(
            nVersion=1,
            hashPrevBlock=prev_block,
            hashMerkleRoot=b'',
            nTime=time,
            nBits=bits,
            nNonce=0
        )
        block = CBlock(block_header, transactions)
        block.hashMerkleRoot = block.build_merkle_root()
        return block

    def update_local_state(self, block):
        """Adds the newly mined block to the blockchain."""
        self.blockchain.append(block)
        self.utxo_set.update_from_block(block, Miner.BLOCK_HEIGHT)

    def mine_new_block(self):
        if self.blockchain:
            prev_hash = self.blockchain[-1].get_hash()
        else:
            prev_hash = bytes(32)

        candidate_block = self.create_candidate_block(
            prev_block=prev_hash,
            transactions=list(self.mempool.values()),
            bits=Miner.DIFFICULTY_BITS,
            coinbase_data=b'' + len(self.blockchain).to_bytes(4, 'little'),
            miner_reward=Miner.BLOCK_REWARD,
            script_pubkey=ScriptBuilder.p2pkh_script_pubkey(self.miner_pubkey),
            time=None
        )

        # Calculates the hash of a block header and
        # performs Proof of Work to find a valid block hash.
        candidate_block.mine()
        Miner.BLOCK_HEIGHT += 1

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
