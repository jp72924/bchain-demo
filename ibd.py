import time

class IBDState:
    def __init__(self, chain_state):
        self.chain_state = chain_state
        self.active = False
        self.current_height = 0
        self.target_height = 0
        self.active_peer = None
        self.pending_blocks = {}  # hash -> block data
        self.requested_blocks = set()
        self.STALE_THRESHOLD = 30  # seconds
        self.last_request_time = 0

    def should_start_ibd(self):
        """Check if IBD should be initiated"""
        return (self.chain_state.chain.tip is None or 
                self.chain_state.chain.tip.height < self.target_height)

    def start_ibd(self, peer_sock):
        """Begin IBD with a specific peer"""
        if not self.active:
            self.active = True
            self.active_peer = peer_sock
            self._request_next_block()

    def _request_next_block(self):
        """Request the next block in sequence"""
        next_height = self.chain_state.chain.tip.height + 1 if self.chain_state.chain.tip else 0
        locator = self._build_locator()
        
        # Send GETBLOCKS message
        msg = {
            'type': 'GETBLOCKS',
            'locator': [h.hex() for h in locator],
            'hash_stop': bytes(32).hex()
        }
        self.chain_state.node._send_direct_message(msg, self.active_peer)
        self.last_request_time = time.time()

    def _build_locator(self):
        """Build block locator (exponential step back)"""
        locator = []
        step = 1
        current = self.chain_state.chain.tip
        
        while current:
            locator.append(current.hash)
            # Exponential backoff
            for _ in range(min(step, 10)):
                current = current.pprev
                if not current:
                    break
            step *= 2
        
        if not locator:
            locator.append(bytes(32))  # Genesis not found
        return locator

    def process_block(self, block):
        """Process received block during IBD"""
        # Add to pending until we have full chain
        block_hash = block.get_hash()
        self.pending_blocks[block_hash] = block
        
        # Try to connect blocks in order
        self._try_connect_blocks()

    def _try_connect_blocks(self):
        """Attempt to connect pending blocks in height order"""
        next_height = self.chain_state.chain.tip.height + 1 if self.chain_state.chain.tip else 0
        
        while True:
            next_block = self._find_block_at_height(next_height)
            if not next_block:
                break
                
            # Validate and connect block
            try:
                self.chain_state.update(next_block)
                next_height += 1
                # Remove from pending
                del self.pending_blocks[next_block.get_hash()]
            except Exception as e:
                print(f"IBD block connection failed: {e}")
                break

    def _find_block_at_height(self, height):
        """Find block at specific height in pending blocks"""
        for block in self.pending_blocks.values():
            # Find block by comparing to known chain
            prev_index = self.chain_state.chain.block_map.get(block.hashPrevBlock)
            if prev_index and prev_index.height + 1 == height:
                return block
            # Genesis case
            if height == 0 and block.hashPrevBlock == bytes(32):
                return block
        return None
