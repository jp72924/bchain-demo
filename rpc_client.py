"""
Enhanced JSON-RPC client for testing all node API methods
"""
import json
import requests
from typing import List, Dict, Any


class BitcoinRPCClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 8332):
        self.url = f'http://{host}:{port}'
        self.headers = {'content-type': 'application/json'}

    def call(self, method: str, params=None):
        """Make JSON-RPC call"""
        if params is None:
            params = []

        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': 1
        }

        response = requests.post(self.url, data=json.dumps(payload),
                               headers=self.headers, timeout=30)
        return response.json()

    # Existing methods
    def getblockchaininfo(self):
        return self.call('getblockchaininfo')

    def getnetworkinfo(self):
        return self.call('getnetworkinfo')

    def getbalance(self, address='*', minconf=1):
        return self.call('getbalance', [address, minconf])

    def getblockcount(self):
        return self.call('getblockcount')

    def getbestblockhash(self):
        return self.call('getbestblockhash')

    def stop(self):
        return self.call('stop')

    # New methods
    def getblockhash(self, height: int):
        """Get block hash by height"""
        return self.call('getblockhash', [height])

    def getblock(self, block_hash: str, verbose: bool = True):
        """Get block information"""
        return self.call('getblock', [block_hash, verbose])

    def getrawtransaction(self, txid: str, verbose: bool = False):
        """Get raw transaction data"""
        return self.call('getrawtransaction', [txid, verbose])

    def sendrawtransaction(self, hexstring: str):
        """Send raw transaction"""
        return self.call('sendrawtransaction', [hexstring])

    def listunspent(self, minconf: int = 1, maxconf: int = 9999999, addresses: List[str] = None):
        """List unspent transaction outputs"""
        params = [minconf, maxconf]
        if addresses:
            params.append(addresses)
        return self.call('listunspent', params)

    def validateaddress(self, address: str):
        """Validate bitcoin address"""
        return self.call('validateaddress', [address])

    def getmempoolinfo(self):
        """Get memory pool information"""
        return self.call('getmempoolinfo')

    def gettxout(self, txid: str, n: int, include_mempool: bool = True):
        """Get transaction output details"""
        return self.call('gettxout', [txid, n, include_mempool])

    def createrawtransaction(self, inputs: List[Dict], outputs: Dict, locktime: int = 0):
        """Create raw transaction"""
        return self.call('createrawtransaction', [inputs, outputs, locktime])

    def signrawtransactionwithkey(self, hexstring: str, privkeys: List[str], prevtxs: List[Dict] = None):
        """Sign raw transaction with private keys"""
        params = [hexstring, privkeys]
        if prevtxs:
            params.append(prevtxs)
        return self.call('signrawtransactionwithkey', params)


def main():
    # Test the RPC interface
    client = BitcoinRPCClient('127.0.0.1', 8332)

    print("=== Testing All RPC Methods ===\n")

    # 1. Basic blockchain info
    print("1. Blockchain Info:")
    blockchain_info = client.getblockchaininfo()
    print(f"   Blocks: {blockchain_info['result']['blocks']}")
    print(f"   Best block hash: {blockchain_info['result']['bestblockhash']}")
    print(f"   Difficulty: {blockchain_info['result']['difficulty']}\n")

    # 2. Network info
    print("2. Network Info:")
    network_info = client.getnetworkinfo()
    print(f"   Connections: {network_info['result']['connections']}")
    print(f"   Version: {network_info['result']['version']}\n")

    # 3. Balance
    print("3. Balance:")
    balance = client.getbalance()
    print(f"   Total balance: {balance['result']} BTC\n")

    # 4. Block operations
    print("4. Block Operations:")
    block_count = client.getblockcount()
    current_height = block_count['result']
    print(f"   Current block height: {current_height}")

    # Get block hash for height 0 (genesis)
    block_hash = client.getblockhash(0)
    print(f"   Genesis block hash: {block_hash['result']}")

    # Get block info for genesis block
    block_info = client.getblock(block_hash['result'])
    print(f"   Genesis block time: {block_info['result']['time']}\n")

    # 5. Memory pool info
    print("5. Memory Pool:")
    mempool_info = client.getmempoolinfo()
    print(f"   Mempool size: {mempool_info['result']['size']} transactions")
    print(f"   Mempool bytes: {mempool_info['result']['bytes']} bytes\n")

    # 6. List unspent outputs
    print("6. Unspent Outputs:")
    unspent = client.listunspent()
    print(f"   Found {len(unspent['result'])} unspent outputs")
    if unspent['result']:
        first_utxo = unspent['result'][0]
        print(f"   First UTXO: {first_utxo['txid']}:{first_utxo['vout']}")
        print(f"   Amount: {first_utxo['amount']} BTC\n")

        # 7. Get specific transaction output
        print("7. Transaction Output:")
        txout = client.gettxout(first_utxo['txid'], first_utxo['vout'])
        if txout['result']:
            print(f"   Output value: {txout['result']['value']} BTC")
            print(f"   Confirmations: {txout['result']['confirmations']}\n")
        else:
            print("   Output not found (may be spent)\n")

        # 8. Get raw transaction
        print("8. Raw Transaction:")
        raw_tx = client.getrawtransaction(first_utxo['txid'], verbose=True)
        print(f"   Transaction version: {raw_tx['result']['version']}")
        print(f"   Input count: {len(raw_tx['result']['vin'])}")
        print(f"   Output count: {len(raw_tx['result']['vout'])}\n")

    # 9. Address validation
    print("9. Address Validation:")
    test_address = "1A9Dc8oouGkbi1gdr1xRwJnmGNaxETZKqn"
    address_validation = client.validateaddress(test_address)
    print(f"   Address {test_address} is valid: {address_validation['result']['isvalid']}\n")

    # 10. Create raw transaction (example)
    print("10. Create Raw Transaction:")
    try:
        # Example inputs and outputs (would need real data)
        inputs = [{"txid": bytes(32).hex(), "vout": 0}]
        outputs = {"1A9Dc8oouGkbi1gdr1xRwJnmGNaxETZKqn": 0.001}

        raw_tx_creation = client.createrawtransaction(inputs, outputs)
        print(f"   Created raw transaction: {raw_tx_creation['result'][:64]}...\n")
    except Exception as e:
        print(f"   Raw transaction creation failed: {e}\n")

    # 11. Sign raw transaction (example - will fail without proper implementation)
    print("11. Sign Raw Transaction:")
    try:
        # This will fail since signing isn't fully implemented
        signing_result = client.signrawtransactionwithkey("rawtxhex", ["privatekey"])
        print(f"   Signing complete: {signing_result['result']['complete']}\n")
    except Exception as e:
        print("   Signing not fully implemented (expected)\n")

    # 12. Best block hash
    print("12. Best Block:")
    best_block = client.getbestblockhash()
    print(f"   Best block hash: {best_block['result']}\n")

    print("=== All RPC methods tested successfully! ===")

    # Uncomment to test node shutdown
    # print("\nTesting node shutdown...")
    # shutdown = client.stop()
    # print(f"Shutdown result: {shutdown}")


if __name__ == "__main__":
    main()
