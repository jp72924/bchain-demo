import copy
from typing import Dict, Optional

from block import CBlock
from crypto import hash160
from transaction import COutPoint
from transaction import CTxIn
from transaction import CTxOut
from transaction import CTransaction
from script import CScript
from script import is_op_return
from script_utils import ScriptBuilder


class UTXO:
    def __init__(self, prevout: 'COutPoint', tx_out: 'CTxOut', height: int, coinbase: bool):
        self.height = height        # The height of the block containing the UTXO
        self.coinbase = coinbase    # Whether the UTXO comes from a coinbase transaction or not.
        self.tx_out = tx_out        # The value of the output in satoshis
                                    # and locking code that was placed on the output.
        self.prevout = prevout


class UTXOSet:
    def __init__(self):
        self.utxos: Dict['COutPoint', 'UTXO'] = {}
        self.spent_utxos: Dict['COutPoint', 'UTXO'] = {}  # Added spent UTXO cache

    def update_from_block(self, block: 'CBlock', height: int):
        """Process all transactions in a block (spend inputs and add outputs)"""
        # First: Process inputs (spend UTXOs)
        for tx in block.vtx:
            if not tx.is_coinbase():
                for tx_in in tx.vin:
                    self.spend(tx_in.prevout)

        # Then: Add outputs as new UTXOs
        for tx in block.vtx:
            is_coinbase = tx.is_coinbase()
            tx_hash = tx.get_hash()
            for i, tx_out in enumerate(tx.vout):
                # Skip OP_RETURN outputs as they are unspendable
                if is_op_return(tx_out.scriptPubKey):
                    continue

                prevout = COutPoint(tx_hash, i)
                self.utxos[prevout] = UTXO(
                    prevout=prevout,
                    tx_out=tx_out,
                    height=height,
                    coinbase=is_coinbase
                )

    def disconnect_block(self, block: 'CBlock'):
        """Undo block effects on UTXO set"""
        # 1. Remove created outputs
        for tx in block.vtx:
            tx_hash = tx.get_hash()
            for i in range(len(tx.vout)):
                prevout = COutPoint(tx_hash, i)
                del self.utxos[prevout]
  
        # 2. Restore spent inputs
        for tx in block.vtx[1:]:  # Skip coinbase
            for txin in tx.vin:
                self.utxos[txin.prevout] = self.spent_utxos[txin.prevout]

    def add(self, utxo: 'UTXO'):
        if not isinstance(utxo, UTXO):
            raise TypeError("Cannot add non-UTXO objects")
        self.utxos[utxo.prevout] = utxo

    def spend(self, prevout: 'COutPoint'):
        if prevout not in self.utxos:
            raise ValueError(f"UTXO not found: {prevout}")
        # Cache spent UTXO for potential restoration
        self.spent_utxos[prevout] = self.utxos[prevout]
        del self.utxos[prevout]

    def is_unspent(self, prevout: 'COutPoint'):
        return prevout in self.utxos

    def get_balance(self, script_pubkey: Optional['CScript'] = None) -> int:
        """Calculate balance filtered by scriptPubKey (if provided)"""
        total = 0
        for utxo in self.utxos.values():
            if script_pubkey is None or utxo.tx_out.scriptPubKey == script_pubkey:
                total += utxo.tx_out.nValue
        return total

    def __repr__(self):
        return f"UTXOSet({list(self.utxos.values())})"


def create_coinbase_transaction(coinbase_data: 'CScript', miner_reward: int, script_pubkey: 'CScript'):
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
    # Recipient's public key (bytes)
    pubkey_bytes = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")

    # Build P2PKH script
    p2pkh_script = ScriptBuilder.p2pkh_script_pubkey(pubkey_bytes)

    # Create a coinbase transaction
    coinbase = create_coinbase_transaction(
        coinbase_data=CScript(b""),
        miner_reward=5_000_000_000,
        script_pubkey=p2pkh_script
    )

    utxo_set = UTXOSet()
    height = 1

    tx = coinbase
    if not tx.is_coinbase():
        for tx_in in tx.vin:
            utxo_set.spend(tx_in.prevout)

    for index, tx_out in enumerate(tx.vout):
        outpoint = COutPoint(tx.get_hash(), index)
        new_utxo = UTXO(outpoint, tx_out, height, tx.is_coinbase())
        utxo_set.add(new_utxo)

    wallet_balance = utxo_set.get_balance(p2pkh_script)
    print(f"Wallet Balance: {wallet_balance / (10 ** 8)} BTC")


if __name__ == '__main__':
    main()
