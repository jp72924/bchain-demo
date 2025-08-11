# Standard library
import socket
import threading
import time
from typing import List

# Blockchain components
from block import CBlock
from block_index import CBlockIndex
from chainstate import ChainState
from transaction import CTransaction

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

                chain = self.node.chain_state.chain
                block_height = self.node.chain_state.chain.tip.height
                utxo_set = self.node.utxo_set
                prev_hash = self.node.chain_state.chain.tip.pprev.hash if chain else bytes(32)

                if validate_block(block, utxo_set, prev_hash, block_height):
                    if block_hash not in self.node.chain_state.chain.block_map:
                        self.node.chain_state.update(block)

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

                chain = self.node.chain_state.chain
                utxo_set = self.node.utxo_set
                block_height = self.node.chain_state.chain.tip.height

                if validate_transaction(tx, utxo_set, block_height):
                    if txid not in self.node.chain_state.mempool:
                        self.node.chain_state.mempool[txid] = tx

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
                    if not (item_hash in self.node.chain_state.chain.block_map):
                        inv_req.append((item_type, item_hash))
                elif item_type == 'MSG_TX':
                    if not (item_hash in self.node.chain_state.mempool):
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
                    if item_hash in self.node.chain_state.chain.block_map:
                        block = self.node.chain_state.chain.block_map.get(item_hash).header
                        response = {
                            'id': block.get_hash().hex(),
                            'type': 'BLOCK',
                            'block': block.serialize().hex(),
                        }
                        # Send direct response through original socket
                        self.node._send_direct_message(response, sock=sock)
                elif item_type == 'MSG_TX':
                    if item_hash in self.node.chain_state.mempool:
                        tx = self.node.chain_state.mempool[item_hash]
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
    def __init__(self, chain_state: ChainState, host: str, port: int, bootstrap_peers: list,  node_id: str):
        super().__init__(host, port, bootstrap_peers, node_id)

        # Blockchain state
        self.chain_state = chain_state
        self.chain_state.register(self.on_chain_update)

        # Register chain message handlers
        self.router.add_handler("BLOCK", BlockHandler(self))
        self.router.add_handler("TX", TxHandler(self))
        self.router.add_handler("INV", InventoryHandler(self))
        self.router.add_handler("GET_DATA", GetDataHandler(self))

    def relay_inventory(self, items: list):
        self.send_message({
            'type': 'INV',
            'count': len(items),
            'inventory': items
        })

    def on_chain_update(self, block):
        tip_hash = self.chain_state.chain.tip.hash.hex()
        self.seen_messages.add(tip_hash)

        item_hash = tip_hash
        item_type = 'MSG_BLOCK'
        inv_data = [(item_type, item_hash)]
        self.relay_inventory(inv_data)


if __name__ == "__main__":
    # Recipient's public key (bytes)
    pubkey1 = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    # pubkey2 = bytes.fromhex("026e21e332324f8634ef47584ef130dd97828e2f626a5f2d7d7a1a33e32a26ac20")

    shared_state = ChainState()

    miner_node = BlockchainNode(
        chain_state=shared_state,
        host='localhost',
        port=8333,
        bootstrap_peers=[],
        node_id="NODE-A"
    )

    isolated_state = ChainState()
    
    regular_node = BlockchainNode(
        chain_state=isolated_state,
        host='localhost',
        port=8334,
        bootstrap_peers=[('127.0.0.1', 8333)],
        node_id="NODE-B"
    )

    time.sleep(10)

    miner = Miner(shared_state, pubkey1)
    miner.run()

    # Keep nodes running
    while True:
        time.sleep(1)
