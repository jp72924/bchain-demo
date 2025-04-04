import math
import json

from hashlib import sha256


def binary_heap_levels(n):
    if n < 1:
        return 0  # No levels for an empty heap
    return math.ceil(math.log2(n + 1))


def count_leaves(n):
    if n < 1:
        return 0  # No leaves in an empty heap
    return (n + 1) // 2  # Equivalent to ceil(n / 2)


def count_non_leaves(n):
    if n < 1:
        return 0  # No non-leaf nodes in an empty heap
    return n // 2


def depth_in_binary_heap(n):
    if n < 1:
        return -1  # Invalid index
    return (n).bit_length() - 1


def get_parent(index, n):
    if index < 1 or index >= n:
        return None  # No parent for the root or invalid index
    return (index - 1) // 2


def get_children(index, n):
    left_child = 2 * index + 1
    right_child = 2 * index + 2
    
    left = left_child if left_child < n else None
    right = right_child if right_child < n else None
    
    return (left, right)


def binary_heap_to_nested_dict(heap, index=0, depth=0):
    """
    Convert a binary heap (array) representation of a Merkle tree to a nested dictionary.

    Parameters:
        heap (list): The binary heap representing the Merkle tree as an array of hashes.
        index (int): The current index in the heap (default is 0, the root).

    Returns:
        dict: A nested dictionary representation of the Merkle tree.
    """
    if index >= len(heap):
        return None  # Base case: No node exists at this index
    
    # Recursive construction of the nested dictionary
    return {
        "hash": heap[index],
        "index": index,
        "depth": depth,
        "left": binary_heap_to_nested_dict(heap, 2 * index + 1, depth + 1),
        "right": binary_heap_to_nested_dict(heap, 2 * index + 2, depth + 1)
    }


def find_mismatches(tree_a, tree_b, index=0, mismatches=None):
    """
    Compares two Merkle trees and returns indices where node hashes differ.
    
    Args:
        tree_a (list): First Merkle tree represented as a binary heap
        tree_b (list): Second Merkle tree represented as a binary heap
        index (int): Index to start comparison from (default: root=0)
        mismatches (list): Accumulator for recursion (should not be provided by caller)
    
    Returns:
        List of indices where node hashes differ between the two trees
    
    Example:
        mismatches = find_mismatched_nodes(tree1, tree2)
    """
    if mismatches is None:
        mismatches = []

    # Check if current index is valid for both trees
    if index >= len(tree_a) or index >= len(tree_b):
        return mismatches

    # Record mismatch if hashes differ at current index
    if tree_a[index] != tree_b[index]:
        mismatches.append(index)

        # Recursively check child nodes
        left_child, right_child = get_children(index, len(tree_a))
        
        if left_child is not None:
            find_mismatches(tree_a, tree_b, left_child, mismatches)
        if right_child is not None:
            find_mismatches(tree_a, tree_b, right_child, mismatches)

    return mismatches


def merkle_root(iterable):
    """Calculate the Merkle root of a list of iterable."""
    if not iterable:
        return None
    
    # Create initial leaves
    leaves = [sha256(item) for item in iterable]
    hashes = leaves

    while len(leaves) > 1:
        # If odd number of leaves, duplicate the last one
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])
        
        # Create new level
        new_level = []
        for i in range(0, len(leaves), 2):
            combined_hash = sha256(leaves[i] + leaves[i + 1])
            new_level.append(combined_hash)
        
        leaves = new_level
        hashes.extend(leaves)

    return leaves[0], hashes  # The Merkle root and flat tree

# Example usage:
numbers = [str(x) for x in range(2**2)]
root_hash, binary_heap = merkle_root(numbers)
print("Merkle Root: ", root_hash)

size = len(binary_heap)

binary_heap.reverse()

merkle_tree = binary_heap_to_nested_dict(binary_heap)
d = {
    'root': root_hash, 
    'leaves': count_leaves(size),
    'non_leaves': count_non_leaves(size),
    'tree': merkle_tree
}
print(json.dumps(d, indent=2))