import base58
import hashlib
from hashlib import sha256
from transaction import Outpoint, TxIn, TxOut, Transaction
import copy

try:
    import ecdsa
except ImportError:
    print("Please install the ecdsa library: pip install ecdsa")
    exit()


class Wallet:
    def __init__(self):
        """
        Initializes a new Wallet instance.
        """
        self.private_key = None
        self.public_key = None

    @classmethod
    def from_private_key(cls, private_key):
        """
        Creates a Wallet instance from a given private key.

        Args:
            private_key: The private key as bytes.

        Returns:
            A new Wallet instance with the provided private key.
        """
        private_key_obj = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
        wallet = cls()
        wallet.private_key = private_key_obj
        wallet.public_key = private_key_obj.get_verifying_key()
        return wallet

    def sign(self, message):
        """
        Signs a message using the wallet's private key.

        Args:
            message: The message to be signed as bytes.

        Returns:
            The signature as a bytes object.
        """
        return self.private_key.sign(message)

    def create_transaction(self, recipient_public_key, amount, utxo_list):
        """
        Creates a new transaction.

        Args:
            recipient_public_key: The public key of the recipient.
            amount: The amount to send to the recipient.
            utxo_list: A list of UTXOs (Unspent Transaction Outputs) to use as inputs.

        Returns:
            A new Transaction object.
        """
        # 1. Calculate total input value
        total_input = sum(utxo.value for utxo in utxo_list)

        # 2. Create transaction outputs
        outputs = [
            TxOut(amount, recipient_public_key), 
            TxOut(total_input - amount, self.public_key)  # Change output to sender
        ]

        # 3. Create transaction inputs
        inputs = [
            TxIn(
                Outpoint(utxo.tx_hash, utxo.tx_index), b''
            ) 
            for utxo in utxo_list
        ]

        # 4. Create transaction object
        transaction = Transaction(inputs, outputs)

        return transaction

    def sign_transaction(self, transaction):
        """
        Signs a transaction using the wallet's private key.

        Args:
            transaction: The Transaction object to be signed.

        Returns:
            A new Transaction object with the script_sig field in the inputs 
            populated with the signatures.
        """
        new_transaction = Transaction(vin=copy.deepcopy(transaction.vin), 
                                    vout=copy.deepcopy(transaction.vout))

        # Sign the transaction hash
        signature = self.sign(transaction.hash())

        for i, tx_in in enumerate(new_transaction.vin):

            # Append signature to script_sig (simplified example)
            # In a real-world scenario, script_sig would be more complex
            new_transaction.vin[i].script_sig = signature

        return new_transaction

    def verify(self, message, signature):
        """
        Verifies the authenticity of a signature using the wallet's public key.

        Args:
            message: The message as bytes.
            signature: The signature to be verified as bytes.

        Returns:
            True if the signature is valid, False otherwise.
        """
        try:
            self.public_key.verify(signature, message)
            return True
        except:
            return False

    def verify_transaction_signature(self, transaction, utx):
        """
        Verifies the signatures in a transaction.

        Args:
            transaction: The Transaction object to be verified.

        Returns:
            True if all signatures are valid, False otherwise.
        """
        # Create a copy of the transaction (without the script signatures).
        inputs = [
            TxIn(tx_in.prevout, b'') 
            for tx_in in copy.deepcopy(transaction.vin)
        ]
        outputs = copy.deepcopy(transaction.vout)

        # Hash the unsigned transaction
        transaction_hash = Transaction(inputs, outputs).hash()

        for i, tx_in in enumerate(transaction.vin):
            # Verify the signature
            try:
                self.verify(transaction_hash, tx_in.script_sig) 
            except:
                return False  # Signature verification failed

        return True

    def get_address(self, testnet=False):
        """
        Generates a Bitcoin address from the wallet's public key.

        Args:
            testnet: If True, generates a testnet address. Defaults to False.

        Returns:
            The Bitcoin address as a string.
        """
        # 1. Hash the public key with SHA-256
        sha256_hash = sha256(self.public_key.to_string("compressed")).digest()

        # 2. Hash the SHA-256 hash with RIPEMD-160
        ripemd160_hash = hashlib.new('ripemd160')
        ripemd160_hash.update(sha256_hash)
        hash160 = ripemd160_hash.digest()

        # 3. Add prefix byte
        if testnet:
            prefix = bytes([0x6F])  # Testnet prefix byte
        else:
            prefix = bytes([0x00])  # Mainnet prefix byte

        payload = prefix + hash160

        # 4. Calculate checksum
        checksum = sha256(sha256(payload).digest()).digest()[:4]

        # 5. Combine payload and checksum
        final_bytes = payload + checksum

        # 6. Encode with Base58Check
        address = base58.b58encode(final_bytes).decode('utf-8')

        return address

def main():
    # Example usage:
    private_key = bytes.fromhex("93b4e468821ac20a05df4404f4b401c46f0e18f3dc819f134bd39d003641387c")

    wallet = Wallet.from_private_key(private_key)
    print("Address (mainnet):", wallet.get_address())

    message = b'Hello, world!'
    signature = wallet.sign(message)

    is_valid = wallet.verify(message, signature)
    print(f"Message signature is valid: {is_valid}")

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
        script_pubkey=bytes.fromhex("026e21e332324f8634ef47584ef130dd97828e2f626a5f2d7d7a1a33e32a26ac20")  # Recipient's public key (bytes)
    )

    # Create a transaction
    coinbase = Transaction(vin=[tx_in], vout=[tx_out])

    # Sign the transaction
    signed_transaction = wallet.sign_transaction(coinbase)

    # Verify the signatures
    is_valid = wallet.verify_transaction_signature(signed_transaction, coinbase)
    print(f"Transaction signatures are valid: {is_valid}")


if __name__ == '__main__':
    main()