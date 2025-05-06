import io

from crypto import hash256
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
        return hash((self.hash, self.n))

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

    def serialize(self) -> bytes:
        return self.hash + self.n.to_bytes(4, 'little')


class CTxIn:
    def __init__(self, prevout: COutPoint, scriptSig: 'CScript', nSequence: int = 0xffffffff):
        self.prevout = prevout
        self.scriptSig = scriptSig
        self.nSequence = nSequence

    def __repr__(self):
        return f"CTxIn(prevout={self.prevout}, scriptSig={self.scriptSig}, nSequence={self.nSequence})"  

    def serialize(self) -> bytes:
        return (
            self.prevout.serialize() +
            compact_size(len(self.scriptSig.data)) +
            self.scriptSig.data +
            self.nSequence.to_bytes(4, 'little')
        )

class CTxOut:
    def __init__(self, nValue: int, scriptPubKey: 'CScript'):
        self.nValue = nValue  # Renamed field
        self.scriptPubKey = scriptPubKey  # Case correction

    def __repr__(self):
        return f"CTxOut(nValue={self.nValue}, scriptPubKey={self.scriptPubKey.data.hex()})"

    def serialize(self) -> bytes:
        return (
            self.nValue.to_bytes(8, 'little') +
            compact_size(len(self.scriptPubKey.data)) +
            self.scriptPubKey.data
        )

class CTransaction:
    def __init__(self, nVersion: int = 1, vin: list[CTxIn] = None, 
                 vout: list[CTxOut] = None, nLockTime: int = 0):
        self.nVersion = nVersion  # Added version field
        self.vin = vin or []
        self.vout = vout or []
        self.nLockTime = nLockTime  # Fix: Initialize nLockTime

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
        # Version
        stream.write(self.nVersion.to_bytes(4, 'little'))
        
        # Inputs
        stream.write(compact_size(len(self.vin)))
        for txin in self.vin:
            stream.write(txin.serialize())
        
        # Outputs
        stream.write(compact_size(len(self.vout)))
        for txout in self.vout:
            stream.write(txout.serialize())
        
        # Lock time
        stream.write(self.nLockTime.to_bytes(4, 'little'))
        return stream.getvalue()

    def get_hash(self):
        """Calculates the transaction hash"""
        raw_transaction = self.serialize()
        return hash256(raw_transaction)
