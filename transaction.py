from hashlib import sha256
import io
from serialize import compact_size


class COutPoint:
    def __init__(self, hash: bytes = bytes(32), n: int = 0xffffffff):
        if len(hash) != 32:
            raise ValueError("COutPoint hash must be 32 bytes")
        self.hash = hash
        self.n = n

    def __repr__(self):
        return f"COutPoint(hash={self.hash.hex()}, n={self.n})"

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        if not isinstance(other, COutPoint):
            # Don't attempt to compare against unrelated types
            return NotImplemented
        return self.hash == other.hash and self.n == other.n

    def is_null(self):
        """
        Checks if the COutPoint is a null outpoint.

        A null outpoint is defined as having a hash of all zeros 
        and an index of 0xffffffff.

        Returns:
            bool: True if the COutPoint is a null outpoint, False otherwise.
        """
        return self.hash == bytes(32) and self.n == 0xffffffff


class CTxIn:
    def __init__(self, prevout: COutPoint, scriptSig: bytes):
        self.prevout = prevout
        self.scriptSig = scriptSig

    def __repr__(self):
        return f"CTxIn(prevout={self.prevout}, scriptSig={self.scriptSig})"


class CTxOut:
    def __init__(self, nValue: int, scriptPubKey: bytes):
        self.nValue = nValue  # Renamed field
        self.scriptPubKey = scriptPubKey  # Case correction

    def __repr__(self):
        return f"CTxOut(nValue={self.nValue}, scriptPubKey={self.scriptPubKey.hex()})"


class CTransaction:
    def __init__(self, nVersion: int = 1, vin: list[CTxIn] = None, 
                 vout: list[CTxOut] = None):
        self.nVersion = nVersion  # Added version field
        self.vin = vin or []
        self.vout = vout or []

    def is_coinbase(self):
        """
        Checks if the transaction is a coinbase transaction.

        Returns:
            bool: True if the transaction is a coinbase transaction, False otherwise.
        """
        if len(self.vin) != 1:
            return False  # Coinbase transactions have only one input

        coinbase_input = self.vin[0] 
        return coinbase_input.prevout.is_null()

    def serialize(self):
        """Serializes the transaction into a byte string"""
        stream = io.BytesIO()

        stream.write(len(self.vin).to_bytes(4, 'little'))
        for tx_in in self.vin:
            stream.write(tx_in.prevout.hash)
            stream.write(tx_in.prevout.n.to_bytes(4, 'little'))
            stream.write(compact_size(len(tx_in.scriptSig)))
            stream.write(tx_in.scriptSig)

        stream.write(len(self.vout).to_bytes(4, 'little'))
        for tx_out in self.vout:
            stream.write(tx_out.nValue.to_bytes(8, 'little'))
            stream.write(compact_size(len(tx_out.scriptPubKey)))
            stream.write(tx_out.scriptPubKey)

        return stream.getvalue()

    def get_hash(self):
        """Calculates the transaction hash"""
        raw_transaction = self.serialize()
        return sha256(sha256(raw_transaction).digest()).digest()


def main():
    # Create sample UTXOs
    prevout = COutPoint(
        hash=bytes(32),
        n=int('0xffffffff', 16),  # 2 ^ 32 (maximun nValue)
    )

    tx_in = CTxIn(
        prevout=prevout,
        scriptSig=b''  # Sender's signature (signs transaction hash using the private key)
    )

    tx_out = CTxOut(
        nValue=5000000000,  # 50 Bitcoins (5,000,000,000 sats)
        scriptPubKey=bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")  # Recipient's public key (bytes)
    )

    # Create a transaction
    coinbase = CTransaction(vin=[tx_in], vout=[tx_out])

    # Serialize and hash the transaction
    raw_transaction = coinbase.serialize()
    tx_hash = coinbase.get_hash()

    print(f"Serialized Transaction: {raw_transaction.hex()}")
    print(f"Transaction Hash: {tx_hash.hex()}")


if __name__ == '__main__':
    main()