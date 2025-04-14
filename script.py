import io
from hashlib import sha256
import hashlib
from serialize import compact_size

try:
    import ecdsa
except ImportError:
    print("Please install the ecdsa library: pip install ecdsa")
    exit()


class CScript:
    def __init__(self, data: bytes = b""):
        self.data = bytearray(data)

    def __repr__(self):
        return f"CScript({self.data.hex()})"

    def __add__(self, other):
        return CScript(self.data + other.data)

    def __len__(self):
        return len(self.data)

    def push_opcode(self, opcode: int) -> None:
        """Appends a single opcode (e.g., OP_DUP) to the script."""
        self.data.append(opcode)

    def push_data(self, data: bytes) -> None:
        """Appends data with proper push opcodes (e.g., OP_PUSHDATA1)."""
        length = len(data)
        if length < 0x4c:
            self.data.append(length)
        elif length <= 0xff:
            self.data.append(0x4c)
            self.data.append(length)
        elif length <= 0xffff:
            self.data.append(0x4d)
            self.data += length.to_bytes(2, "little")
        else:
            self.data.append(0x4e)
            self.data += length.to_bytes(4, "little")
        self.data += data

    def serialize(self) -> bytes:
        """Serializes the script with compact size prefix."""
        return compact_size(len(self.data)) + bytes(self.data)

    @staticmethod
    def deserialize(stream: io.BytesIO) -> "CScript":
        """Deserializes a script from a byte stream."""
        size = parse_compact_size(stream)
        data = stream.read(size)
        return CScript(data)


class ScriptExecutionError(Exception):
    pass


class ScriptInterpreter:
    OP_DUP = 0x76
    OP_HASH160 = 0xa9
    OP_EQUALVERIFY = 0x88
    OP_CHECKSIG = 0xac

    MAX_SCRIPT_SIZE = 10000  # Max script size in bytes
    MAX_STACK_SIZE = 1000    # Max stack size

    def __init__(self, script: CScript):
        if len(script.data) > self.MAX_SCRIPT_SIZE:
            raise ScriptExecutionError("Script too large")

        self.script = script
        self.stack = []
        self.pc = 0  # Program counter

    def execute(self) -> bool:
        while self.pc < len(self.script.data):
            opcode = self.script.data[self.pc]
            self.pc += 1

            if opcode <= 0x4e:  # Data push
                self._push_data(opcode)
            else:
                if opcode == self.OP_DUP:
                    self._op_dup()
                elif opcode == self.OP_HASH160:
                    self._op_hash160()
                elif opcode == self.OP_EQUALVERIFY:
                    self._op_equalverify()
                elif opcode == self.OP_CHECKSIG:
                    return self._op_checksig()
                else:
                    raise ScriptExecutionError(f"Unsupported opcode: {opcode:02x}")
        return len(self.stack) >= 1 and self.stack[-1] != b"\x00"

    def _push_data(self, opcode: int) -> None:
        if len(self.stack) >= self.MAX_STACK_SIZE:
            raise ScriptExecutionError("Stack overflow")

        # Simplified logic for Bitcoin v0.1 push opcodes
        if opcode < 0x4c:
            size = opcode
        elif opcode == 0x4c:
            size = self.script.data[self.pc]
            self.pc += 1
        elif opcode == 0x4d:
            size = int.from_bytes(self.script.data[self.pc:self.pc+2], "little")
            self.pc += 2
        else:
            size = int.from_bytes(self.script.data[self.pc:self.pc+4], "little")
            self.pc += 4
        data = self.script.data[self.pc:self.pc+size]
        self.stack.append(bytes(data))
        self.pc += size

    def _op_dup(self) -> None:
        if len(self.stack) < 1:
            raise ScriptExecutionError("OP_DUP: Stack underflow")
        self.stack.append(self.stack[-1])

    def _op_hash160(self) -> None:
        if len(self.stack) < 1:
            raise ScriptExecutionError("OP_HASH160: Stack underflow")
        data = self.stack.pop()
        sha = sha256(data).digest()
        ripe = hashlib.new('ripemd160', sha).digest()
        self.stack.append(ripe)

    def _op_equalverify(self) -> None:
        if len(self.stack) < 2:
            raise ScriptExecutionError("OP_EQUALVERIFY: Stack underflow")
        a = self.stack.pop()
        b = self.stack.pop()
        if a != b:
            raise ScriptExecutionError("OP_EQUALVERIFY: Values not equal")

    def _op_checksig(self) -> bool:
        """Verify ECDSA signature using secp256k1"""
        if len(self.stack) < 2:
            raise ScriptExecutionError("OP_CHECKSIG: Stack underflow")

        # Pop pubkey and signature from the stack
        pubkey = self.stack.pop()
        sig = self.stack.pop()

        # Split signature into DER + hash_type (assumes SIGHASH_ALL)
        if len(sig) < 1:
            return False
        hash_type = sig[-1]
        der_sig = sig[:-1]

        # Bitcoin v0.1 only supports SIGHASH_ALL (0x01)
        if hash_type != 0x01:
            return False

        # Validate pubkey format (compressed/uncompressed)
        if len(pubkey) not in (33, 65):
            return False

        try:
            # Parse public key
            vk = ecdsa.VerifyingKey.from_string(pubkey, curve=ecdsa.SECP256k1)

            # Verify signature against the transaction hash (precomputed SHA256d)
            # Note: self.tx_hash must be the double SHA-256 of the transaction data
            vk.verify_digest(
                der_sig,
                self.tx_hash,  # Precomputed transaction hash
                sigdecode=ecdsa.util.sigdecode_der
            )
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False