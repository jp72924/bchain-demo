import time

from block import CBlock, CBlockHeader, create_coinbase_transaction
from script import CScript
from script_utils import ScriptBuilder
from transaction import CTransaction, CTxIn, CTxOut, COutPoint

# Import the blockchain index system
from block_index import Chain

# --------------------------
# Example Usage
# --------------------------

if __name__ == "__main__":
    def create_dummy_transaction():
        """Create a simple transaction for block inclusion"""
        return CTransaction(
            vin=[CTxIn(prevout=COutPoint(hash=bytes(32), n=0), scriptSig=CScript(b""))],
            vout=[CTxOut(nValue=500000000, scriptPubKey=CScript(b""))]
        )

    # Initialize blockchain
    blockchain = Chain()

    # Create miner public key (dummy)
    pubkey_bytes = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    p2pkh_script = ScriptBuilder.p2pkh_script_pubkey(pubkey_bytes)

    print("===== Creating Genesis Block =====")
    # Create and mine genesis block
    genesis_block = CBlock(
        header=CBlockHeader(
            nVersion=1,
            hashPrevBlock=bytes(32),
            hashMerkleRoot=bytes(32),
            nTime=int(time.time()),
            nBits=0x1f00ffff,  # Bitcoin mainnet difficulty
            nNonce=0
        ),
        vtx=[]
    )

    # Create coinbase transaction for genesis
    genesis_coinbase = create_coinbase_transaction(
        coinbase_data=CScript(b""),
        miner_reward=5000000000,
        script_pubkey=p2pkh_script
    )
    genesis_block.vtx = [genesis_coinbase]

    # Mine the genesis block
    print("Mining genesis block...")
    genesis_block.mine(max_attempts=100)
    print(f"Genesis mined! Hash: {genesis_block.get_hash().hex()}")

    # Add to blockchain
    genesis_index = blockchain.add_block(genesis_block)
    if not genesis_index:
        raise RuntimeError("Failed to add genesis block")
    print("Genesis added to blockchain\n")

    # Print current chain state
    blockchain.print_main_chain()
    blockchain.print_tree()

    print("\n===== Creating Block 1 =====")
    # Create block 1 building on genesis
    block1 = CBlock(
        header=CBlockHeader(
            nVersion=1,
            hashPrevBlock=genesis_block.get_hash(),
            hashMerkleRoot=bytes(32),
            nTime=int(time.time()),
            nBits=0x1f00ffff,
            nNonce=0
        ),
        vtx=[]
    )

    # Create coinbase and add a transaction
    block1_coinbase = create_coinbase_transaction(
        coinbase_data=CScript(b""),
        miner_reward=5000000000,
        script_pubkey=p2pkh_script
    )
    block1.vtx = [block1_coinbase, create_dummy_transaction()]

    # Mine block 1
    print("Mining block 1...")
    block1.mine()
    print(f"Block 1 mined! Hash: {block1.get_hash().hex()}")

    # Add to blockchain
    block1_index = blockchain.add_block(block1)
    if not block1_index:
        raise RuntimeError("Failed to add block 1")
    print("Block 1 added to blockchain\n")

    # Print current chain state
    blockchain.print_main_chain()
    blockchain.print_tree()

    print("\n===== Creating Fork (Block 2A) =====")
    # Create alternative block 2 building on genesis
    block2a = CBlock(
        header=CBlockHeader(
            nVersion=1,
            hashPrevBlock=genesis_block.get_hash(),
            hashMerkleRoot=bytes(32),
            nTime=int(time.time()) + 60,  # Different timestamp
            nBits=0x1f00ffff,
            nNonce=0
        ),
        vtx=[]
    )

    block2a_coinbase = create_coinbase_transaction(
        coinbase_data=CScript(b""),
        miner_reward=5000000000,
        script_pubkey=p2pkh_script
    )
    block2a.vtx = [block2a_coinbase]

    # Mine block 2A
    print("Mining block 2A...")
    block2a.mine()
    print(f"Block 2A mined! Hash: {block2a.get_hash().hex()}")

    # Add to blockchain - creates fork
    block2a_index = blockchain.add_block(block2a)
    if not block2a_index:
        raise RuntimeError("Failed to add block 2A")
    print("Block 2A added to blockchain (fork created)\n")

    # Print chain state showing fork
    blockchain.print_main_chain()
    blockchain.print_tree()

    print("\n===== Extending Fork (Block 3A) =====")
    # Create block 3A building on the fork
    block3a = CBlock(
        header=CBlockHeader(
            nVersion=1,
            hashPrevBlock=block2a.get_hash(),
            hashMerkleRoot=bytes(32),
            nTime=int(time.time()),
            nBits=0x1f00ffff,
            nNonce=0
        ),
        vtx=[]
    )

    block3a_coinbase = create_coinbase_transaction(
        coinbase_data=CScript(b""),
        miner_reward=5000000000,
        script_pubkey=p2pkh_script
    )
    block3a.vtx = [block3a_coinbase]

    # Mine block 3A
    print("Mining block 3A...")
    block3a.mine()
    print(f"Block 3A mined! Hash: {block3a.get_hash().hex()}")

    # Add to blockchain - should cause reorganization
    block3a_index = blockchain.add_block(block3a)
    if not block3a_index:
        raise RuntimeError("Failed to add block 3A")
    print("Block 3A added to blockchain (chain reorganization occurred)\n")

    # Print chain state showing new longest chain
    blockchain.print_main_chain()
    blockchain.print_tree()