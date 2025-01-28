from collections import namedtuple
from datetime import datetime

import hashlib
import json


def calculate_hash(data):
	hash_object = hashlib.sha256()
	hash_object.update(data.encode())
	return hash_object.hexdigest()


def now():
	current_datetime = datetime.now()
	return current_datetime.strftime("%Y-%m-%d")


Txn = namedtuple("Transaction", "id timestamp sender receiver amount memo")
# bTxn = namedtuple("Transaction", "id nonce timestamp sender receiver amount memo prev_hash hash signature")

a_dt = now()
a = Txn(1, a_dt, "Alice", "Bob", 3.125, "BTC reward")

a_json = json.dumps(a._asdict())
print(calculate_hash(a_json))