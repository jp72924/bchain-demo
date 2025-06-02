from typing import List
from typing import Union

from crypto import hash256
from crypto import ripemd160
from crypto import sha256
from opcodes import *
from script import CScript
from transaction import CTxIn
from transaction import CTransaction

# --------------------------
# Helper functions
# --------------------------

def decode_num(data: bytes) -> int:
    """Decodes a numeric value from the stack (little-endian, signed)"""
    if not data:
        return 0
    # Reverse for little-endian, handle negative sign
    n = int.from_bytes(data, byteorder='little', signed=True)
    return n

# --------------------------
# Script Execution Engine
# --------------------------

class ScriptExecutionError(Exception): pass


def eval_script(ops: List[Union[int, bytes]], stack: List[bytes], tx: CTransaction, input_index: int, script_pubkey: CScript) -> bool:
    """
    Executes a script (either scriptSig or scriptPubKey) and updates the stack.
    Returns True if execution succeeds, False on error.
    """
    op_count = 0
    try:
        for op in ops:
            # Opcode counting and validation
            if isinstance(op, int):
                op_count += 1
                if op_count > CScript.MAX_OPS_PER_SCRIPT:
                    raise ScriptExecutionError("OP_COUNT_EXCEEDED")

            # --- Stack Operations ---
            if op == OP_DUP:
                if not stack:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                stack.append(stack[-1])

            elif op == OP_HASH160:
                if not stack:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                data = stack.pop()
                stack.append(ripemd160(sha256(data)))

            # --- Numeric Opcodes (Only if `op` is an integer) ---
            elif isinstance(op, int) and op == OP_0:
                stack.append(b'')
            elif isinstance(op, int) and OP_1 <= op <= OP_16:
                num = op - 0x50  # Translate opcode to number (OP_1=0x51 → 1)
                stack.append(num.to_bytes(1, 'little', signed=True))

            # --- Crypto Operations ---
            elif op == OP_CHECKSIG:
                if len(stack) < 2:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                pubkey = stack.pop()
                sig = stack.pop()

                # Extract SIGHASH type (last byte)
                if len(sig) < 1:
                    stack.append(0x00)
                    continue
                sighash_type = sig[-1]
                der_sig = sig[:-1]

                # Compute sighash
                try:
                    sighash = signature_hash(tx, input_index, script_pubkey, sighash_type)
                except ValueError:
                    stack.append(0x00)
                    continue
                
                if not verify_signature(pubkey, der_sig, sighash):
                    stack.append(0x00)
                else:
                    stack.append(0x01)

            elif op == OP_CHECKMULTISIG:
                # Pop n (public key count)
                if len(stack) < 1:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                n = decode_num(stack.pop())
                if n < 0 or n > 20:  # Bitcoin consensus limit
                    raise ScriptExecutionError("PUBKEY_COUNT_INVALID")

                # Pop n public keys
                if len(stack) < n:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                pubkeys = [stack.pop() for _ in range(n)]

                # Pop m (signature count)
                if len(stack) < 1:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                m = decode_num(stack.pop())
                if m < 0 or m > n:
                    raise ScriptExecutionError("SIG_COUNT_INVALID")

                # Pop m signatures
                if len(stack) < m:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                sigs = [stack.pop() for _ in range(m)]

                # Pop dummy element (Bitcoin's off-by-one bug)
                if len(stack) < 1:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                stack.pop()

                # Signature validation logic
                valid_sigs = 0
                pubkeys_remaining = pubkeys.copy()
                for sig in sigs:
                    if not sig:
                        continue  # Skip empty sig
                        
                    # Extract SIGHASH type
                    sighash_type = sig[-1]
                    der_sig = sig[:-1]
                    
                    # Find matching pubkey
                    for i in reversed(range(len(pubkeys_remaining))):
                        try:
                            sighash = signature_hash(tx, input_index, script_pubkey, sighash_type)
                            if verify_signature(pubkeys_remaining[i], der_sig, sighash):
                                valid_sigs += 1
                                del pubkeys_remaining[i]  # Prevent reuse
                                break
                        except:
                            continue

                stack.append(0x01 if valid_sigs >= m else 0x00)

            # --- Flow Control ---
            elif op == OP_EQUAL:
                if len(stack) < 2:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                a = stack.pop()
                b = stack.pop()
                stack.append(0x01 if a == b else 0x00)

            elif op == OP_VERIFY:
                if not stack:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                if stack.pop() == 0x00:
                    raise ScriptExecutionError("VERIFY_FAILED")

            elif op == OP_EQUALVERIFY:
                if len(stack) < 2:
                    raise ScriptExecutionError("STACK_UNDERFLOW")
                # First, perform OP_EQUAL (compare and push result)
                a = stack.pop()
                b = stack.pop()
                stack.append(0x01 if a == b else 0x00)
                
                # Then, perform OP_VERIFY (check top value)
                if stack.pop() == 0x00:
                    raise ScriptExecutionError("EQUALVERIFY_FAILED")

            # --- Data pushes ---
            elif isinstance(op, bytes):
                stack.append(op)

            # Stack size check
            if len(stack) > CScript.MAX_STACK_SIZE:
                raise ScriptExecutionError("STACK_OVERFLOW")

        return True
    except ScriptExecutionError:
        return False


def is_p2sh(script_pubkey: CScript) -> bool:
    """Check if script is a P2SH scriptPubKey."""
    ops = script_pubkey.ops
    return (len(ops) == 3 and
            ops[0] == OP_HASH160 and
            isinstance(ops[1], bytes) and len(ops[1]) == 20 and
            ops[2] == OP_EQUAL)


def verify_script(script_sig: CScript, script_pubkey: CScript, tx: CTransaction, input_index: int) -> bool:
    """
    Bitcoin v0.1 script verification logic
    Returns True if script executes successfully
    """

    # Check script sizes
    if (len(script_sig.data) > CScript.MAX_SCRIPT_SIZE or 
        len(script_pubkey.data) > CScript.MAX_SCRIPT_SIZE):
        return False

    stack = []

    # Execute scriptSig
    if not eval_script(script_sig.ops, stack, tx, input_index, script_pubkey):
        return False

    # Check if scriptPubKey is P2SH
    if is_p2sh(script_pubkey):
        if not stack:
            return False
        redeem_script_bytes = stack[-1]
        redeem_script = CScript(redeem_script_bytes)
        stack_before_p2sh = stack.copy()
        
        # Execute scriptPubKey (consumes redeem_script)
        if not eval_script(script_pubkey.ops, stack, tx, input_index, script_pubkey):
            return False
        
        # Check hash validation result
        if not stack or stack[-1] == b'\x00':
            return False
        stack.pop()  # Remove OP_EQUAL result
        
        # Execute redeemScript with remaining stack elements
        redeem_stack = stack_before_p2sh[:-1]  # Exclude redeem_script
        if not eval_script(redeem_script.ops, redeem_stack, tx, input_index, redeem_script):
            return False
        
        return bool(redeem_stack) and redeem_stack[-1] != b'\x00'
    else:
        # Standard script execution
        if not eval_script(script_pubkey.ops, stack, tx, input_index, script_pubkey):
            return False
        return bool(stack) and stack[-1] != b'\x00'

# --------------------------
# Signature Verification
# --------------------------

def signature_hash(tx: CTransaction, input_index: int, script_pubkey: CScript, sighash_type: int) -> bytes:
    """
    Calculates the signature hash for transaction verification
    """
    # Validate input index
    if input_index < 0 or input_index >= len(tx.vin):
        raise ValueError("Invalid input index")
    
    # Extract SIGHASH flags
    sighash_anyonecanpay = (sighash_type & SIGHASH_ANYONECANPAY) != 0
    base_type = sighash_type & 0x1f  # Mask off ANYONECANPAY bit
    
    # Prepare inputs
    if sighash_anyonecanpay:
        vin = [CTxIn(prevout=tx.vin[input_index].prevout, scriptSig=CScript(b""), 
                    nSequence=tx.vin[input_index].nSequence)]
    else:
        vin = [CTxIn(txin.prevout, CScript(b""), txin.nSequence) for txin in tx.vin]
    
    # Restore scriptSig for current input
    if input_index < len(vin):
        vin[input_index].scriptSig = script_pubkey
    
    # Prepare outputs
    if base_type == SIGHASH_ALL:
        vout = tx.vout.copy()
    elif base_type == SIGHASH_NONE:
        vout = []
        if not sighash_anyonecanpay:
            for i in range(len(vin)):
                if i != input_index:
                    vin[i].nSequence = 0
    elif base_type == SIGHASH_SINGLE:
        if input_index >= len(tx.vout):
            return bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000001")
        vout = [tx.vout[input_index]]
        if not sighash_anyonecanpay:
            for i in range(len(vin)):
                if i != input_index:
                    vin[i].nSequence = 0
    else:
        raise ValueError(f"Unsupported SIGHASH type: {base_type}")
    
    # Build modified transaction
    tx_copy = CTransaction(vin=vin, vout=vout, nLockTime=tx.nLockTime)
    preimage = tx_copy.serialize() + sighash_type.to_bytes(4, 'little')
    return hash256(preimage)

# Simplified ECDSA verification (use proper crypto library in real implementation)
def verify_signature(pubkey: bytes, sig: bytes, sighash: bytes) -> bool:    
    try:
        from ecdsa import VerifyingKey, SECP256k1
        vk = VerifyingKey.from_string(pubkey, curve=SECP256k1)
        return vk.verify(sig, sighash, hashfunc=hashlib.sha256)
    except:
        return False
