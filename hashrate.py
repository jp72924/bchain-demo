import hashlib
import time

def measure_hashrate(hash_function="sha256", iterations=1000000):
  """
  Measures the hash rate of the current machine.

  Args:
    hash_function: The hash function to use (e.g., "sha256", "md5", "sha1").
    iterations: The number of iterations to perform.

  Returns:
    The measured hash rate in hashes per second.
  """

  data = b"This is a test string for hash rate measurement."
  hash_func = getattr(hashlib, hash_function)

  start_time = time.time()
  for _ in range(iterations):
    hash_func(data).hexdigest()
  end_time = time.time()

  elapsed_time = end_time - start_time
  hash_rate = iterations / elapsed_time

  return hash_rate

if __name__ == "__main__":
  hash_rate = measure_hashrate()
  print(f"Hash rate: {hash_rate:.2f} hashes/second")