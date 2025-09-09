"""
Simple JSON-RPC client for testing the node API
"""
import json
import requests


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
    
    def getblockchaininfo(self):
        return self.call('getblockchaininfo')
    
    def getnetworkinfo(self):
        return self.call('getnetworkinfo')
    
    def getbalance(self, address='*', minconf=1):
        return self.call('getbalance', [address, minconf])

    def getblockcount(self):
        return self.call('getblockcount')

    def stop(self):
        return self.call('stop')


if __name__ == "__main__":
    # Test the RPC interface
    client = BitcoinRPCClient('127.0.0.1', 8332)  # Adjust host and port as needed

    print("Testing RPC methods:")
    print("Blockchain Info:", client.getblockchaininfo())
    print("Network Info:", client.getnetworkinfo())

    # Get total balance (all addresses)
    print("Total Balance:", client.getbalance())

    # Get balance for a specific address
    specific_address = "1A9Dc8oouGkbi1gdr1xRwJnmGNaxETZKqn"  # Example address
    print(f"Balance for {specific_address}:", client.getbalance(specific_address))

    print("Block Count:", client.getblockcount())
