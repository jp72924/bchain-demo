import hashlib

def sha256(data):
	return hashlib.sha256(data.encode('utf-8')).hexdigest()

class Block:
	def __init__(self, data, hash, prev_hash):
		self.data = data
		self.hash = hash
		self.prev_hash = prev_hash

class Blockchain:
	def __init__(self):
		hashLast = sha256('last_gen')
		hashFisrt = sha256('first_gen')

		genesis = Block('gen_data', hashFisrt, hashLast)
		self.chain = [genesis]

	def add(self, data):
		prev_hash = self.chain[-1].hash
		hash = sha256(data+prev_hash)
		block = Block(data, hash, prev_hash)
		self.chain.append(block)

bchain = Blockchain()
bA = bchain.add('A')
bB = bchain.add('B')
bC = bchain.add('C')

for block in bchain.chain:
	print(block.__dict__)