from crypto import hash160
from script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, OP_1, OP_CHECKMULTISIG, OP_EQUAL, OP_0


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
    def p2ms(cls, m: int, pubkeys: list[bytes]) -> CScript:
        """Build M-of-N multisig script"""
        if not 1 <= m <= 16:
            raise ValueError("m must be between 1-16")
        if len(pubkeys) < m or len(pubkeys) > 16:
            raise ValueError("Invalid number of pubkeys (1-16)")

        script = bytes([OP_1 + m - 1])  # Convert to OP_1-OP_16
        for pk in pubkeys:
            script += cls._push_data(pk)
        script += bytes([OP_1 + len(pubkeys) - 1, OP_CHECKMULTISIG])
        
        return CScript(script)

    @classmethod
    def p2sh(cls, redeem_script: CScript) -> CScript:
        """Build Pay-to-Script-Hash (P2SH) script"""
        script_hash = hash160(redeem_script.data)
        return CScript(
            bytes([OP_HASH160]) +
            cls._push_data(script_hash) +
            bytes([OP_EQUAL])
        )


if __name__ == '__main__':
    # Example usage
    from ecdsa import SigningKey, SECP256k1
    
    # Generate test keys
    sk1 = SigningKey.generate(curve=SECP256k1)
    pk1 = sk1.get_verifying_key().to_string("compressed")
    
    sk2 = SigningKey.generate(curve=SECP256k1)
    pk2 = sk2.get_verifying_key().to_string("compressed")
    
    # P2SH example with 2-of-2 multisig
    redeem_script = ScriptBuilder.p2ms(2, [pk1, pk2])
    p2sh_script = ScriptBuilder.p2sh(redeem_script)
    print(f"Redeem script: {redeem_script}")
    print(f"P2SH scriptPubKey: {p2sh_script}")
