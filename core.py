from transaction import COutPoint
from transaction import CTxIn
from transaction import CTxOut
from transaction import CTransaction
from block import CBlockHeader
from block import CBlock
from utxo import UTXO
from utxo import UTXOSet

from datetime import datetime


class Miner:
    BLOCK_REWARD = 625000000  # 6.25 Bitcoins (625,000,000 sats)
    DIFFICULTY_BITS = 20

    def __init__(self, miner_address):
        self.blockchain = []
        self.utxo_set = UTXOSet()

        self.miner_address = miner_address

    def create_coinbase_transaction(self, coinbase_data, miner_reward, miner_script_pubkey):
        """
        Creates a new coinbase transaction paying the miner.

        Args:
            coinbase_data (bytes, optional): Extra data included in the coinbase transaction. Defaults to an empty byte string.
            miner_reward (int): The amount of the miner reward in satoshis.
            miner_script_pubkey (bytes): The script public key of the miner's address.

        Returns:
            CTransaction: A new coinbase transaction instance.
        """
        coinbase_input = CTxIn(
            prevout=COutPoint(bytes(32), n=0xffffffff),  # Special prevout for coinbase
            scriptSig=coinbase_data
        )
        coinbase_output = CTxOut(nValue=miner_reward, scriptPubKey=miner_script_pubkey)

        return CTransaction(vin=[coinbase_input], vout=[coinbase_output])

    def create_candidate_block(self, prev_block, transactions, bits, coinbase_data, miner_reward, miner_script_pubkey, time=None):
        """
        Creates a new candidate block with a coinbase transaction.

        Args:
            prev_block (bytes): The hash of the previous block.
            transactions (list[CTransaction]): A list of transactions to include in the block.
            bits (int): The difficulty target for block hash.
            coinbase_data (bytes, optional): Extra data for the coinbase transaction. Defaults to an empty byte string.
            miner_reward (int): The miner reward in satoshis.
            miner_script_pubkey (bytes): The script public key of the miner.
            time (int, optional): The Unix epoch time for the block. Defaults to current time.

        Returns:
            CBlock: A new CBlock instance.
        """
        if time is None:
            time = int(datetime.now().timestamp()) 

        # Create the coinbase transaction
        coinbase_tx = self.create_coinbase_transaction(
            coinbase_data=coinbase_data,
            miner_reward=miner_reward,
            miner_script_pubkey=miner_script_pubkey
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

    def create_genesis_block(self, bits, coinbase_data, miner_reward, miner_script_pubkey):
        """
        Creates the genesis block.

        Args:
            bits (int): The difficulty target for the Genesis CBlock.
            coinbase_data (bytes, optional): Extra data for the Genesis CBlock's coinbase transaction. Defaults to an empty byte string.
            miner_reward (int): The miner reward for the Genesis CBlock.
            miner_script_pubkey (bytes): The script public key of the miner for the Genesis CBlock.

        Returns:
            CBlock: The Genesis CBlock instance.
        """
        # Genesis CBlock has no previous block
        prev_block = bytes(32)

        return self.create_candidate_block(
            prev_block=prev_block, 
            transactions=[], 
            bits=bits, 
            coinbase_data=coinbase_data, 
            miner_reward=miner_reward, 
            miner_script_pubkey=miner_script_pubkey,
            time=None
        )

    def update_local_state(self, block):
        """Adds the newly mined block to the blockchain."""
        self.blockchain.append(block)

        for tx in block.vtx:
            for tx_in in tx.vin:
                if not tx.is_coinbase():
                    self.utxo_set.spend(tx_in.prevout)

            for index, tx_out in enumerate(tx.vout):
                outpoint = COutPoint(tx.get_hash(), index)
                new_utxo = UTXO(outpoint, tx_out)
                self.utxo_set.add(new_utxo)

    def mine_new_block(self):
        candidate_block = self.create_candidate_block(
            prev_block=self.blockchain[-1].get_hash(),
            transactions=[],
            bits=Miner.DIFFICULTY_BITS,
            coinbase_data=b'' + len(self.blockchain).to_bytes(4, 'little'),
            miner_reward=Miner.BLOCK_REWARD,
            miner_script_pubkey=self.miner_address,
            time=None
        )

        # Calculates the hash of a block header and
        # performs Proof of Work to find a valid block hash.
        candidate_block.mine()
        print("CBlock mined!", candidate_block.get_hash().hex())

        self.update_local_state(candidate_block)
        print("CBlock added to the blockchain.")

    def run(self):
        """Continuously mines new blocks."""
        if not self.blockchain:
            genesis_block = self.create_genesis_block(
                bits=Miner.DIFFICULTY_BITS,
                coinbase_data=b'', 
                miner_reward=Miner.BLOCK_REWARD, 
                miner_script_pubkey=self.miner_address
            )
            print("Genesis block created.")
            self.blockchain.append(genesis_block)

        while True:
            print("Starting Proof of Work...")
            self.mine_new_block()


def main():
    # Recipient's public key (bytes)
    miner_address = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    miner = Miner(miner_address)
    miner.run()


if __name__ == '__main__':
    main()