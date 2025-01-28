import hashlib

def calculate_hash(data):
	hash_object = hashlib.sha256()
	hash_object.update(data.encode())
	return hash_object.hexdigest()

sha256 = calculate_hash('Hello, world')
print(sha256)