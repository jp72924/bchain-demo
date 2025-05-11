from crypto import hash160
from script import CScript, OP_0, OP_1, OP_PUSHDATA1, OP_PUSHDATA2, OP_PUSHDATA4, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, OP_CHECKMULTISIG, OP_EQUAL


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
    def p2pk_script_pubkey(cls, pubkey: bytes) -> CScript:
        """Build Pay-to-Public-Key (P2PK) script"""
        if len(pubkey) not in {33, 65}:
            raise ValueError("Invalid public key length (must be 33/65 bytes)")
        
        push_pubkey = cls._push_data(pubkey)
        return CScript(push_pubkey + bytes([OP_CHECKSIG]))

    @classmethod
    def p2pkh_script_pubkey(cls, pubkey_or_hash: bytes, *, is_hash: bool = False) -> CScript:
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
    def p2ms_script_pubkey(cls, m: int, pubkeys: list[bytes]) -> CScript:
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
    def p2sh_script_pubkey(cls, redeem_script: CScript) -> CScript:
        """Build Pay-to-Script-Hash (P2SH) script"""
        script_hash = hash160(redeem_script.data)
        return CScript(
            bytes([OP_HASH160]) +
            cls._push_data(script_hash) +
            bytes([OP_EQUAL])
        )

    @classmethod
    def p2pk_script_sig(cls, signature: bytes) -> CScript:
        """Build scriptSig for P2PK (single signature)"""
        return CScript(cls._push_data(signature))

    @classmethod
    def p2pkh_script_sig(cls, signature: bytes, pubkey: bytes) -> CScript:
        """Build scriptSig for P2PKH (signature + pubkey)"""
        return CScript(
            cls._push_data(signature) + 
            cls._push_data(pubkey)
        )

    @classmethod
    def p2ms_script_sig(cls, *signatures: bytes) -> CScript:
        """Build scriptSig for P2MS (dummy OP_0 + signatures)"""
        script = bytes([OP_0])  # Required for multisig off-by-one bug
        for sig in signatures:
            script += cls._push_data(sig)
        return CScript(script)

    @classmethod
    def p2sh_script_sig(cls, redeem_script: CScript, *unlocking_data: bytes) -> CScript:
        """Build scriptSig for P2SH (unlocking data + redeem script)"""
        script = b''
        for data in unlocking_data:
            script += cls._push_data(data)
        script += cls._push_data(redeem_script.data)
        return CScript(script)
