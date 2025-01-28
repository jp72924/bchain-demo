from hashlib import sha256
import io


class Outpoint:
    def __init__(self, hash, index):
        self.hash = hash
        self.index = index

    def __repr__(self):
        return f"Outpoint(hash={self.hash.hex()}, index={self.index})"


class TxIn:
    def __init__(self, prevout, script_sig):
        self.prevout = prevout
        self.script_sig = script_sig

    def __repr__(self):
        return f"TxIn(prevout={self.prevout}, script_sig={self.script_sig})"


class TxOut:
    def __init__(self, value, script_pubkey):
        self.value = value
        self.script_pubkey = script_pubkey

    def __repr__(self):
        return f"TxOut(value={self.value}, script_pubkey={self.script_pubkey.hex()})"


class Transaction:
    def __init__(self, vin=[], vout=[]):
        self.vin = vin
        self.vout = vout

    def serialize(self):
        """Serializes the transaction into a byte string"""
        stream = io.BytesIO()

        stream.write(len(self.vin).to_bytes(4, 'little'))
        for tx_in in self.vin:
            stream.write(tx_in.prevout.hash)
            stream.write(tx_in.prevout.index.to_bytes(4, 'little'))
            stream.write(len(tx_in.script_sig).to_bytes(4, 'little'))
            stream.write(tx_in.script_sig)

        stream.write(len(self.vout).to_bytes(4, 'little'))
        for tx_out in self.vout:
            stream.write(tx_out.value.to_bytes(8, 'little'))
            stream.write(len(tx_out.script_pubkey).to_bytes(4, 'little'))
            stream.write(tx_out.script_pubkey)

        return stream.getvalue()

    def hash(self):
        """Calculates the transaction hash"""
        raw_transaction = self.serialize()
        return sha256(sha256(raw_transaction).digest()).digest()


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
    raw_transaction = coinbase.serialize()
    tx_hash = coinbase.hash()

    print(f"Serialized Transaction: {raw_transaction.hex()}")
    print(f"Transaction Hash: {tx_hash.hex()}")


if __name__ == '__main__':
    main()