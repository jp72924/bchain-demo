from crypto import hash160
from script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, OP_1, OP_CHECKMULTISIG

class ScriptBuilder:
    @staticmethod
    def _push_data(data: bytes) -> bytes:
        """Generate proper push opcodes for data"""
        length = len(data)
        if length == 0:
            return bytes([OP_0])
        elif length <= 75:
            return bytes([length]) + data
        elif length <= 0xff:
            return bytes([OP_PUSHDATA1, length]) + data
        elif length <= 0xffff:
            return bytes([OP_PUSHDATA2]) + length.to_bytes(2, 'little') + data
        else:
            return bytes([OP_PUSHDATA4]) + length.to_bytes(4, 'little') + data

    @classmethod
    def p2pk(cls, pubkey: bytes) -> CScript:
        """Build Pay-to-Public-Key (P2PK) script"""
        if len(pubkey) not in {33, 65}:
            raise ValueError("Invalid public key length (must be 33/65 bytes)")
        
        push_pubkey = cls._push_data(pubkey)
        return CScript(push_pubkey + bytes([OP_CHECKSIG]))

    @classmethod
    def p2pkh(cls, pubkey_or_hash: bytes, *, is_hash: bool = False) -> CScript:
        """Build Pay-to-Public-Key-Hash (P2PKH) script"""
        if is_hash:
            pubkey_hash = pubkey_or_hash
            if len(pubkey_hash) != 20:
                raise ValueError("P2PKH requires 20-byte hash")
        else:
            if len(pubkey_or_hash) not in {33, 65}:
                raise ValueError("Invalid public key length (must be 33/65 bytes)")
            pubkey_hash = hash160(pubkey_or_hash)

        return CScript(
            bytes([OP_DUP, OP_HASH160]) +
            cls._push_data(pubkey_hash) +
            bytes([OP_EQUALVERIFY, OP_CHECKSIG])
        )

    @classmethod
    def multisig(cls, m: int, pubkeys: list[bytes]) -> CScript:
        """Build M-of-N multisig script (for extension example)"""
        if not 1 <= m <= 16:
            raise ValueError("m must be between 1-16")
        if len(pubkeys) < m or len(pubkeys) > 16:
            raise ValueError("Invalid number of pubkeys")

        ops = [bytes([OP_1 + m - 1])]  # Convert to OP_1-OP_16
        for pk in pubkeys:
            ops.append(cls._push_data(pk))
        ops.append(bytes([OP_1 + len(pubkeys) - 1, OP_CHECKMULTISIG]))
        
        return CScript(b''.join(ops))


if __name__ == '__main__':
    # For 33-byte compressed public key
    pubkey_bytes = bytes.fromhex("026e21e332324f8634ef47584ef130dd97828e2f626a5f2d7d7a1a33e32a26ac20")
    p2pk_script = ScriptBuilder.p2pk(pubkey_bytes)
    # Result: <33-byte push> <pubkey> OP_CHECKSIG

    # From public key (auto-hashes)
    p2pkh_script = ScriptBuilder.p2pkh(pubkey_bytes)
    # From existing hash (20-byte)
    pubkey_hash = hash160(pubkey_bytes)
    _p2pkh_script = ScriptBuilder.p2pkh(pubkey_hash, is_hash=True)
    # Result: OP_DUP OP_HASH160 <20-byte push> <hash> OP_EQUALVERIFY OP_CHECKSIG

    print(f"P2PK: {p2pk_script}")
    print(f"P2PKH: {p2pkh_script}")
    print(f"P2PKH (auto-hash): {_p2pkh_script}")