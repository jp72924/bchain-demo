from typing import List, Dict, Optional


class CBlockIndex:
    """
    Represents a single block in the blockchain.
    It contains data and pointers for navigating the tree and the main chain.
    """
    __slots__ = ('hash', 'height', 'pprev', 'pnext', 'children')
    
    def __init__(self, hash: str, parent: Optional['CBlockIndex'] = None):
        """
        Initialize a new block.
        
        Args:
            hash: Cryptographic hash of this block
            parent (optional): Parent CBlockIndex reference (None for genesis)
        """
        self.hash = hash     # A unique identifier for the block
        self.children = []   # A list of all potential next blocks
        self.pprev = parent  # Pointer to the previous block in the chain
        self.pnext = None    # Pointer to the next block in the longest chain
        self.height = 0      # The height of the block from the genesis block
        
        if parent:
            self.height = parent.height + 1
            parent.children.append(self)

    def __repr__(self):
        """Provides a string representation of the block for easy debugging."""
        return f"CBlockIndex(hash={self.hash[:8]}..., height={self.height})"


class Chain:
    """
    Maintains a tree-shaped blockchain with efficient longest-chain tracking.
    Implements Bitcoin-style chain reorganization logic.
    
    Attributes:
        genesis (CBlockIndex): First block in the chain
        tip (CBlockIndex): Current endpoint of the longest valid chain
        block_map (Dict[str, CBlockIndex]): Hash-to-block lookup dictionary
    """
    def __init__(self):
        """Initialize an empty blockchain."""
        self.genesis = None
        self.tip = None
        self.block_map = {}
    
    def add_block(self, block_hash: str, parent_hash: Optional[str] = None) -> CBlockIndex:
        """
        Add a new block to the blockchain as a child of the specified parent.
        
        Args:
            block_hash: Cryptographic hash of the new block
            parent_hash: Hash of the parent block (None for genesis)
            
        Returns:
            The created CBlockIndex object
            
        Raises:
            ValueError: For invalid genesis block or missing parent
        """
        # Genesis block creation
        if not self.genesis:
            if parent_hash is not None:
                raise ValueError("Genesis block must have no parent")
            self.genesis = CBlockIndex(block_hash)
            self.tip = self.genesis
            self.block_map[block_hash] = self.genesis
            return self.genesis
        
        # Validate parent exists
        if parent_hash not in self.block_map:
            raise ValueError(f"Parent block {parent_hash} not found")
        
        parent = self.block_map[parent_hash]
        new_block = CBlockIndex(block_hash, parent)
        self.block_map[block_hash] = new_block

        # Update longest chain if new block extends it
        if new_block.height > self.tip.height:
            self._update_main_chain(new_block)
            
        return new_block
    
    def _update_main_chain(self, new_tip: CBlockIndex):
        """
        Update chain pointers after discovering a new longest chain.
        
        Args:
            new_tip: The new endpoint of the longest chain
        """
        old_tip = self.tip
        self.tip = new_tip
        
        # Find fork point between old and new chains
        fork_block = self._find_fork_point(old_tip, new_tip)
        
        # Invalidate old chain (set pnext to None)
        self._invalidate_chain_segment(old_tip, fork_block)
        
        # Build new chain path
        self._rebuild_chain_path(fork_block, new_tip)
    
    def _find_fork_point(self, block_a: CBlockIndex, block_b: CBlockIndex) -> CBlockIndex:
        """
        Find the last common ancestor of two chain tips.
        
        Args:
            block_a: First chain tip
            block_b: Second chain tip
            
        Returns:
            The fork point CBlockIndex where the chains diverge
        """
        a, b = block_a, block_b
        while a.height > b.height:
            a = a.pprev
        while b.height > a.height:
            b = b.pprev
        while a != b:
            a = a.pprev
            b = b.pprev
        return a
    
    def _invalidate_chain_segment(self, from_block: CBlockIndex, to_block: CBlockIndex):
        """
        Clear pnext pointers along a chain segment (exclusive of to_block).
        
        Args:
            from_block: Starting point (tip of segment)
            to_block: Endpoint (not cleared)
        """
        current = from_block
        while current != to_block:
            current.pnext = None
            current = current.pprev
    
    def _rebuild_chain_path(self, fork_block: CBlockIndex, new_tip: CBlockIndex):
        """
        Reconstruct pnext pointers from fork point to new tip.
        
        Args:
            fork_block: Where the new chain branches
            new_tip: Endpoint of the new chain
        """
        # Build path from fork to tip
        path = []
        current = new_tip
        while current != fork_block:
            path.append(current)
            current = current.pprev
        path.append(fork_block)
        path.reverse()  # Order: fork_block -> ... -> new_tip
        
        # Set pnext pointers
        for i in range(len(path) - 1):
            path[i].pnext = path[i+1]
        path[-1].pnext = None  # Tip has no next
    
    def get_longest_chain(self) -> list[CBlockIndex]:
        """Return all blocks in the current longest chain from genesis to tip."""
        chain = []
        current = self.genesis
        while current:
            chain.append(current)
            current = current.pnext
        return chain

    def print_main_chain(self):
        """Prints the main (longest) chain from genesis to the latest block"""
        print("\n=== Main Chain ===")
        current = self.genesis
        while current is not None:
            print(f"  -> {current}")
            # Follow the pnext pointer, which only exists for the main chain
            current = current.pnext
        print("==================\n")

    def print_tree(self, block=None, prefix="", is_last=True):
        """Prints a visual representation of the entire block tree"""
        if block is None:
            print("\n=== CBlockIndex Tree ===")
            block = self.genesis

        # Visual decorators for the tree structure
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{block}")

        # Adjust prefix for children
        child_prefix = prefix + ("    " if is_last else "│   ")
        
        for i, child in enumerate(block.children):
            is_child_last = (i == len(block.children) - 1)
            self.print_tree(child, child_prefix, is_child_last)
        
        if block == self.genesis:
             print("================\n")

# Example Usage
if __name__ == "__main__":
    chain = Chain()
    
    # Build blockchain (genesis -> A -> B -> C)
    chain.add_block("0")          # Genesis
    chain.add_block("A", "0")
    chain.add_block("B", "A")
    chain.add_block("C", "B")     # Main chain: 0-A-B-C
    
    # Create fork: 0 -> D -> E
    chain.add_block("D", "0")
    chain.add_block("E", "D")
    
    # Extend fork to become longest chain: 0 -> D -> E -> F -> G
    chain.add_block("F", "E")
    chain.add_block("G", "F")     # New main chain: 0-D-E-F-G
    
    # Print results
    chain.print_tree()
    chain.print_main_chain()