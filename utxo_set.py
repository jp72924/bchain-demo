from transaction import Outpoint, TxIn, TxOut, Transaction


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
            raise ValueError(f"UTXO ({utxo.prevout.hash.hex()}, {utxo.prevout.index}) not found or already spent.")

    def is_unspent(self, prevout):
        return prevout in self.utxos

    def get_balance(self, script_pubkey=None):
        return sum(tx_out.value for tx_out in self.utxos.values() if tx_out.script_pubkey == script_pubkey)

    def __repr__(self):
        return f"UTXOSet({list(self.utxos.values())})"


def main():
    # Create sample UTXOs
    prevout = Outpoint(
        hash=bytes.fromhex("0" * 64),
        index=int('0xffffffff', 16),  # 2 ^ 32 (maximun value)
    )

    tx_in = TxIn(
        prevout=prevout,
        script_sig=b''  # Sender's signature (signs transaction hash using the private key)
    )

    tx_out = TxOut(
        value=5000000000,  # 50 Bitcoins (5,000,000,000 sats)
        script_pubkey=bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")  # Recipient's public key (bytes)
    )

    # Create a transaction
    coinbase = Transaction(vin=[tx_in], vout=[tx_out])

    # Serialize and hash the transaction
    tx_hash = coinbase.hash()
    print(f"Transaction Hash: {tx_hash.hex()}")

    utxo = UTXO(prevout, tx_out)
    utxo_set = UTXOSet()
    utxo_set.add(utxo)
    print(utxo_set)
    print(utxo_set.is_unspent(utxo.prevout))
    print(utxo_set.get_balance(utxo.tx_out.script_pubkey))
    utxo_set.spend(utxo.prevout)
    print(utxo_set.is_unspent(utxo.prevout))
    print(utxo_set.get_balance(utxo.tx_out.script_pubkey))


if __name__ == '__main__':
    main()
