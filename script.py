from typing import List
from typing import Union

from opcodes import *  # Import all OP constants

# --------------------------
# Core Data Structures
# --------------------------

class CScript:
    MAX_SCRIPT_SIZE = 10000
    MAX_STACK_SIZE = 1000
    MAX_OPS_PER_SCRIPT = 201

    def __init__(self, data: bytes = b''):
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

    def serialize(self) -> bytes:
        return self.data

    @classmethod
    def deserialize(cls, data: bytes) -> 'CScript':
        return cls(data)

    def __add__(self, other: 'CScript') -> 'CScript':
        return CScript(self.data + other.data)

    def __repr__(self) -> str:
        return f"CScript({self.data.hex()})"

    def __hash__(self):
        return hash(self.data)

    def __eq__(self, other):
        if not isinstance(other, CScript):
            # Don't attempt to compare against unrelated types
            return NotImplemented
        return self.data == other.data

# --------------------------
# Helper functions
# --------------------------

def is_op_return(script_pubkey: CScript) -> bool:
    """Check if script is an OP_RETURN scriptPubKey."""
    ops = script_pubkey.ops
    return (len(ops) >= 1 and
            ops[0] == OP_RETURN and
            all(isinstance(op, bytes) for op in ops[1:]))  # All subsequent ops should be data pushes


def is_p2sh(script_pubkey: CScript) -> bool:
    """Check if script is a P2SH scriptPubKey."""
    ops = script_pubkey.ops
    return (len(ops) == 3 and
            ops[0] == OP_HASH160 and
            isinstance(ops[1], bytes) and len(ops[1]) == 20 and
            ops[2] == OP_EQUAL)
