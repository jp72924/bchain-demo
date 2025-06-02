import copy

from crypto import hash160
from crypto import hash256
from interpreter import signature_hash
from opcodes import OP_PUSHDATA1
from opcodes import SIGHASH_ALL
from script import CScript
from script_utils import ScriptBuilder
from transaction import COutPoint
from transaction import CTxIn
from transaction import CTxOut
from transaction import CTransaction

try:
    import base58
except ImportError:
    print("Please install the ecdsa library: pip install base58")
    exit()

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

    def create_transaction(self, script_pubkey, amount, utxo_list):
        """
        Creates a new transaction.

        Args:
            script_pubkey: The recipient's scriptPubKey (CScript object).
            amount: The amount to send to the recipient (in satoshis).
            utxo_list: A list of UTXOs (Unspent Transaction Outputs) to use as inputs.

        Returns:
            A new CTransaction object.
        """
        # 1. Calculate total input value
        total_input = sum(utxo.tx_out.nValue for utxo in utxo_list)

        # 2. Create transaction outputs
        pubkey_bytes = self.public_key.to_string("compressed")

        vout = [
            CTxOut(amount, script_pubkey),
            CTxOut(total_input - amount, ScriptBuilder.p2pkh_script_pubkey(pubkey_bytes))  # Change output to sender (P2PKH)
        ]

        # 3. Create transaction inputs
        vin = [
            CTxIn(
                COutPoint(utxo.prevout.hash, utxo.prevout.n), CScript(b'')
            )
            for utxo in utxo_list
        ]

        # 4. Create transaction object
        transaction = CTransaction(vin, vout)

        return transaction

    def sign_transaction(self, transaction):
        """
        Signs a transaction using the wallet's private key.

        Args:
            transaction: The CTransaction object to be signed.

        Returns:
            A new CTransaction object with the scriptSig field in the inputs
            populated with the signatures.
        """
        new_transaction = CTransaction(vin=copy.deepcopy(transaction.vin),
                                        vout=copy.deepcopy(transaction.vout))

        # Sign the transaction hash for each input
        for i, tx_in in enumerate(new_transaction.vin):
            # Assuming a simple P2PKH input for signing
            pubkey_bytes = self.public_key.to_string("compressed")
            script_pubkey = ScriptBuilder.p2pkh_script_pubkey(pubkey_bytes)
            sighash = signature_hash(new_transaction, i, script_pubkey, SIGHASH_ALL)
            signature = self.sign(sighash)
            script_sig = ScriptBuilder.p2pkh_script_sig(signature, pubkey_bytes)
            new_transaction.vin[i].scriptSig = script_sig

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

    def verify_transaction(self, transaction):
        """
        Verifies the signatures in a transaction (simplified for P2PKH).

        Args:
            transaction: The CTransaction object to be verified.

        Returns:
            True if all signatures are valid, False otherwise.
        """
        # Iterate through each input in the transaction
        for i, tx_in in enumerate(transaction.vin):
            # Extract the scriptSig from the transaction input
            script_sig = tx_in.scriptSig
            # Assume the output being spent is a P2PKH scriptPubKey for simplicity
            # In a real scenario, you would need to fetch the actual scriptPubKey
            script_pubkey = ScriptBuilder.p2pkh_script_pubkey(self.public_key.to_string("compressed"))
            # A P2PKH scriptSig should contain two elements: the signature and the public key
            if len(script_sig.ops) != 2:
                return False  # ScriptSig does not have the expected number of elements
            # The signature is the first element pushed onto the stack
            signature_bytes = script_sig.ops[0]
            # The public key is the second element pushed onto the stack
            pubkey_bytes = script_sig.ops[1]
            # Calculate the hash of the transaction to be signed
            # This hash depends on the input being verified and the scriptPubKey of the output being spent
            sighash = signature_hash(transaction, i, script_pubkey, SIGHASH_ALL)
            # Verify the signature against the transaction hash) using the public key
            verifying_key = ecdsa.VerifyingKey.from_string(pubkey_bytes, curve=ecdsa.SECP256k1)
            try:
                verifying_key.verify(signature_bytes, sighash)
            except:
                return False  # Signature verification failed for this input
        # If all input signatures are successfully verified, return True
        return True

    def get_address(self, testnet=False):
        """
        Generates a Bitcoin address from the wallet's public key.

        Args:
            testnet: If True, generates a testnet address. Defaults to False.

        Returns:
            The Bitcoin address as a string.
        """
        pubkey_bytes = self.public_key.to_string("compressed")

        # 1. Hash the public key with HASH160
        pubkey_hash = hash160(pubkey_bytes)

        # 2. Add prefix byte
        if testnet:
            prefix = bytes([0x6F])  # Testnet prefix byte
        else:
            prefix = bytes([0x00])  # Mainnet prefix byte

        payload = prefix + pubkey_hash

        # 3. Calculate checksum
        checksum = hash256(payload)[:4]

        # 4. Combine payload and checksum
        final_bytes = payload + checksum

        # 5. Encode with Base58Check
        address = base58.b58encode(final_bytes).decode('utf-8')

        return address


def create_coinbase_transaction(coinbase_data: CScript, miner_reward: int, script_pubkey: CScript):
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
    # Sender's private key (bytes)
    sender_sk_bytes = bytes.fromhex("93b4e468821ac20a05df4404f4b401c46f0e18f3dc819f134bd39d003641387c")

    # Recipient's public key (bytes)
    recipient_pk_bytes = bytes.fromhex("026e21e332324f8634ef47584ef130dd97828e2f626a5f2d7d7a1a33e32a26ac20")

    # Create a wallet from private key string (bytes representation)
    wallet = Wallet.from_private_key(sender_sk_bytes)
    print("Address (mainnet):", wallet.get_address())

    # Create a sign a message with Sender's private key
    message = b'Hello, world!'
    signature = wallet.sign(message)

    # Verify message signature
    is_valid = wallet.verify(message, signature)
    print(f"Message signature is valid: {is_valid}")

    # Example of creating P2PKH scriptPubKey
    p2pkh_script = ScriptBuilder.p2pkh_script_pubkey(recipient_pk_bytes)
    print("P2PKH ScriptPubKey:", p2pkh_script)

    # Create a coinbase transaction
    coinbase = create_coinbase_transaction(
        coinbase_data=CScript(b''),
        miner_reward=5_000_000_000,
        script_pubkey=p2pkh_script
    )

    # Sign the transaction
    signed_transaction = wallet.sign_transaction(coinbase)

    # Verify the signatures
    is_valid = wallet.verify_transaction(signed_transaction)
    print(f"Transaction signatures are valid: {is_valid}")


if __name__ == '__main__':
    main()
