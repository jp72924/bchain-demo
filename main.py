# Standard library
import socket
import threading
import time
from typing import List

# Blockchain components
from block import CBlock
from block_index import CBlockIndex
from chainstate import ChainState
from ibd import IBDState
from transaction import CTransaction

# Network components
from node import PeerNode
from rpc_server import start_rpc_server

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
                utxo_set = self.node.chain_state.utxo_set

                block_height = 0
                prev_hash = bytes(32)
                if chain.tip:
                    block_height = self.node.chain_state.chain.tip.height + 1
                    prev_hash = self.node.chain_state.chain.tip.hash

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
                    block_hash = bytes.fromhex(item_hash)
                    if block_hash in self.node.chain_state.chain.block_map:
                        block = self.node.chain_state.chain.block_map.get(block_hash).header
                        response = {
                            'id': block.get_hash().hex(),
                            'type': 'BLOCK',
                            'block': block.serialize().hex(),
                        }
                        # Send direct response through original socket
                        self.node._send_direct_message(response, sock=sock)
                elif item_type == 'MSG_TX':
                    tx_hash = bytes.fromhex(item_hash)
                    if tx_hash in self.node.chain_state.mempool:
                        tx = self.node.chain_state.mempool[tx_hash]
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


class GetBlocksHandler:
    def __init__(self, node: 'BlockchainNode'):
        self.node = node

    def __call__(self, message: dict, sock: socket.socket) -> bool:
        """Handle GETBLOCKS request (peer asking for block inventory)"""
        locator = [bytes.fromhex(h) for h in message['locator']]
        hash_stop = bytes.fromhex(message['hash_stop'])

        # Find last common block
        common_block = self._find_common_block(locator)

        # Send inventory of next blocks
        inventory = []
        current = common_block.pnext if common_block else self.node.chain_state.chain.genesis
        max_blocks = 500  # Limit response size

        while current and max_blocks > 0:
            if current.hash == hash_stop:
                break
            inventory.append(('MSG_BLOCK', current.hash.hex()))
            current = current.pnext
            max_blocks -= 1

        # Send INV message
        self.node.send_message({
            'type': 'INV',
            'inventory': inventory
        })
        return False

    def _find_common_block(self, locator):
        """Find last common block from locator"""
        for block_hash in locator:
            if block_hash in self.node.chain_state.chain.block_map:
                return self.node.chain_state.chain.block_map[block_hash]
        return None


class IBDBlockHandler(BlockHandler):
    """Special handler for blocks during IBD"""
    def __call__(self, message: dict, sock: socket.socket) -> bool:
        try:
            block_data = bytes.fromhex(message['block'])
            block = CBlock.deserialize(block_data)

            # Process only if from IBD peer
            if self.node.ibd.active and sock == self.node.ibd.active_peer:
                self.node.ibd.process_block(block)
                return False
            else:
                # Normal block processing
                return super().__call__(message, sock)
        except Exception as e:
            print(f"IBD block processing error: {e}")
            return False


class BlockchainNode(PeerNode):
    def __init__(self, chain_state: ChainState, host: str, port: int, bootstrap_peers: list,  node_id: str):
        super().__init__(host, port, bootstrap_peers, node_id)

        # Blockchain state
        self.chain_state = chain_state
        self.chain_state.register(self.on_chain_update)
        self.chain_state.node = self  # Set back-reference
        self.ibd = IBDState(chain_state)

        # Register additional handlers
        self.router.add_handler("GETBLOCKS", GetBlocksHandler(self))

        # Register chain message handlers
        self.router.add_handler("BLOCK", IBDBlockHandler(self))
        self.router.add_handler("TX", TxHandler(self))
        self.router.add_handler("INV", InventoryHandler(self))
        self.router.add_handler("GET_DATA", GetDataHandler(self))

    def relay_inventory(self, items: list):
        self.send_message({
            'type': 'INV',
            'count': len(items),
            'inventory': items
        })

    def on_peer_connected(self, sock, address, connection_type):
        """Override peer connection handler"""
        # super().on_peer_connected(sock, address, connection_type)

        # Start IBD if needed
        if self.ibd.should_start_ibd() and not self.ibd.active:
            self.ibd.start_ibd(sock)

    def on_chain_update(self, block):
        tip_hash = self.chain_state.chain.tip.hash.hex()
        self.seen_messages.add(tip_hash)

        item_hash = tip_hash
        item_type = 'MSG_BLOCK'
        inv_data = [(item_type, item_hash)]
        self.relay_inventory(inv_data)

        # Check if we should request next block
        if self.ibd.active:
            # Check for timeout
            if time.time() - self.ibd.last_request_time > self.ibd.STALE_THRESHOLD:
                print("IBD request timeout, retrying...")
                self.ibd._request_next_block()

            # Check if we've reached target height
            if (self.chain_state.chain.tip and
                self.chain_state.chain.tip.height >= self.ibd.target_height):
                print(f"IBD completed at height {self.chain_state.chain.tip.height}")
                self.ibd.active = False


if __name__ == "__main__":
    # Recipient's public key (bytes)
    pubkey1 = bytes.fromhex("02d8fdf598efc46d1dc0ca8582dc29b3bd28060fc27954a98851db62c55d6b48c5")
    # pubkey2 = bytes.fromhex("026e21e332324f8634ef47584ef130dd97828e2f626a5f2d7d7a1a33e32a26ac20")

    shared_state = ChainState()
    isolated_state = ChainState()

    miner_node = BlockchainNode(
        chain_state=shared_state,
        host='localhost',
        port=8333,
        bootstrap_peers=[],
        node_id="NODE-A"
    )

    # Start RPC server for miner node
    rpc_server = start_rpc_server(shared_state, miner_node, '127.0.0.1', 8332)

    time.sleep(5)

    miner = Miner(shared_state, pubkey1)
    for x in range(5):
        block = miner.mine_new_block()
        shared_state.update(block)
        # isolated_state.update(block) if x <= 2 else ...

    time.sleep(5)

    regular_node = BlockchainNode(
        chain_state=isolated_state,
        host='localhost',
        port=8334,
        bootstrap_peers=[('127.0.0.1', 8333)],
        node_id="NODE-B"
    )

    # Start RPC server for regular node on different port
    regular_rpc_server = start_rpc_server(isolated_state, regular_node, '127.0.0.1', 8331)

    # Keep nodes running
    try:
        while True:
            time.sleep(5)
            # isolated_state.chain.print_main_chain()
    except KeyboardInterrupt:
        print("Shutting down nodes...")
        miner_node.shutdown()
        regular_node.shutdown()
        rpc_server.stop()
        regular_rpc_server.stop()
