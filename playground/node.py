import hashlib
import time

class Node:
    BLOCK_REWARD = 6.25  # Block subsidy in BTC
    DIFFICULTY_TARGET = "00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"  # Simplified target

    def __init__(self, miner_address):
        """Initializes the Node with a blockchain and miner address."""
        self.blockchain = []
        self.miner_address = miner_address

    def create_coinbase_transaction(self):
        """Creates a coinbase transaction paying the miner."""
        return {
            "to": self.miner_address,
            "amount": Node.BLOCK_REWARD,
            "timestamp": time.time()
        }

    def create_candidate_block(self, previous_hash):
        """Creates a candidate block with a coinbase transaction."""
        coinbase_tx = self.create_coinbase_transaction()
        return {
            "previous_hash": previous_hash,
            "transactions": [coinbase_tx],
            "nonce": 0,
            "timestamp": time.time()
        }

    def calculate_block_hash(self, block):
        """Calculates the hash of a block header."""
        block_header = (
            str(block["previous_hash"])
            + str(block["transactions"])
            + str(block["timestamp"])
            + str(block["nonce"])
        )
        return hashlib.sha256(block_header.encode()).hexdigest()

    def perform_proof_of_work(self, block):
        """Performs Proof of Work to find a valid block hash."""
        print("Starting Proof of Work...")
        while True:
            block_hash = self.calculate_block_hash(block)
            if block_hash < Node.DIFFICULTY_TARGET:
                print("Block mined!", block_hash)
                return block_hash
            block["nonce"] += 1

    def update_local_state(self, block):
        """Adds the newly mined block to the blockchain."""
        self.blockchain.append(block)
        print("Block added to the blockchain.")

    def create_genesis_block(self):
        """Creates and adds the genesis block to the blockchain."""
        genesis_block = {
            "previous_hash": "0" * 64,
            "transactions": [self.create_coinbase_transaction()],
            "nonce": 0,
            "timestamp": time.time()
        }
        genesis_block["hash"] = self.calculate_block_hash(genesis_block)
        self.blockchain.append(genesis_block)
        print("Genesis block created.")

    def mine_new_block(self):
        """Creates and mines a new block, then adds it to the blockchain."""
        previous_hash = self.blockchain[-1]["hash"]
        candidate_block = self.create_candidate_block(previous_hash)
        valid_hash = self.perform_proof_of_work(candidate_block)
        candidate_block["hash"] = valid_hash
        self.update_local_state(candidate_block)

    def run(self):
        """Continuously mines new blocks."""
        if not self.blockchain:
            self.create_genesis_block()
        while True:
            self.mine_new_block()

    def display_blockchain(self):
        """Prints the blockchain."""
        for i, block in enumerate(self.blockchain):
            print(f"Block {i}: {block}")

# Main function to simulate a mining node
def mining_node_simulation():
    miner_address = "miner1"
    node = Node(miner_address)
    node.run()

# Run the mining node simulation
if __name__ == "__main__":
    mining_node_simulation()
