import hashlib
import ecdsa

def sha256(data):
    return hashlib.sha256(data).digest()

class UTXO:
    def __init__(self, txid, vout, amount, address):
        self.txid = txid  # Transaction ID where this UTXO was created
        self.vout = vout  # Output index in the transaction
        self.amount = amount  # Amount of satoshis
        self.address = address # Recipient's address (public key)

    def to_dict(self):
        return {
            "txid": self.txid.hex() if isinstance(self.txid, bytes) else self.txid,
            "vout": self.vout,
            "amount": self.amount,
            "address": self.address.hex() if isinstance(self.address, bytes) else self.address
        }

    @classmethod
    def from_dict(cls, data):
        return cls(bytes.fromhex(data["txid"]), data["vout"], data["amount"], bytes.fromhex(data["address"]))


class Transaction:
    def __init__(self):
        self.inputs = []  # List of input UTXOs
        self.outputs = [] # List of output UTXOs

    def add_input(self, utxo, private_key):
        self.inputs.append({"utxo": utxo, "signature": self.sign_input(utxo, private_key)})

    def add_output(self, amount, address):
        self.outputs.append({"amount": amount, "address": address})

    def sign_input(self, utxo, private_key):
        message = self.to_bytes(utxo)
        sk = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
        signature = sk.sign(message)
        return signature

    def verify_input(self, input_data):
        utxo = input_data["utxo"]
        signature = input_data["signature"]
        vk = ecdsa.VerifyingKey.from_string(utxo.address, curve=ecdsa.SECP256k1)
        message = self.to_bytes(utxo)
        try:
            return vk.verify(signature, message)
        except ecdsa.BadSignatureError:
            return False

    def to_bytes(self, utxo):
        data = utxo.txid + utxo.vout.to_bytes(4, 'big') + utxo.address
        return data

    def calculate_txid(self):
        # A simplified TXID calculation. In real Bitcoin, it's more complex.
        tx_data = b""
        for input_data in self.inputs:
            tx_data += self.to_bytes(input_data["utxo"])
        for output in self.outputs:
            tx_data += output["amount"].to_bytes(8, 'big') + output["address"]
        return sha256(tx_data)

# Example usage:
private_key_alice = b'YOUR_PRIVATE_KEY_ALICE' # Replace with actual private keys
public_key_alice = ecdsa.SigningKey.from_string(private_key_alice, curve=ecdsa.SECP256k1).verifying_key.to_string()

private_key_bob = b'YOUR_PRIVATE_KEY_BOB' # Replace with actual private keys
public_key_bob = ecdsa.SigningKey.from_string(private_key_bob, curve=ecdsa.SECP256k1).verifying_key.to_string()

# Create a UTXO for Alice (simulating a previous transaction)
utxo_alice = UTXO(sha256(b"previous_tx"), 0, 10, public_key_alice)

# Create a transaction from Alice to Bob
tx = Transaction()
tx.add_input(utxo_alice, private_key_alice)  # Alice spends her UTXO
tx.add_output(7, public_key_bob)       # 7 to Bob
tx.add_output(3, public_key_alice)       # 3 back to Alice (change)

txid = tx.calculate_txid()
print("Transaction ID:", txid.hex())

# Verification
for input_data in tx.inputs:
    if tx.verify_input(input_data):
        print("Input signature verified.")
    else:
        print("Input signature verification failed.")

# Example of serialization/deserialization
import json
utxo_dict = utxo_alice.to_dict()
utxo_json = json.dumps(utxo_dict)
print(utxo_json)
utxo_restored = UTXO.from_dict(json.loads(utxo_json))
print(utxo_restored.to_dict())