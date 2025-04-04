from transaction import COutPoint
from transaction import CTxIn
from transaction import CTxOut
from transaction import CTransaction
import copy


class UTXO:
    def __init__(self, prevout, tx_out):
        self.prevout = prevout
        self.tx_out = tx_out


class UTXOSet:
    def __init__(self):
        self.utxos = {}

    def add(self, utxo):
        self.utxos[utxo.prevout] = utxo.tx_out

    def spend(self, prevout):
        if self.is_unspent(prevout):
            del self.utxos[prevout]
        else:
            raise ValueError(f"UTXO ({prevout.hash.hex()}, {prevout.n}) not found or already spent.")

    def is_unspent(self, prevout):
        return prevout in self.utxos

    def get_balance(self, scriptPubKey=None):
        return sum(tx_out.nValue for tx_out in self.utxos.values() if tx_out.scriptPubKey == scriptPubKey or scriptPubKey == None)

    def __repr__(self):
        return f"UTXOSet({list(self.utxos.values())})"


def create_coinbase_transaction(coinbase_data, miner_reward, miner_script_pubkey):
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
        prevout=COutPoint(hash=bytes(32), n=0xffffffff),  # Special prevout for coinbase
        scriptSig=coinbase_data
    )
    coinbase_output = CTxOut(nValue=miner_reward, scriptPubKey=miner_script_pubkey)

    return CTransaction(vin=[coinbase_input], vout=[coinbase_output])


def main():
    # Recipient's public key (bytes)
    public_key = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    
    # Create a coinbase transaction
    coinbase = create_coinbase_transaction(
        coinbase_data=b'',
        miner_reward=5000000000,
        miner_script_pubkey=public_key
    )

    # Serialize and hash the transaction
    tx_hash = coinbase.get_hash()
    print(f"Transaction Hash: {tx_hash.hex()}")

    utxo_set = UTXOSet()

    tx = coinbase
    for tx_in in tx.vin:
        if not tx.is_coinbase():
            utxo_set.spend(tx_in.prevout)

    for index, tx_out in enumerate(tx.vout):
        outpoint = COutPoint(tx.get_hash(), index)
        new_utxo = UTXO(outpoint, tx_out)
        utxo_set.add(new_utxo)

    print(utxo_set.get_balance(public_key))


if __name__ == '__main__':
    main()
