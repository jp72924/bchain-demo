from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der
import hashlib
import copy
from hashlib import sha256

# Import necessary classes (assumes prior implementation)
from script import CScript, ScriptInterpreter
from transaction import CTransaction, CTxIn, CTxOut, COutPoint

# -----------------------------------------
# Helper Functions
# -----------------------------------------
def create_signing_hash(tx: CTransaction, utxo_script: CScript, input_index: int) -> bytes:
    """Compute the transaction hash for signing (replaces scriptSig with UTXO scriptPubKey)."""
    modified_tx = copy.deepcopy(tx)
    modified_tx.vin[input_index].scriptSig = utxo_script
    return modified_tx.get_hash()

# -----------------------------------------
# Key Generation
# -----------------------------------------
# Generate a secp256k1 key pair
sk = SigningKey.generate(curve=SECP256k1)
vk = sk.get_verifying_key()
pubkey = vk.to_string("compressed")  # 33-byte compressed public key

# -----------------------------------------
# P2PK (Pay-to-Public-Key) Demonstration
# -----------------------------------------
print("\n=== P2PK (Pay-to-Public-Key) ===")

# Step 1: Create P2PK scriptPubKey: <pubkey> OP_CHECKSIG
script_pubkey_p2pk = CScript()
script_pubkey_p2pk.push_data(pubkey)  # Push public key
script_pubkey_p2pk.push_opcode(ScriptInterpreter.OP_CHECKSIG)

# Step 2: Build transaction
tx_p2pk = CTransaction(
    vin=[CTxIn(COutPoint(), scriptSig=CScript())],  # Empty scriptSig
    vout=[CTxOut(1000, script_pubkey_p2pk)]
)

# Step 3: Compute signing hash (scriptSig replaced with scriptPubKey)
tx_hash_p2pk = create_signing_hash(tx_p2pk, script_pubkey_p2pk, 0)

# Step 4: Sign the hash
signature_p2pk = sk.sign_digest(
    tx_hash_p2pk,
    sigencode=lambda r, s, order: sigencode_der(r, s, order) + b"\x01"  # SIGHASH_ALL
)

# Step 5: Build scriptSig: <signature>
script_sig_p2pk = CScript()
script_sig_p2pk.push_data(signature_p2pk)
tx_p2pk.vin[0].scriptSig = script_sig_p2pk

# Step 6: Validate
utxo_p2pk = CTxOut(1000, script_pubkey_p2pk)
is_valid_p2pk = tx_p2pk.validate_input(0, utxo_p2pk)
print(f"P2PK Validation: {is_valid_p2pk}")  # Output: True

# -----------------------------------------
# P2PKH (Pay-to-Public-Key-Hash) Demonstration
# -----------------------------------------
print("\n=== P2PKH (Pay-to-Public-Key-Hash) ===")

# Step 1: Compute public key hash (RIPEMD-160 of SHA-256)
pubkey_hash = hashlib.new('ripemd160', sha256(pubkey).digest()).digest()

# Step 2: Create P2PKH scriptPubKey: OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG
script_pubkey_p2pkh = CScript()
script_pubkey_p2pkh.push_opcode(ScriptInterpreter.OP_DUP)
script_pubkey_p2pkh.push_opcode(ScriptInterpreter.OP_HASH160)
script_pubkey_p2pkh.push_data(pubkey_hash)
script_pubkey_p2pkh.push_opcode(ScriptInterpreter.OP_EQUALVERIFY)
script_pubkey_p2pkh.push_opcode(ScriptInterpreter.OP_CHECKSIG)

# Step 3: Build transaction
tx_p2pkh = CTransaction(
    vin=[CTxIn(COutPoint(), scriptSig=CScript())],  # Empty scriptSig
    vout=[CTxOut(2000, script_pubkey_p2pkh)]
)

# Step 4: Compute signing hash (scriptSig replaced with scriptPubKey)
tx_hash_p2pkh = create_signing_hash(tx_p2pkh, script_pubkey_p2pkh, 0)

# Step 5: Sign the hash
signature_p2pkh = sk.sign_digest(
    tx_hash_p2pkh,
    sigencode=lambda r, s, order: sigencode_der(r, s, order) + b"\x01"  # SIGHASH_ALL
)

# Step 6: Build scriptSig: <signature> <pubkey>
script_sig_p2pkh = CScript()
script_sig_p2pkh.push_data(signature_p2pkh)
script_sig_p2pkh.push_data(pubkey)
tx_p2pkh.vin[0].scriptSig = script_sig_p2pkh

# Step 7: Validate
utxo_p2pkh = CTxOut(2000, script_pubkey_p2pkh)
is_valid_p2pkh = tx_p2pkh.validate_input(0, utxo_p2pkh)
print(f"P2PKH Validation: {is_valid_p2pkh}")  # Output: True