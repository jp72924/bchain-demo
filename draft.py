from transaction import Outpoint
from transaction import TxIn
from transaction import TxOut
from transaction import Transaction
from block import Block


def create_coinbase_transaction(coinbase_data, miner_reward, miner_script_pubkey):
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


def create_candidate_block(prev_block, transactions, bits, coinbase_data, miner_reward, miner_script_pubkey, time):
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
    coinbase_tx = create_coinbase_transaction(
        block_height=0,  # Placeholder for block height (will be set later)
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


def create_genesis_block(bits, coinbase_data, miner_reward, miner_script_pubkey):
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

    return create_candidate_block(
        prev_block=prev_block, 
        transactions=[], 
        bits=bits, 
        coinbase_data=coinbase_data, 
        miner_reward=miner_reward, 
        miner_script_pubkey=miner_script_pubkey,
        time=None
    )


def mine_new_block(self):
    candidate_block = self.create_candidate_block()
    candidate_block.mine()

    self.update_local_state(candidate_block)


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



def run(self):
    """Continuously mines new blocks."""
    if not self.blockchain:
        self.create_genesis_block()
    while True:
        self.mine_new_block()