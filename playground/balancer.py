import time


def recursive_minority_majority(n, recursion_limit=0):
    """
    Recursively computes the "minority of the majority" of a number `n` a specified number of times.

    The function first calculates two values for the input `n`:
    1. Majority: two-thirds (2/3) of `n`
    2. Minority of the Majority: one-third (1/3) of the Majority

    It then recursively applies this transformation, passing the result of each iteration as the new input for the next step. The recursion continues until the `recursion_limit` is reached, at which point the function returns the final result.

    Args:
        n (float or int): The initial number to be transformed.
        recursion_limit (int, optional): The number of recursive transformations to apply. Defaults to 0, which means no recursion and just one transformation.

    Returns:
        float: The resulting value after the specified number of recursive transformations.

    Example:
        >>> recursive_minority_majority(100, recursion_limit=3)
        1.0973936899862822

    Notes:
        - If the recursion limit is 0, the function performs a single transformation.
        - The function will recursively compute `n * (2/9)^k` after `k` recursions, where `k` is the recursion limit.
    """
    majority = n * (2 / 3)
    majority_minority = majority / 3

    if recursion_limit == 0:
        return majority_minority
    return recursive_minority_majority(majority_minority, recursion_limit - 1)


def recursive_sum_majority_minority(n, recursion_limit=0):
    """
    Recursively computes the majority of a number `n` and accumulates the majority values over multiple recursive steps.

    The function calculates the following at each recursion step:
    1. Majority: two-thirds (2/3) of the current number `n`.
    2. Minority: one-third (1/3) of the current number `n`.

    In each recursive call, the function adds the majority of the current number to the result of the next recursive step, which is calculated using the minority as the new input. This continues until the recursion limit is reached.

    Args:
        n (float or int): The initial number to be transformed and processed.
        recursion_limit (int, optional): The number of recursive steps to perform. Defaults to 0, meaning no recursion (just one step).

    Returns:
        float: The resulting value after recursively summing the majorities across the given recursion limit.

    Example:
        >>> recursive_sum_majority_minority(100, recursion_limit=3)
        67.03246456332874

    Notes:
        - If the recursion limit is set to 0, the function simply returns the majority (2/3 of `n`).
        - The function recursively adds the majority at each level of recursion until the recursion limit is reached.

    """
    majority = n * (2 / 3)
    minority = n / 3

    if recursion_limit == 0:
        return majority
    return majority + recursive_sum_majority_minority(minority, recursion_limit - 1)


MAX_SUPPLY = 10 ** 8
MARKET_CAP = 500 * 1000
recursion_limit = 7

while True:
	BURN_RATE = recursive_minority_majority(MAX_SUPPLY, recursion_limit)
	COIN_RATE = recursive_sum_majority_minority(BURN_RATE, recursion_limit)
	NET_BURN_RATE = BURN_RATE - COIN_RATE
	COIN_PRICE = MARKET_CAP / MAX_SUPPLY
	
	print(f"{COIN_PRICE:.8f} {MAX_SUPPLY:.8f} {NET_BURN_RATE:.8f}")

	MAX_SUPPLY = MAX_SUPPLY - NET_BURN_RATE
	time.sleep(0.175)
