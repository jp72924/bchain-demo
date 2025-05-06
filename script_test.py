from transaction import COutPoint, CTxIn, CTxOut, CTransaction
from script import verify_script
from crypto import sha256, ripemd160
from script import signature_hash, CScript
from script import SIGHASH_ALL, OP_DUP, OP_HASH160, OP_PUSHBYTES_20, OP_0, OP_2, OP_3, OP_CHECKMULTISIG, OP_PUSHBYTES_33, OP_PUSHDATA1, OP_EQUALVERIFY, OP_CHECKSIG
import hashlib
from ecdsa import SigningKey, SECP256k1
from script_utils import ScriptBuilder

# --------------------------
# Example Usage
# --------------------------

if __name__ == "__main__":
    # Generate key pair
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()
    pubkey = vk.to_string("compressed")

    # Build P2PK scriptPubKey (push 33-byte pubkey + OP_CHECKSIG)
    push_pubkey = bytes([OP_PUSHDATA1, len(pubkey)]) + pubkey  # 0x21 = 33 bytes
    script_pubkey = CScript(push_pubkey + bytes([OP_CHECKSIG]))

    # Create transaction
    tx = CTransaction(
        vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=CScript(b""))],  # Coinbase input
        vout=[CTxOut(nValue=50_000_000, scriptPubKey=script_pubkey)]
    )

    # Sign transaction
    sighash = signature_hash(tx, 0, script_pubkey, SIGHASH_ALL)
    signature = sk.sign(sighash, hashfunc=hashlib.sha256)

    # Build scriptSig (push 71-byte signature)
    push_sig = bytes([OP_PUSHDATA1, len(signature)]) + signature
    script_sig = CScript(push_sig)

    # Attach and verify
    tx.vin[0].scriptSig = script_sig
    print("P2PK Verification:", verify_script(script_sig, script_pubkey, tx, 0))  # Output: True

    # Generate pubkey hash
    pubkey_hash = ripemd160(sha256(pubkey))

    # Build P2PKH scriptPubKey
    script_pubkey = CScript(
        bytes([OP_DUP, OP_HASH160, OP_PUSHBYTES_20]) +  # 0x14 pushes 20 bytes
        pubkey_hash +
        bytes([OP_EQUALVERIFY, OP_CHECKSIG])
    )

    # Create transaction
    tx = CTransaction(
        vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=CScript(b""))],
        vout=[CTxOut(nValue=50_000_000, scriptPubKey=script_pubkey)]
    )

    # Sign transaction
    sighash = signature_hash(tx, 0, script_pubkey, SIGHASH_ALL)
    signature = sk.sign(sighash, hashfunc=hashlib.sha256)

    # Build scriptSig (push sig + pubkey)
    push_sig = bytes([OP_PUSHDATA1, len(signature)]) + signature
    push_pubkey = bytes([OP_PUSHDATA1, OP_PUSHBYTES_33]) + pubkey
    script_sig = CScript(push_sig + push_pubkey)

    # Attach and verify
    tx.vin[0].scriptSig = script_sig
    print("P2PKH Verification:", verify_script(script_sig, script_pubkey, tx, 0))  # Output: True

    # Generate 3 key pairs
    sk1 = SigningKey.generate(curve=SECP256k1)
    vk1 = sk1.get_verifying_key()
    pubkey1 = vk1.to_string("compressed")

    sk2 = SigningKey.generate(curve=SECP256k1)
    vk2 = sk2.get_verifying_key()
    pubkey2 = vk2.to_string("compressed")

    sk3 = SigningKey.generate(curve=SECP256k1)
    vk3 = sk3.get_verifying_key()
    pubkey3 = vk3.to_string("compressed")

    # Build P2MS scriptPubKey
    push_pubkeys = (
        bytes([OP_2]) +
        bytes([OP_PUSHDATA1, OP_PUSHBYTES_33]) + pubkey1 +
        bytes([OP_PUSHDATA1, OP_PUSHBYTES_33]) + pubkey2 +
        bytes([OP_PUSHDATA1, OP_PUSHBYTES_33]) + pubkey3 +
        bytes([OP_3, OP_CHECKMULTISIG])
    )
    script_pubkey = CScript(push_pubkeys)

    # Create transaction
    tx = CTransaction(
        vin=[CTxIn(prevout=COutPoint(bytes(32), 0xffffffff), scriptSig=CScript(b""))],
        vout=[CTxOut(nValue=50_000_000, scriptPubKey=script_pubkey)]
    )

    # Sign with 2 keys
    sighash = signature_hash(tx, 0, script_pubkey, SIGHASH_ALL)
    sig1 = sk1.sign(sighash, hashfunc=hashlib.sha256)
    sig2 = sk2.sign(sighash, hashfunc=hashlib.sha256)

    # Build scriptSig (OP_0 + sig1 + sig2)
    script_sig = CScript(
        bytes([OP_0]) +  # Dummy for off-by-one bug
        bytes([OP_PUSHDATA1, len(sig1)]) + sig1 +
        bytes([OP_PUSHDATA1, len(sig2)]) + sig2
    )

    # Attach and verify
    tx.vin[0].scriptSig = script_sig
    print("P2MS Verification:", verify_script(script_sig, script_pubkey, tx, 0))  # Output: True