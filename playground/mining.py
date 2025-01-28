import hashlib
import json


def calculate_hash(data):
	hash_object = hashlib.sha256()
	hash_object.update(data.encode())
	return hash_object.hexdigest()


class Transaction(object):
	"""docstring for Transaction"""
	def __init__(self, id, sender, receiver, amount):
		super(Transaction, self).__init__()
		self.id = id
		# self.timestamp = timestamp
		self.sender = sender
		self.receiver = receiver
		self.amount = amount
		# self.memo = memo

		self.nonce = 0
		self.hash = None

	def mine(self):
		while True:
			data = self.__dict__
			data_str = json.dumps(data)
			txn_hash = calculate_hash(data_str)

			if txn_hash.startswith("00000"):
				self.hash = txn_hash
				break

			self.nonce += 1


txn = Transaction(1, "Alice", "Bob", 3.125)
print(txn)
txn.mine()
print(txn.__dict__)