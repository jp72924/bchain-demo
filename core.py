from transaction import Outpoint
from transaction import TxIn
from transaction import TxOut
from transaction import Transaction
from block import Block
from utxo import UTXO
from utxo import UTXOSet

from datetime import datetime


class Minner:
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
            Transaction: A new coinbase transaction instance.
        """
        coinbase_input = TxIn(
            prevout=Outpoint(hash=b'\x00' * 32, index=0xffffffff),  # Special prevout for coinbase
            script_sig=coinbase_data
        )
        coinbase_output = TxOut(value=miner_reward, script_pubkey=miner_script_pubkey)

        return Transaction(vin=[coinbase_input], vout=[coinbase_output])


    def create_candidate_block(self, prev_block, transactions, bits, coinbase_data, miner_reward, miner_script_pubkey, time=None):
        """
        Creates a new candidate block with a coinbase transaction.

        Args:
            prev_block (bytes): The hash of the previous block.
            transactions (list[Transaction]): A list of transactions to include in the block.
            bits (int): The difficulty target for block hash.
            coinbase_data (bytes, optional): Extra data for the coinbase transaction. Defaults to an empty byte string.
            miner_reward (int): The miner reward in satoshis.
            miner_script_pubkey (bytes): The script public key of the miner.
            time (int, optional): The Unix epoch time for the block. Defaults to current time.

        Returns:
            Block: A new Block instance.
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

        block = Block(
            version=1, 
            prev_block=prev_block, 
            merkle_root=b'', 
            time=time, 
            bits=bits, 
            nonce=0 
        )

        for tx in transactions:
            block.add_transaction(tx)

        block.merkle_root = block._merkle_root() 
        return block


    def create_genesis_block(self, bits, coinbase_data, miner_reward, miner_script_pubkey):
        """
        Creates the genesis block.

        Args:
            bits (int): The difficulty target for the Genesis Block.
            coinbase_data (bytes, optional): Extra data for the Genesis Block's coinbase transaction. Defaults to an empty byte string.
            miner_reward (int): The miner reward for the Genesis Block.
            miner_script_pubkey (bytes): The script public key of the miner for the Genesis Block.

        Returns:
            Block: The Genesis Block instance.
        """
        # Genesis Block has no previous block
        prev_block = b'\x00' * 32 

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
                outpoint = Outpoint(tx.hash(), index)
                new_utxo = UTXO(outpoint, tx_out)
                self.utxo_set.add(new_utxo)

    def mine_new_block(self):
        candidate_block = self.create_candidate_block(
            prev_block=b'',
            transactions=[],
            bits=Minner.DIFFICULTY_BITS,
            coinbase_data=b'' + len(self.blockchain).to_bytes(4, 'little') ,
            miner_reward=Minner.BLOCK_REWARD,
            miner_script_pubkey=self.miner_address,
            time=None
        )

        # Calculates the hash of a block header and
        # performs Proof of Work to find a valid block hash.
        candidate_block.mine()
        print("Block mined!", candidate_block.hash().hex())

        self.update_local_state(candidate_block)
        print("Block added to the blockchain.")

    def run(self):
        """Continuously mines new blocks."""
        if not self.blockchain:
            self.create_genesis_block(
                bits=Minner.DIFFICULTY_BITS,
                coinbase_data=b'', 
                miner_reward=Minner.BLOCK_REWARD, 
                miner_script_pubkey=self.miner_address
            )
            print("Genesis block created.")

        while True:
            print("Starting Proof of Work...")
            self.mine_new_block()


def main():
    # Recipient's public key (bytes)
    miner_address = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    minner = Minner(miner_address)
    minner.run()


if __name__ == '__main__':
    main()