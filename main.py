# Standard library
import socket
import threading
import time

# Blockchain components
from block import CBlock
from transaction import CTransaction
from utxo import UTXOSet

# Network components
from node import PeerNode

# Operations
from block_validator import validate_block
from tx_validator import validate_transaction
from miner import Miner


class BlockHandler:
        def __init__(self, node: 'BlockchainNode'):
            self.node = node
            
        def __call__(self, message: dict, sock: socket.socket) -> bool:
            try:
                block_data = bytes.fromhex(message['block'])
                block = CBlock.deserialize(block_data)
                block_hash = block.get_hash().hex()
                
                print(f"[{self.node.node_id}] Received block: {block.get_hash()[::-1].hex()}")

                blockchain = self.node.blockchain
                block_height = len(blockchain)
                utxo_set = self.node.utxo_set
                prev_hash = blockchain[-1].get_hash() if blockchain else bytes(32)
                if validate_block(block, utxo_set, prev_hash, block_height):
                # with self.node.sync_lock:
                    if block_hash not in self.node.map_block_index:
                        self.node.blockchain.append(block)
                        self.node.map_block_index.append(block_hash)
                        self.node.utxo_set.update_from_block(block, block_height)
                        # self.node.chain_work += block.calculate_work()

                        # Clear mined transactions from mempool
                        for tx in block.vtx[1:]:  # Skip coinbase
                            txid = tx.get_hash()
                            if txid in self.node.miner.mempool:
                                del self.node.miner.mempool[txid]

                        # Propagate block
                        item_hash = block.get_hash().hex()
                        item_type = 'MSG_BLOCK'
                        inv_data = [(item_type, item_hash)]
                        self.node.relay_inventory(inv_data)
            except Exception as e:
                print(f"Block processing error: {e}")
            return False


class TxHandler:
        def __init__(self, node: 'BlockchainNode'):
            self.node = node
            
        def __call__(self, message: dict, sock: socket.socket) -> bool:
            try:
                tx_data = bytes.fromhex(message['tx'])
                tx = CTransaction.deserialize(tx_data)
                txid = tx.get_hash()

                print(f"[{self.node.node_id}] Received transaction: {txid[::-1].hex()}")

                blockchain = self.node.blockchain
                utxo_set = self.node.utxo_set
                block_height = len(blockchain)
                if validate_transaction(tx, utxo_set, block_height):
                    if txid not in self.node.miner.mempool:
                        self.node.miner.mempool[txid] = tx

                        # Propagate transaction
                        item_hash = tx.get_hash().hex()
                        item_type = 'MSG_TX'
                        inv_data = [(item_type, item_hash)]
                        self.node.relay_inventory(inv_data)
            except Exception as e:
                print(f"Transaction processing error: {e}")
            return False


class InventoryHandler:
    def __init__(self, node: 'BlockchainNode'):
        self.node = node

    def __call__(self, message: dict, sock: socket.socket) -> bool:
        try:
            inv_data = message['inventory']
            inv_req = []
            for item_type, item_hash in inv_data:
                if item_type == 'MSG_BLOCK':
                    if not (item_hash in self.node.map_block_index):
                        inv_req.append((item_type, item_hash))
                elif item_type == 'MSG_TX':
                    if not (item_hash in self.node.miner.mempool):
                        inv_req.append((item_type, item_hash))

            if inv_req:
                response = {
                    'type': 'GET_DATA',
                    'inventory': inv_req
                }
                # Send direct response through original socket
                # self.node._send_direct_message(response, sock=sock)
                self.node.send_message(response)
        except Exception as e:
            print(f"Inventory processing error: {e}")
        return False


class GetDataHandler:
    def __init__(self, node: 'BlockchainNode'):
        self.node = node

    def __call__(self, message: dict, sock: socket.socket) -> bool:
        try:
            inv_data = message['inventory']
            for item_type, item_hash in inv_data:
                if item_type == 'MSG_BLOCK':
                    if item_hash in self.node.map_block_index:
                        height = self.node.map_block_index.index(item_hash)
                        block = self.node.blockchain[height]
                        response = {
                            'id': block.get_hash().hex(),
                            'type': 'BLOCK',
                            'block': block.serialize().hex(),
                        }
                        # Send direct response through original socket
                        self.node._send_direct_message(response, sock=sock)
                elif item_type == 'MSG_TX':
                    if item_hash in self.node.miner.mempool:
                        tx = self.node.miner.mempool[item_hash]
                        response = {
                            'id': tx.get_hash().hex(),
                            'type': 'TX',
                            'tx': tx.serialize().hex(),
                        }
                        # Send direct response through original socket
                        self.node._send_direct_message(response, sock=sock)
        except Exception as e:
            print(f"Inventory processing error: {e}")
        return False


class BlockchainNode(PeerNode):
    def __init__(self, host: str, port: int, bootstrap_peers: list, pubkey: bytes,  node_id: str = None):
        super().__init__(host, port, bootstrap_peers, node_id)

        # Blockchain state
        self.blockchain: List[CBlock] = []
        self.utxo_set = UTXOSet()
        # self.mempool: Dict[bytes, CTransaction] = {}
        self.map_block_index = []
        # self.chain_work = 0

        # Mining setup
        self.miner = Miner(pubkey)
        self.miner.on_block_mine = self.on_block_mine
        self.miner_thread = None
        
        # Register blockchain message handlers
        self.router.add_handler("BLOCK", BlockHandler(self))
        self.router.add_handler("TX", TxHandler(self))
        self.router.add_handler("INV", InventoryHandler(self))
        self.router.add_handler("GET_DATA", GetDataHandler(self))

    def broadcast_block(self, block: CBlock):
        self.send_message({
            'id': block.get_hash().hex(),
            'type': 'BLOCK',
            'block': block.serialize().hex(),
        })

    def broadcast_transaction(self, tx: CTransaction):
        self.send_message({
            'id': tx.get_hash().hex(),
            'type': 'TX',
            'tx': tx.serialize().hex(),
        })

    def relay_inventory(self, items: list):
        self.send_message({
            'type': 'INV',
            'count': len(items),
            'inventory': items
        })

    def run(self):
        self.miner_thread = threading.Thread(target=self.miner.run)
        self.miner_thread.start()

    def on_block_mine(self):
        head = self.miner.blockchain[-1]
        head_hash = head.get_hash().hex()

        self.seen_messages.add(head_hash)
        self.blockchain.append(head)
        self.map_block_index.append(head_hash)

        # UTXO update and mempool cleanup
        self.utxo_set.update_from_block(head, len(self.blockchain))
        for tx in head.vtx[1:]:
            txid = tx.get_hash()
            if txid in self.miner.mempool:
                del self.miner.mempool[txid]

        item_hash = head.get_hash().hex()
        item_type = 'MSG_BLOCK'
        inv_data = [(item_type, item_hash)]
        self.relay_inventory(inv_data)


if __name__ == "__main__":
    # Recipient's public key (bytes)
    pubkey1 = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    pubkey2 = bytes.fromhex("026e21e332324f8634ef47584ef130dd97828e2f626a5f2d7d7a1a33e32a26ac20")

    # Example usage
    miner_node = BlockchainNode(
        host='localhost',
        port=8333,
        bootstrap_peers=[],
        pubkey=pubkey1,
        node_id="NODE-A"
    )
    
    regular_node = BlockchainNode(
        host='localhost',
        port=8334,
        bootstrap_peers=[('127.0.0.1', 8333)],
        pubkey=pubkey2,
        node_id="NODE-B"
    )
    # regular_node.run()
    time.sleep(5)
    miner_node.run()

    # Keep nodes running
    while True:
        time.sleep(1)
