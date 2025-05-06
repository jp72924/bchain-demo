from typing import List, Union
from transaction import CTransaction, CTxIn
from crypto import sha256, ripemd160, hash256

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
# Script Opcodes (Partial List)
# --------------------------

SIGHASH_ALL = 0x01
SIGHASH_NONE = 0x02
SIGHASH_SINGLE = 0x03
SIGHASH_ANYONECANPAY = 0x80

OP_0 = 0x00
OP_FALSE = OP_0
OP_PUSHBYTES_1  = 0x01
OP_PUSHBYTES_2  = 0x02
OP_PUSHBYTES_3  = 0x03
OP_PUSHBYTES_4  = 0x04
OP_PUSHBYTES_5  = 0x05
OP_PUSHBYTES_6  = 0x06
OP_PUSHBYTES_7  = 0x07
OP_PUSHBYTES_8  = 0x08
OP_PUSHBYTES_9  = 0x09
OP_PUSHBYTES_10 = 0x0a
OP_PUSHBYTES_11 = 0x0b
OP_PUSHBYTES_12 = 0x0c
OP_PUSHBYTES_13 = 0x0d
OP_PUSHBYTES_14 = 0x0e
OP_PUSHBYTES_15 = 0x0f
OP_PUSHBYTES_16 = 0x10
OP_PUSHBYTES_17 = 0x11
OP_PUSHBYTES_18 = 0x12
OP_PUSHBYTES_19 = 0x13
OP_PUSHBYTES_20 = 0x14
OP_PUSHBYTES_21 = 0x15
OP_PUSHBYTES_22 = 0x16
OP_PUSHBYTES_23 = 0x17
OP_PUSHBYTES_24 = 0x18
OP_PUSHBYTES_25 = 0x19
OP_PUSHBYTES_26 = 0x1a
OP_PUSHBYTES_27 = 0x1b
OP_PUSHBYTES_28 = 0x1c
OP_PUSHBYTES_29 = 0x1d
OP_PUSHBYTES_30 = 0x1e
OP_PUSHBYTES_31 = 0x1f
OP_PUSHBYTES_32 = 0x20
OP_PUSHBYTES_33 = 0x21
OP_PUSHBYTES_34 = 0x22
OP_PUSHBYTES_35 = 0x23
OP_PUSHBYTES_36 = 0x24
OP_PUSHBYTES_37 = 0x25
OP_PUSHBYTES_38 = 0x26
OP_PUSHBYTES_39 = 0x27
OP_PUSHBYTES_40 = 0x28
OP_PUSHBYTES_41 = 0x29
OP_PUSHBYTES_42 = 0x2a
OP_PUSHBYTES_43 = 0x2b
OP_PUSHBYTES_44 = 0x2c
OP_PUSHBYTES_45 = 0x2d
OP_PUSHBYTES_46 = 0x2e
OP_PUSHBYTES_47 = 0x2f
OP_PUSHBYTES_48 = 0x30
OP_PUSHBYTES_49 = 0x31
OP_PUSHBYTES_50 = 0x32
OP_PUSHBYTES_51 = 0x33
OP_PUSHBYTES_52 = 0x34
OP_PUSHBYTES_53 = 0x35
OP_PUSHBYTES_54 = 0x36
OP_PUSHBYTES_55 = 0x37
OP_PUSHBYTES_56 = 0x38
OP_PUSHBYTES_57 = 0x39
OP_PUSHBYTES_58 = 0x3a
OP_PUSHBYTES_59 = 0x3b
OP_PUSHBYTES_60 = 0x3c
OP_PUSHBYTES_61 = 0x3d
OP_PUSHBYTES_62 = 0x3e
OP_PUSHBYTES_63 = 0x3f
OP_PUSHBYTES_64 = 0x40
OP_PUSHBYTES_65 = 0x41
OP_PUSHBYTES_66 = 0x42
OP_PUSHBYTES_67 = 0x43
OP_PUSHBYTES_68 = 0x44
OP_PUSHBYTES_69 = 0x45
OP_PUSHBYTES_70 = 0x46
OP_PUSHBYTES_71 = 0x47
OP_PUSHBYTES_72 = 0x48
OP_PUSHBYTES_73 = 0x49
OP_PUSHBYTES_74 = 0x4a
OP_PUSHBYTES_75 = 0x4b
OP_PUSHDATA1 = 0x4c
OP_PUSHDATA2 = 0x4d
OP_PUSHDATA4 = 0x4e
OP_1  = 0x51
OP_TRUE = OP_1
OP_2  = 0x52
OP_3  = 0x53
OP_4  = 0x54
OP_5  = 0x55
OP_6  = 0x56
OP_7  = 0x57
OP_8  = 0x58
OP_9  = 0x59
OP_10 = 0x5a
OP_11 = 0x5b
OP_12 = 0x5c
OP_13 = 0x5d
OP_14 = 0x5e
OP_15 = 0x5f
OP_16 = 0x60
OP_DUP = 0x76
OP_HASH160 = 0xa9
OP_EQUAL = 0x87
OP_VERIFY = 0x69
OP_EQUALVERIFY = 0x88
OP_CHECKSIG = 0xac
OP_CHECKMULTISIG = 0xae

# --------------------------
# Core Data Structures
# --------------------------

class CScript:
    MAX_SCRIPT_SIZE = 10000
    MAX_STACK_SIZE = 1000
    MAX_OPS_PER_SCRIPT = 201

    def __init__(self, data: bytes = b""):
        if len(data) > self.MAX_SCRIPT_SIZE:
            raise ValueError("Script exceeds maximum size")
        self.data = data
        self.ops = self._parse()

    def _parse(self) -> List[Union[int, bytes]]:
        ops = []
        index = 0
        n = len(self.data)
        
        while index < n:
            opcode = self.data[index]
            index += 1
            
            # Data push operations
            if opcode <= OP_PUSHDATA4:
                size = 0
                if opcode < OP_PUSHDATA1:
                    size = opcode
                elif opcode == OP_PUSHDATA1:
                    size = self.data[index]
                    index += 1
                elif opcode == OP_PUSHDATA2:
                    size = int.from_bytes(self.data[index:index+2], 'little')
                    index += 2
                elif opcode == OP_PUSHDATA4:
                    size = int.from_bytes(self.data[index:index+4], 'little')
                    index += 4
                
                if index + size > n:
                    raise ValueError("Push data exceeds script length")
                
                data_segment = self.data[index:index+size]
                index += size

                ops.append(data_segment)
            else:
                ops.append(opcode)
        
        return ops

    def __add__(self, other: 'CScript') -> 'CScript':
        return CScript(self.data + other.data)

    def serialize(self) -> bytes:
        return self.data

    def __repr__(self) -> str:
        return f"CScript({self.data.hex()})"

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


def verify_script(script_sig: CScript, script_pubkey: CScript, tx: CTransaction, input_index: int) -> bool:
    """
    Bitcoin v0.1 script verification logic
    Returns True if script executes successfully
    """

    # Check individual script sizes
    if (len(script_sig.data) > CScript.MAX_SCRIPT_SIZE or 
        len(script_pubkey.data) > CScript.MAX_SCRIPT_SIZE):
        return False

    stack = []

    # Execute scriptSig (unlocking script)
    if not eval_script(script_sig.ops, stack, tx, input_index, script_pubkey):
        return False

    # Execute scriptPubKey (locking script)
    if not eval_script(script_pubkey.ops, stack, tx, input_index, script_pubkey):
        return False

    # Final stack validation
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
