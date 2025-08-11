from typing import List, Dict, Optional, Tuple

from bignum import set_compact
from block import CBlock
from block import CBlockHeader


def calculate_work(target: int) -> int:
    """Calculate the work represented by a given target."""
    return (1 << 256) // (target + 1)


class CBlockIndex:
    """
    Represents a single block in the blockchain with Bitcoin-specific features.
    """
    MEDIAN_TIMESPAN = 11

    __slots__ = ('header', 'hash', 'height', 'pprev', 'pnext', 'children', 'chain_work')
    
    def __init__(self, block: CBlock, parent: Optional['CBlockIndex'] = None):
        """
        Initialize a new block index from a CBlock object.
        
        Args:
            block: The block object to index
            parent: Parent CBlockIndex reference (None for genesis)
        """
        self.header = block  # Reference to full block header
        self.hash = block.get_hash()  # Block hash as bytes
        self.children = []   # List of potential next blocks
        self.pprev = parent  # Pointer to previous block
        self.pnext = None    # Pointer to next block in longest chain
        self.height = 0      # Height from genesis
        self.chain_work = 0  # Cumulative chain work
        
        if parent:
            self.height = parent.height + 1
            parent.children.append(self)
            # Calculate chain work: parent + current block's work
            block_work = calculate_work(set_compact(self.header.nBits))
            self.chain_work = parent.chain_work + block_work

    def get_median_time_past(self) -> int:
        """Calculate the Median Time Past (MTP) of the last N blocks"""
        # Collect timestamps from previous N blocks
        pmedian = []
        pindex = self

        # Traverse back through the chain (up to N blocks)
        for _ in range(self.MEDIAN_TIMESPAN):
            if pindex is None:
                break
            pmedian.append(pindex.header.nTime)
            pindex = pindex.pprev

        # If no blocks available, return 0
        if not pmedian:
            return 0

        # Sort timestamps in ascending order
        pmedian.sort()

        # Calculate median position (middle of sorted list)
        # Uses integer division: n // 2 per Bitcoin's implementation
        return pmedian[len(pmedian) // 2]

    def __repr__(self):
        """Provides a string representation for debugging"""
        return f"CBlockIndex(height={self.height}, hash={self.hash.hex()[:8]}...)"

class CChain:
    """
    Maintains a tree-shaped blockchain with Bitcoin-style validation.
    """
    def __init__(self):
        """Initialize an empty blockchain"""
        self.genesis = None
        self.tip = None
        self.block_map = {}  # Hash (bytes) to block index mapping

    def add_block(self, block: CBlock) -> Tuple[bool, CBlockIndex]:
        """
        Add a new block to the blockchain with validation.
        
        Returns:
            new_index: CBlockIndex
        """
        # Find parent block
        parent_hash = block.hashPrevBlock
        parent = self.block_map.get(parent_hash, None)
        
        # Genesis block creation
        if parent is None:
            if block.hashPrevBlock != bytes(32):
                raise ValueError("Invalid genesis parent hash")
            if self.genesis is not None:
                raise ValueError("Genesis block already exists")
            
            # Create genesis index
            self.genesis = CBlockIndex(block)
            self.tip = self.genesis
            self.block_map[self.genesis.hash] = self.genesis
            return self.genesis

        # Create new block index
        new_index = CBlockIndex(block, parent)
        self.block_map[new_index.hash] = new_index

        # Update longest chain if new chain has more work
        if new_index.chain_work > self.tip.chain_work:
            self._update_main_chain(new_index)
            
        return new_index

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
