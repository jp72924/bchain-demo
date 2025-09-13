"""
Enhanced JSON-RPC client for testing all node API methods with wallet functionality
"""
import json
import requests
from typing import List, Dict, Any, Optional
import time


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

        try:
            response = requests.post(self.url, data=json.dumps(payload),
                                   headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"RPC call failed: {e}")
            return {'error': str(e)}

    # Existing methods
    def getblockchaininfo(self):
        return self.call('getblockchaininfo')

    def getnetworkinfo(self):
        return self.call('getnetworkinfo')

    def getbalance(self, address: str = "*", minconf: int = 1) -> Optional[float]:
        """Get balance for specific address or total if address='*'"""
        result = self.call('getbalance', [address, minconf])
        if 'result' in result:
            return result['result']
        return None

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

    def sendrawtransaction(self, hexstring: str) -> Optional[str]:
        """Send raw transaction and return txid if successful"""
        result = self.call('sendrawtransaction', [hexstring])
        if 'result' in result:
            return result['result']
        elif 'error' in result:
            print(f"Transaction failed: {result['error']}")
        return None

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

    def signrawtransactionwithkey(self, hexstring: str, privkeys: List[str], prevtxs: List[Dict] = None, sighashtype: str = "ALL"):
        """Sign raw transaction with private keys"""
        params = [hexstring, privkeys]
        if prevtxs:
            params.append(prevtxs)
            params.append(sighashtype)
        elif sighashtype != "ALL":
            params.append([])
            params.append(sighashtype)
        return self.call('signrawtransactionwithkey', params)

    # Enhanced wallet methods
    def get_address_balance(self, address: str, minconf: int = 1) -> Dict[str, Any]:
        """Get detailed balance information for a specific address"""
        # Validate address first
        validation = self.validateaddress(address)
        if not validation.get('result', {}).get('isvalid', False):
            return {'error': f'Invalid address: {address}'}

        # Get balance
        balance = self.getbalance(address, minconf)
        if balance is None:
            return {'error': 'Failed to get balance'}

        # Get UTXOs for this address
        unspent = self.listunspent(minconf, 9999999, [address])
        utxos = unspent.get('result', [])

        total_utxo_value = sum(utxo['amount'] for utxo in utxos)
        utxo_count = len(utxos)

        return {
            'address': address,
            'balance': balance,
            'utxo_count': utxo_count,
            'total_utxo_value': total_utxo_value,
            'utxos': utxos
        }

    def create_and_send_transaction(self, from_address: str, to_address: str, amount: float, privkey: str, fee: float = 0.0001) -> Optional[str]:
        """
        Create and send a transaction from one address to another

        Args:
            from_address: Source address (must have UTXOs)
            to_address: Destination address
            amount: Amount to send in BTC
            privkey: Private key in WIF format for signing
            fee: Transaction fee in BTC

        Returns:
            Transaction ID if successful, None otherwise
        """
        print(f"Creating transaction: {amount} BTC from {from_address} to {to_address}")

        # Validate addresses
        from_valid = self.validateaddress(from_address)
        to_valid = self.validateaddress(to_address)

        if not from_valid.get('result', {}).get('isvalid', False):
            print(f"Invalid from address: {from_address}")
            return None

        if not to_valid.get('result', {}).get('isvalid', False):
            print(f"Invalid to address: {to_address}")
            return None

        # Get UTXOs for the from address - filter for spendable ones only
        unspent_result = self.listunspent(1, 9999999, [from_address])
        utxos = unspent_result.get('result', [])

        # Filter out non-spendable UTXOs
        spendable_utxos = [utxo for utxo in utxos if utxo.get('spendable', False)]

        if not spendable_utxos:
            print(f"No spendable UTXOs found for address: {from_address}")
            print(f"Total UTXOs: {len(utxos)}, Spendable: {len(spendable_utxos)}")
            # Optionally show why UTXOs are not spendable
            for utxo in utxos:
                if not utxo.get('spendable', False):
                    print(f"  UTXO {utxo['txid']}:{utxo['vout']} - not spendable")
            return None

        # Sort spendable UTXOs by amount (ascending) to try to use greatest ones first
        spendable_utxos.sort(key=lambda x: x['amount'], reverse=True)

        # Select minimum necessary UTXOs instead of all
        selected_utxos = []
        total_selected = 0.0
        target_amount = amount + fee

        for utxo in spendable_utxos:
            if total_selected < target_amount:
                selected_utxos.append(utxo)
                total_selected += utxo['amount']
            else:
                break  # We have enough, stop selecting

        # Check if we have enough funds with selected UTXOs
        if total_selected < target_amount:
            print(f"Insufficient funds: {total_selected} BTC selected, need {target_amount} BTC")
            print(f"Total spendable balance: {sum(utxo['amount'] for utxo in spendable_utxos)} BTC")
            return None

        inputs = []
        prevtxs = []

        for utxo in selected_utxos:
            inputs.append({
                "txid": utxo['txid'],
                "vout": utxo['vout']
            })
            prevtxs.append({
                "txid": utxo['txid'],
                "vout": utxo['vout'],
                "scriptPubKey": utxo['scriptPubKey'],
                "value": utxo['amount']
            })

        # Calculate change
        total_input = total_selected
        change = total_input - amount - fee

        # Create outputs
        outputs = {to_address: amount}
        if change > 0:
            outputs[from_address] = change

        # Create raw transaction
        raw_tx_result = self.createrawtransaction(inputs, outputs)
        if 'error' in raw_tx_result:
            print(f"Failed to create raw transaction: {raw_tx_result.get('error')}")
            return None

        raw_tx_hex = raw_tx_result.get('result')
        if not raw_tx_hex:
            print("No transaction hex returned")
            return None

        # Sign the transaction
        sign_result = self.signrawtransactionwithkey(raw_tx_hex, [privkey], prevtxs)
        if 'error' in sign_result:
            print(f"Failed to sign transaction: {sign_result.get('error')}")
            return None

        signed_tx = sign_result.get('result', {})
        if not signed_tx.get('complete', False):
            print(f"Transaction signing incomplete: {signed_tx.get('errors')}")
            return None

        # Send the transaction
        txid = self.sendrawtransaction(signed_tx['hex'])
        if txid:
            print(f"Transaction sent successfully! TXID: {txid}")
            print(f"Used {len(selected_utxos)} UTXOs (minimum necessary)")
            print(f"Selected amount: {total_selected} BTC, Needed: {target_amount} BTC")

            # Wait for transaction to propagate
            print("Waiting for transaction to be detected...")
            time.sleep(2)

            # Check if transaction is in mempool
            mempool_info = self.getmempoolinfo()
            print(f"Mempool size: {mempool_info.get('result', {}).get('size', 'unknown')}")

            return txid

        return None

    def monitor_transaction(self, txid: str, timeout: int = 60):
        """Monitor a transaction until it's confirmed or timeout"""
        print(f"Monitoring transaction {txid}...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check mempool first
            try:
                raw_tx = self.getrawtransaction(txid, verbose=True)
                if 'result' in raw_tx:
                    tx_data = raw_tx['result']
                    if 'confirmations' in tx_data and tx_data['confirmations'] > 0:
                        print(f"Transaction confirmed with {tx_data['confirmations']} confirmations!")
                        return True
                    else:
                        print("Transaction in mempool, waiting for confirmation...")
                else:
                    print("Transaction not found in mempool or blockchain yet...")
            except:
                print("Error checking transaction status")

            time.sleep(5)

        print("Transaction monitoring timeout")
        return False


def main():
    # Test the RPC interface with enhanced wallet functionality
    client = BitcoinRPCClient('127.0.0.1', 8332)

    print("=== Testing Enhanced Wallet Functionality ===\n")

    # Test addresses (replace with actual addresses from your node)
    test_address_1 = "1LjSwS2r46eQuWsgV1zUKV4vXAJvG9BgRd"  # Replace with real address
    test_address_2 = "1A9Dc8oouGkbi1gdr1xRwJnmGNaxETZKqn"  # Replace with real address

    # Test private key (replace with actual private key for test_address_1)
    test_privkey = "L2AqHErFdJvM9Pscv6eJceyWzFAu5z8rCiWH1opivENwkdKssUUa"  # Replace with real WIF

    # 1. Check specific address balance
    print("1. Address Balance Check:")
    balance_info = client.get_address_balance(test_address_1)
    if 'error' in balance_info:
        print(f"   Error: {balance_info['error']}")
    else:
        print(f"   Address: {balance_info['address']}")
        print(f"   Balance: {balance_info['balance']} BTC")
        print(f"   UTXO Count: {balance_info['utxo_count']}")
        print(f"   Total UTXO Value: {balance_info['total_utxo_value']} BTC")

        if balance_info['utxos']:
            print(f"   First UTXO: {balance_info['utxos'][0]['txid']}:{balance_info['utxos'][0]['vout']}")
            print(f"   UTXO Amount: {balance_info['utxos'][0]['amount']} BTC")
    print()

    # 2. Validate addresses
    print("2. Address Validation:")
    for addr in [test_address_1, test_address_2, "invalid_address"]:
        validation = client.validateaddress(addr)
        is_valid = validation.get('result', {}).get('isvalid', False)
        print(f"   {addr}: {'Valid' if is_valid else 'Invalid'}")
    print()

    # 3. Send transaction (only if we have funds)
    print("3. Transaction Creation and Sending:")

    # Check if we have enough balance to send a small amount
    balance_info = client.get_address_balance(test_address_1)
    if 'error' not in balance_info and balance_info['balance'] > 0.001:
        amount_to_send = 51 # Send a very small amount
        txid = client.create_and_send_transaction(
            from_address=test_address_1,
            to_address=test_address_2,
            amount=amount_to_send,
            privkey=test_privkey,
            fee=0.00001
        )

        if txid:
            print(f"   Transaction sent! TXID: {txid}")

            # Monitor the transaction
            print("4. Transaction Monitoring:")
            confirmed = client.monitor_transaction(txid, timeout=30)
            if confirmed:
                print("   Transaction confirmed!")
            else:
                print("   Transaction not confirmed within timeout")
        else:
            print("   Failed to send transaction")
    else:
        print("   Insufficient balance for transaction test")
    print()

    # 5. Check updated balances
    print("5. Updated Balances:")
    for addr in [test_address_1, test_address_2]:
        balance = client.getbalance(addr)
        print(f"   {addr}: {balance if balance is not None else 'Unknown'} BTC")
    print()

    print("=== Wallet functionality test completed! ===")


if __name__ == "__main__":
    main()
