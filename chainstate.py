from threading import RLock

from block_index import CChain
from utxo import UTXOSet


class ChainState:
    def __init__(self):
        self._chain = CChain()
        self._utxo_set = UTXOSet()
        self._mempool = {}

        self._state_lock = RLock()

        # Store callbacks to call when chain is updated
        self._callbacks = []

    @property
    def chain(self):
        with self._state_lock:
            return self._chain

    @property
    def utxo_set(self):
        with self._state_lock:
            return self._utxo_set

    @property
    def mempool(self):
        with self._state_lock:
            return self._mempool

    def update(self, block):
        """Adds the newly mined block to the blockchain index"""
        try:
            with self._state_lock:
                new_index = self._chain.add_block(block)

                # Update UTXO set based on new chain state
                if self._chain.tip == new_index:
                    # Simple extension case
                    self._utxo_set.update_from_block(block, new_index.height)
                else:
                    # Handle chain reorganization
                    self._handle_chain_reorg(new_index)

                # Clear mined transactions from mempool
                for tx in block.vtx[1:]:  # Skip coinbase
                    txid = tx.get_hash()
                    if txid in self._mempool:
                        del self._mempool[txid]

            # Notify all listeners outside of the main lock to avoid deadlocks
            self._notify(block)

        except ValueError as e:
            print(f"Block addition failed: {e}")

    def _handle_chain_reorg(self, new_tip):
        """Update UTXO set during chain reorganization"""
        # 1. Find fork point
        fork_block = self._chain._find_fork_point(self._chain.tip, new_tip)

        # 2. Disconnect blocks from old chain
        current = self._chain.tip
        while current != fork_block:
            self._utxo_set.disconnect_block(current.header)
            current = current.pprev

        # 3. Connect blocks from new chain
        blocks_to_connect = []
        current = new_tip
        while current != fork_block:
            blocks_to_connect.append(current)
            current = current.pprev
        blocks_to_connect.reverse()  # Apply in order

        for block in blocks_to_connect:
            self._utxo_set.update_from_block(block.header, block.height)

    def register(self, func):
        """Register a function to be called when the chain state updates."""
        with self._state_lock:
            self._callbacks.append(func)

    def _notify(self, block):
        """Call all registered callbacks, passing the new block."""
        for func in self._callbacks:
            try:
                func(block)
            except Exception as e:
                print(f"Callback raised exception: {e}")
