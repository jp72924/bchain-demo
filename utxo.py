import copy

from crypto import hash160

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
from script import OP_PUSHDATA1
from script import SIGHASH_ALL


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


def build_p2pk_script(pubkey_bytes: bytes = None):
        """
        Creates a Pay-to-Public-Key (P2PK) scriptPubKey.

        Args:
            pubkey_bytes (bytes): The public key bytes to use.

        Returns:
            CScript: The P2PK scriptPubKey.
        """
        push_pubkey = bytes([OP_PUSHDATA1, len(pubkey_bytes)]) + pubkey_bytes
        script_pubkey = CScript(push_pubkey + bytes([OP_CHECKSIG]))
        return script_pubkey


def build_p2pkh_script(pubkey_bytes: bytes = None):
    """
    Creates a Pay-to-Public-Key-Hash (P2PKH) scriptPubKey.

    Args:
        pubkey_bytes (bytes): The public key bytes to use.

    Returns:
        CScript: The P2PKH scriptPubKey.
    """
    # Generate pubkey hash
    pubkey_hash = hash160(pubkey_bytes)

    # Build P2PKH scriptPubKey
    script_pubkey = CScript(
        bytes([OP_DUP, OP_HASH160, OP_PUSHBYTES_20]) +  # 0x14 pushes 20 bytes
        pubkey_hash +
        bytes([OP_EQUALVERIFY, OP_CHECKSIG])
    )
    return script_pubkey


def create_coinbase_transaction(coinbase_data, miner_reward, script_pubkey):
    """
    Creates a new coinbase transaction paying the miner.

    Args:
        coinbase_data (bytes, optional): Extra data included in the coinbase transaction. Defaults to an empty byte string.
        miner_reward (int): The amount of the miner reward in satoshis.
        script_pubkey (bytes): The script public key of the miner's address.

    Returns:
        CTransaction: A new coinbase transaction instance.
    """
    # Create transaction
    tx = CTransaction(
        vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=CScript(b""))],
        vout=[CTxOut(nValue=miner_reward, scriptPubKey=script_pubkey)]
    )
    return tx


def main():
    # Recipient's public key (bytes)
    pubkey_bytes = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    
    # Build P2PK script
    # p2pk_script = build_p2pk_script(pubkey_bytes)

    # Build P2PKH script
    p2pkh_script = build_p2pkh_script(pubkey_bytes)

    # Create a coinbase transaction
    coinbase = create_coinbase_transaction(
        coinbase_data=b'',
        miner_reward=5000000000,
        script_pubkey=p2pkh_script
    )

    utxo_set = UTXOSet()

    tx = coinbase
    for tx_in in tx.vin:
        if not tx.is_coinbase():
            utxo_set.spend(tx_in.prevout)

    for index, tx_out in enumerate(tx.vout):
        outpoint = COutPoint(tx.get_hash(), index)
        new_utxo = UTXO(outpoint, tx_out)
        utxo_set.add(new_utxo)

    print(utxo_set.get_balance(p2pkh_script))


if __name__ == '__main__':
    main()
