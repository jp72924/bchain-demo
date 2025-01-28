import binascii
import hashlib
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

INITIAL_HASH = "b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553"

PVT_KEY_PATH = "private_key.pem"
PUB_KEY_PATH = "public_key.pem"

# Import the private key from a file (securely!)
with open('private_key.pem', 'rb') as f:
    private_key = serialization.load_pem_private_key(
        f.read(),
        password=None  # If the key is encrypted, provide the password here
    )


def sha256(data):
    # Hash the message
    hash_object = hashes.Hash(hashes.SHA256())
    hash_object.update(data.encode())
    return hash_object.finalize()


def sign_data(data, private_key):
    # Sign the hash with the private key
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature


class Block(object):
    """docstring for Block"""
    def __init__(self, id, data, prev_hash):
        super(Block, self).__init__()
        self.id = id
        # self.timestamp = timestamp
        self.data = data
        self.prev_hash = prev_hash

        self.nonce = 0
        self.hash = None

    def calculate_hash(self):
        block_data = self.__dict__
        json_data = json.dumps(block_data)
        digest = sha256(json_data)
        return binascii.hexlify(digest).decode('ascii')
        
    def mine(self):
        while True:
            block_hash = self.calculate_hash()

            if block_hash.startswith("0000"):
                self.hash = block_hash
                break

            self.nonce += 1

    def __repr__(self):
        return str(self.__dict__)


class Transaction(object):
    """docstring for Transaction"""
    def __init__(self, id, sender, receiver, amount):
        super(Transaction, self).__init__()
        self.id = id
        # self.timestamp = timestamp
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        # self.memo = memo

        digest = self.calculate_hash()
        self.hash = binascii.hexlify(digest).decode('ascii')

    def calculate_hash(self):
        tx_data = self.__dict__
        json_data = json.dumps(tx_data)
        return sha256(json_data)

    def sign(self, private_key):
        signature = sign_data(self.calculate_hash(), private_key)
        self.signature = binascii.hexlify(signature).decode('ascii')

    def __repr__(self):
        return str(self.__dict__)


txn = Transaction(1, "Alice", "Bob", 7)
txn.sign(private_key)

gen = Block(1, [txn.__dict__], INITIAL_HASH)
gen.mine()
print(gen)