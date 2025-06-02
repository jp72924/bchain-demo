"""
Bitcoin Script Opcodes (Partial Implementation)

This module defines constants for Bitcoin script opcodes and signature hash flags.
Opcodes follow the Bitcoin Core implementation specifications.

Reference: https://en.bitcoin.it/wiki/Script
"""

# --------------------------
# Signature Hash Flags
# --------------------------
SIGHASH_ALL = 0x01
SIGHASH_NONE = 0x02
SIGHASH_SINGLE = 0x03
SIGHASH_ANYONECANPAY = 0x80

# --------------------------
# Constants and Stack Operations
# --------------------------
OP_0 = 0x00
OP_FALSE = OP_0
OP_TRUE = 0x51
OP_1 = OP_TRUE
OP_2 = 0x52
OP_3 = 0x53
OP_4 = 0x54
OP_5 = 0x55
OP_6 = 0x56
OP_7 = 0x57
OP_8 = 0x58
OP_9 = 0x59
OP_10 = 0x5a
OP_11 = 0x5b
OP_12 = 0x5c
OP_13 = 0x5d
OP_14 = 0x5e
OP_15 = 0x5f
OP_16 = 0x60

OP_DUP = 0x76

# --------------------------
# Data Push Operations
# --------------------------
# Single-byte push operations
OP_PUSHBYTES_1 = 0x01
OP_PUSHBYTES_2 = 0x02
OP_PUSHBYTES_3 = 0x03
OP_PUSHBYTES_4 = 0x04
OP_PUSHBYTES_5 = 0x05
OP_PUSHBYTES_6 = 0x06
OP_PUSHBYTES_7 = 0x07
OP_PUSHBYTES_8 = 0x08
OP_PUSHBYTES_9 = 0x09
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

# Variable-length push operations
OP_PUSHDATA1 = 0x4c  # Push next byte as length
OP_PUSHDATA2 = 0x4d  # Push next 2 bytes as length
OP_PUSHDATA4 = 0x4e  # Push next 4 bytes as length

# --------------------------
# Flow Control and Logic
# --------------------------
OP_VERIFY = 0x69

# --------------------------
# Bitwise and Arithmetic Operations
# --------------------------
OP_EQUAL = 0x87
OP_EQUALVERIFY = 0x88

# --------------------------
# Cryptographic Operations
# --------------------------
OP_CHECKSIG = 0xac
OP_CHECKMULTISIG = 0xae
OP_HASH160 = 0xa9
