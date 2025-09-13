"""
JSON-RPC 2.0 server for Bitcoin node API.
Provides external control and querying capabilities.
"""
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import List, Dict, Callable, Any, Optional
from urllib.parse import urlparse, parse_qs
import threading
import time

from bignum import set_compact
from block import CBlock
from crypto import hash160
from chainstate import ChainState
from script import CScript
from script_utils import ScriptBuilder
from transaction import COutPoint, CTransaction, CTxIn, CTxOut

# rpc_server.py - Add these imports at the top
from crypto import sign_ecdsa, private_key_to_public_key, wif_to_private_key, hash160
from script_utils import ScriptBuilder
from interpreter import signature_hash
from opcodes import OP_DUP, OP_HASH160, OP_CHECKSIG, SIGHASH_ALL, SIGHASH_NONE, SIGHASH_SINGLE, SIGHASH_ANYONECANPAY

try:
    import base58
except ImportError:
    print("Please install the base58 library: pip install base58")
    exit()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JSON-RPC")

# --------------------------
# Helper functions
# --------------------------

def address_to_script(address: str) -> 'CScript':
    """
    Convert a Bitcoin address to its scriptPubKey representation.
    This would need to handle different address types (P2PKH, P2SH, etc.)
    """
    if address.startswith('1'):  # P2PKH address
        # Decode base58, extract hash, create P2PKH script
        decoded = base58.b58decode(address)
        pubkey_hash = decoded[1:-4]  # Remove version and checksum
        return ScriptBuilder.p2pkh_script_pubkey(pubkey_hash, is_hash=True)
    elif address.startswith('3'):  # P2SH address
        # Similar process for P2SH
        decoded = base58.b58decode(address)
        script_hash = decoded[1:-4]
        return ScriptBuilder.p2sh_script_pubkey(script_hash)
    else:
        raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS,
                          f"Invalid address format: {address}")


def script_to_address(script_pubkey: CScript) -> str:
    """Convert scriptPubKey to Bitcoin address string"""
    try:
        ops = script_pubkey.ops

        # P2PKH: OP_DUP OP_HASH160 <20-byte hash> OP_EQUALVERIFY OP_CHECKSIG
        if (len(ops) == 5 and
            ops[0] == OP_DUP and
            ops[1] == OP_HASH160 and
            isinstance(ops[2], bytes) and
            len(ops[2]) == 20 and
            ops[3] == OP_EQUALVERIFY and
            ops[4] == OP_CHECKSIG):

            pubkey_hash = ops[2]
            # Base58 encoding with version byte 0x00 for mainnet P2PKH
            payload = b'\x00' + pubkey_hash
            checksum = hash256(payload)[:4]
            return base58.b58encode(payload + checksum).decode('ascii')

        # P2SH: OP_HASH160 <20-byte hash> OP_EQUAL
        elif (len(ops) == 3 and
              ops[0] == OP_HASH160 and
              isinstance(ops[1], bytes) and
              len(ops[1]) == 20 and
              ops[2] == OP_EQUAL):

            script_hash = ops[1]
            # Base58 encoding with version byte 0x05 for mainnet P2SH
            payload = b'\x05' + script_hash
            checksum = hash256(payload)[:4]
            return base58.b58encode(payload + checksum).decode('ascii')

        # P2PK (uncommon): <pubkey> OP_CHECKSIG
        elif (len(ops) == 2 and
              isinstance(ops[0], bytes) and
              ops[1] == OP_CHECKSIG):

            pubkey = ops[0]
            pubkey_hash = hash160(pubkey)
            # Convert to P2PKH address
            payload = b'\x00' + pubkey_hash
            checksum = hash256(payload)[:4]
            return base58.b58encode(payload + checksum).decode('ascii')

        # Unsupported script type or OP_RETURN
        return ""

    except Exception:
        return ""  # Return empty string for unsupported script types


class JSONRPCError(Exception):
    """JSON-RPC 2.0 standard error"""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(self.message)


class JSONRPCRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for JSON-RPC requests"""

    # JSON-RPC standard error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    def __init__(self, rpc_server, *args, **kwargs):
        self.rpc_server = rpc_server
        super().__init__(*args, **kwargs)

    def do_POST(self):
        """Handle POST requests (main JSON-RPC endpoint)"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            # Parse request
            request = json.loads(post_data.decode('utf-8'))
            response = self._handle_request(request)

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except JSONRPCError as e:
            self._send_error_response(e, None)
        except Exception as e:
            self._send_error_response(
                JSONRPCError(self.INTERNAL_ERROR, str(e)), None
            )

    def _handle_request(self, request: Dict) -> Dict:
        """Process single JSON-RPC request"""
        # Validate request structure
        if not isinstance(request, dict):
            raise JSONRPCError(self.INVALID_REQUEST, "Request must be an object")

        if 'jsonrpc' not in request or request['jsonrpc'] != '2.0':
            raise JSONRPCError(self.INVALID_REQUEST, "Missing or invalid jsonrpc version")

        if 'method' not in request or not isinstance(request['method'], str):
            raise JSONRPCError(self.INVALID_REQUEST, "Missing or invalid method")

        # Get method and parameters
        method_name = request['method']
        params = request.get('params', [])
        if not isinstance(params, (list, dict)):
            raise JSONRPCError(self.INVALID_REQUEST, "Params must be array or object")

        # Execute method
        try:
            result = self.rpc_server.execute_method(method_name, params)
        except JSONRPCError:
            raise
        except Exception as e:
            raise JSONRPCError(self.INTERNAL_ERROR, f"Internal error: {str(e)}")

        # Build response
        response = {
            'jsonrpc': '2.0',
            'result': result,
            'id': request.get('id')
        }

        return response

    def _send_error_response(self, error: JSONRPCError, request_id: Optional[str]):
        """Send JSON-RPC error response"""
        error_response = {
            'jsonrpc': '2.0',
            'error': {
                'code': error.code,
                'message': error.message
            },
            'id': request_id
        }

        if error.data is not None:
            error_response['error']['data'] = error.data

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(format % args)


class JSONRPCServer:
    """Main JSON-RPC server managing methods and state"""

    def __init__(self, host: str = '127.0.0.1', port: int = 8332,
                 chain_state: ChainState = None, node: 'BlockchainNode' = None):
        self.host = host
        self.port = port
        self.chain_state = chain_state
        self.node = node
        self.methods: Dict[str, Callable] = {}
        self.server: Optional[HTTPServer] = None

        # Register core methods
        self._register_core_methods()

    def _register_core_methods(self):
        """Register all available RPC methods"""
        self.register_method('getblockchaininfo', self.get_blockchain_info)
        self.register_method('getnetworkinfo', self.get_network_info)
        self.register_method('getbalance', self.get_balance)
        self.register_method('getblockcount', self.get_block_count)
        self.register_method('getbestblockhash', self.get_best_block_hash)
        self.register_method('stop', self.stop)

        # New methods to implement
        self.register_method('getblockhash', self.get_block_hash)
        self.register_method('getblock', self.get_block)
        self.register_method('getrawtransaction', self.get_raw_transaction)
        self.register_method('sendrawtransaction', self.send_raw_transaction)
        self.register_method('listunspent', self.list_unspent)
        self.register_method('validateaddress', self.validate_address)
        self.register_method('getmempoolinfo', self.get_mempool_info)
        self.register_method('gettxout', self.get_tx_out)
        self.register_method('createrawtransaction', self.create_raw_transaction)
        self.register_method('signrawtransactionwithkey', self.sign_raw_transaction_with_key)

    def register_method(self, name: str, method: Callable):
        """Register a new RPC method"""
        self.methods[name] = method

    def execute_method(self, method_name: str, params) -> Any:
        """Execute registered RPC method"""
        if method_name not in self.methods:
            raise JSONRPCError(JSONRPCRequestHandler.METHOD_NOT_FOUND,
                              f"Method {method_name} not found")

        method = self.methods[method_name]

        # Handle parameter validation based on method signature
        try:
            if isinstance(params, list):
                return method(*params)
            else:
                return method(**params)
        except TypeError as e:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS,
                              f"Invalid parameters: {str(e)}")

    def start(self):
        """Start the JSON-RPC server"""
        def handler(*args):
            return JSONRPCRequestHandler(self, *args)

        self.server = HTTPServer((self.host, self.port), handler)
        logger.info(f"JSON-RPC server started on {self.host}:{self.port}")

        # Run server in background thread
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the JSON-RPC server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("JSON-RPC server stopped")
        return "Node stopping"

    # --- RPC Method Implementations ---

    def get_blockchain_info(self) -> Dict:
        """Return information about the blockchain"""
        if not self.chain_state:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR,
                              "Chain state not available")

        chain = self.chain_state.chain
        return {
            'chain': 'main',
            'blocks': (chain.tip.height + 1) if chain.tip else 0,
            'headers': chain.tip.height if chain.tip else 0,
            'bestblockhash': chain.tip.hash.hex() if chain.tip else bytes(32),
            'difficulty': float(chain.tip.header.nBits) if chain.tip else 1.0,
            'mediantime': chain.tip.get_median_time_past() if chain.tip else 0,
            'verificationprogress': 1.0,  # Simplified
            'initialblockdownload': not chain.tip or chain.tip.height == 0,
            'chainwork': hex(chain.tip.chain_work) if chain.tip else '0x0',
            'size_on_disk': 0,  # Placeholder
            'pruned': False,
            'warnings': ''
        }

    def get_network_info(self) -> Dict:
        """Return information about the node's network"""
        if not self.node:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR,
                              "Node not available")

        stats = self.node.get_connection_stats()
        return {
            'version': 230000,  # Bitcoin Core compatible version number
            'subversion': f'/PythonBitcoin:0.1.0/',
            'protocolversion': 70015,
            'localservices': '0000000000000409',
            'localrelay': True,
            'timeoffset': 0,
            'connections': stats['total'],
            'networkactive': True,
            'networks': [
                {
                    'name': 'ipv4',
                    'limited': False,
                    'reachable': True,
                    'proxy': ''
                }
            ],
            'relayfee': 0.00001000,
            'incrementalfee': 0.00001000,
            'localaddresses': [],
            'warnings': ''
        }

    def get_balance(self, address: str = "*", minconf: int = 1) -> float:
        """Return the balance for a specific address"""
        if not self.chain_state:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR,
                              "Chain state not available")

        if address == "*":
            # Return total balance (current behavior)
            total_satoshis = self.chain_state.utxo_set.get_balance()
        else:
            # Convert address to scriptPubKey and get filtered balance
            script_pubkey = address_to_script(address)
            total_satoshis = self.chain_state.utxo_set.get_balance(script_pubkey)

        return total_satoshis / 100_000_000  # Convert to BTC

    def get_block_count(self) -> int:
        """Return the height of the most-work chain"""
        if not self.chain_state or not self.chain_state.chain.tip:
            return 0
        return self.chain_state.chain.tip.height

    def get_best_block_hash(self) -> str:
        """Return the hash of the best block"""
        if not self.chain_state or not self.chain_state.chain.tip:
            return '0' * 64
        return self.chain_state.chain.tip.hash.hex()

    # --- New RPC Method Implementations ---

    def get_block_hash(self, height: int) -> str:
        """Returns hash of block in best-block-chain at height provided."""
        if not self.chain_state:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR, "Chain state not available")

        if height < 0:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, "Block height out of range")

        # Traverse the chain to find block at specified height
        current = self.chain_state.chain.tip
        while current and current.height > height:
            current = current.pprev

        if current and current.height == height:
            return current.hash.hex()
        else:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, "Block height out of range")

    def get_block(self, block_hash: str, verbose: bool = True) -> dict:
        """Returns information about a block."""
        if not self.chain_state:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR, "Chain state not available")

        try:
            hash_bytes = bytes.fromhex(block_hash)
            block_index = self.chain_state.chain.block_map.get(hash_bytes)
            if not block_index:
                raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, "Block not found")

            if verbose:
                return {
                    'hash': block_index.hash.hex(),
                    'confirmations': self.chain_state.chain.tip.height - block_index.height + 1,
                    'height': block_index.height,
                    'version': block_index.header.nVersion,
                    'merkleroot': block_index.header.hashMerkleRoot.hex(),
                    'time': block_index.header.nTime,
                    'mediantime': block_index.get_median_time_past(),
                    'nonce': block_index.header.nNonce,
                    'bits': hex(block_index.header.nBits),
                    'difficulty': float(set_compact(block_index.header.nBits)),
                    'previousblockhash': block_index.header.hashPrevBlock.hex(),
                    'nextblockhash': block_index.pnext.hash.hex() if block_index.pnext else None,
                    'nTx': len(block_index.header.vtx),
                    'tx': [tx.get_hash().hex() for tx in block_index.header.vtx]
                }
            else:
                return block_index.header.serialize().hex()

        except ValueError:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, "Invalid block hash")

    def get_raw_transaction(self, txid: str, verbose: bool = False) -> dict:
        """Returns raw transaction data."""
        if not self.chain_state:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR, "Chain state not available")

        try:
            tx_hash = bytes.fromhex(txid)

            # Check mempool first
            tx = self.chain_state.mempool.get(tx_hash)
            if tx:
                if verbose:
                    return self._tx_to_dict(tx, None)
                else:
                    return tx.serialize().hex()

            # Check blockchain transactions
            for block_index in self.chain_state.chain.block_map.values():
                for block_tx in block_index.header.vtx:
                    if block_tx.get_hash() == tx_hash:
                        if verbose:
                            return self._tx_to_dict(block_tx, block_index.height)
                        else:
                            return block_tx.serialize().hex()

            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, "Transaction not found")

        except ValueError:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, "Invalid transaction hash")

    def _tx_to_dict(self, tx: CTransaction, block_height: int = None) -> dict:
        """Convert transaction to dictionary format for verbose response"""
        return {
            'txid': tx.get_hash().hex(),
            'hash': tx.get_hash().hex(),
            'version': tx.nVersion,
            'size': len(tx.serialize()),
            'locktime': tx.nLockTime,
            'vin': [{
                'txid': vin.prevout.hash.hex(),
                'vout': vin.prevout.n,
                'scriptSig': {
                    'asm': '',  # Would need script decompiler
                    'hex': vin.scriptSig.data.hex()
                },
                'sequence': vin.nSequence
            } for vin in tx.vin],
            'vout': [{
                'value': vout.nValue / 100_000_000,  # Convert to BTC
                'n': i,
                'scriptPubKey': {
                    'asm': '',  # Would need script decompiler
                    'hex': vout.scriptPubKey.data.hex()
                }
            } for i, vout in enumerate(tx.vout)],
            'blockhash': None,  # Would need to find containing block
            'confirmations': self.chain_state.chain.tip.height - block_height + 1 if block_height else 0,
            'time': 0,  # Would need block time
            'blocktime': 0  # Would need block time
        }

    def send_raw_transaction(self, hexstring: str) -> str:
        """Submits raw transaction to local node and network."""
        if not self.chain_state or not self.node:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR, "Node not available")

        try:
            tx_data = bytes.fromhex(hexstring)
            tx = CTransaction.deserialize(tx_data)

            # Validate transaction
            from tx_validator import validate_transaction
            if validate_transaction(tx, self.chain_state.utxo_set, self.chain_state.chain.tip.height):
                # Add to mempool
                txid = tx.get_hash()
                self.chain_state.mempool[txid] = tx

                # Broadcast to network
                self.node.send_message({
                    'id': txid.hex(),
                    'type': 'TX',
                    'tx': hexstring
                })

                return txid.hex()
            else:
                raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, "Transaction validation failed")

        except Exception as e:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, f"Invalid transaction: {str(e)}")

    def list_unspent(self, minconf: int = 1, maxconf: int = 9999999, addresses: List[str] = None) -> List[dict]:
        """Returns array of unspent transaction outputs."""
        if not self.chain_state:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR, "Chain state not available")

        current_height = self.chain_state.chain.tip.height
        unspent = []

        # Convert address strings to scriptPubKeys for filtering
        target_scripts = []
        if addresses:
            for address in addresses:
                try:
                    script_pubkey = address_to_script(address)
                    target_scripts.append(script_pubkey)
                except JSONRPCError:
                    # Skip invalid addresses but continue processing
                    continue

        for prevout, utxo in self.chain_state.utxo_set.utxos.items():
            confirmations = current_height - utxo.height + 1
            if minconf <= confirmations <= maxconf:
                # Convert scriptPubKey to address (for response)
                script_hex = utxo.tx_out.scriptPubKey.data.hex()
                address = script_to_address(utxo.tx_out.scriptPubKey)

                # Filter by addresses if specified
                if addresses:
                    if utxo.tx_out.scriptPubKey not in target_scripts:
                        continue

                # Determine spendability
                is_spendable = True
                is_solvable = True  # Assume solvable unless we detect otherwise

                # Check coinbase maturity
                if utxo.coinbase and confirmations < 100:
                    is_spendable = False

                # Check if script type is supported for spending
                # For now, we'll assume P2PKH and P2SH are solvable
                # In a real implementation, you'd check if you have the private keys
                # for the address or if it's a script you can solve

                # Additional checks could be added here for:
                # - Time-locked transactions
                # - Complex script types the node can't solve
                # - etc.

                unspent.append({
                    'txid': prevout.hash.hex(),
                    'vout': prevout.n,
                    'address': address,
                    'scriptPubKey': script_hex,
                    'amount': utxo.tx_out.nValue / 100_000_000,
                    'confirmations': confirmations,
                    'spendable': is_spendable,
                    'solvable': is_solvable,
                    'safe': confirmations > 6  # Consider safe after 6 confirmations
                })

        return unspent

    def validate_address(self, address: str) -> dict:
        """Return information about the given bitcoin address."""
        # Basic validation - would need proper address decoding
        is_valid = len(address) >= 26 and len(address) <= 35
        return {
            'isvalid': is_valid,
            'address': address if is_valid else '',
            'scriptPubKey': '',
            'isscript': False,
            'iswitness': False
        }

    def get_mempool_info(self) -> dict:
        """Returns details on the active state of the TX memory pool."""
        if not self.chain_state:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR, "Chain state not available")

        return {
            'size': len(self.chain_state.mempool),
            'bytes': sum(len(tx.serialize()) for tx in self.chain_state.mempool.values()),
            'usage': 0,  # Would need actual memory usage tracking
            'maxmempool': 300000000,  # Default value
            'mempoolminfee': 0.00001000,
            'minrelaytxfee': 0.00001000
        }

    def get_tx_out(self, txid: str, n: int, include_mempool: bool = True) -> dict:
        """Returns details about an unspent transaction output."""
        if not self.chain_state:
            raise JSONRPCError(JSONRPCRequestHandler.INTERNAL_ERROR, "Chain state not available")

        try:
            tx_hash = bytes.fromhex(txid)
            prevout = COutPoint(tx_hash, n)

            if self.chain_state.utxo_set.is_unspent(prevout):
                utxo = self.chain_state.utxo_set.utxos[prevout]
                current_height = self.chain_state.chain.tip.height

                return {
                    'bestblock': self.chain_state.chain.tip.hash.hex(),
                    'confirmations': current_height - utxo.height + 1,
                    'value': utxo.tx_out.nValue / 100_000_000,
                    'scriptPubKey': {
                        'asm': '',  # Would need script decompiler
                        'hex': utxo.tx_out.scriptPubKey.data.hex()
                    },
                    'coinbase': utxo.coinbase,
                    'height': utxo.height
                }
            else:
                return None

        except ValueError:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, "Invalid parameters")

    def create_raw_transaction(self, inputs: List[dict], outputs: dict, locktime: int = 0) -> str:
        """Create a transaction spending the given inputs and creating new outputs."""
        try:
            vin = []
            for input in inputs:
                txid = bytes.fromhex(input['txid'])
                prevout = COutPoint(txid, input['vout'])
                # Create a basic scriptSig (would need proper signing)
                scriptSig = CScript(b'')
                vin.append(CTxIn(prevout, scriptSig))

            vout = []
            for address, amount in outputs.items():
                # Convert amount to satoshis
                nValue = int(amount * 100_000_000)
                # Create scriptPubKey from address
                scriptPubKey = address_to_script(address)
                vout.append(CTxOut(nValue, scriptPubKey))

            tx = CTransaction(vin=vin, vout=vout, nLockTime=locktime)
            return tx.serialize().hex()

        except Exception as e:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, f"Invalid parameters: {str(e)}")

    def sign_raw_transaction_with_key(self, hexstring: str, privkeys: List[str],
                                    prevtxs: List[dict] = None, sighashtype: str = "ALL") -> dict:
        """Sign inputs for raw transaction using provided private keys."""
        try:
            # Deserialize the transaction
            tx_data = bytes.fromhex(hexstring)
            tx = CTransaction.deserialize(tx_data)

            # Convert SIGHASH type
            sighash_type_map = {
                "ALL": SIGHASH_ALL,
                "NONE": SIGHASH_NONE,
                "SINGLE": SIGHASH_SINGLE,
                "ALL|ANYONECANPAY": SIGHASH_ALL | SIGHASH_ANYONECANPAY,
                "NONE|ANYONECANPAY": SIGHASH_NONE | SIGHASH_ANYONECANPAY,
                "SINGLE|ANYONECANPAY": SIGHASH_SINGLE | SIGHASH_ANYONECANPAY
            }

            sighash_flag = sighash_type_map.get(sighashtype.upper(), SIGHASH_ALL)

            # Parse private keys
            signing_keys = []
            wif_prefixes = {'5', '9', 'K', 'L', 'c'}  # Set for O(1) lookups

            for privkey_str in privkeys:
                try:
                    if len(privkey_str) == 64:
                        # Raw hex private key
                        privkey_bytes = bytes.fromhex(privkey_str)
                        pubkey = private_key_to_public_key(privkey_bytes, True)  # Assume compressed
                        pubkey_hash = hash160(pubkey)
                    elif privkey_str[0] in wif_prefixes and len(privkey_str) in (51, 52):
                        # WIF format
                        privkey_bytes, is_compressed, is_testnet = wif_to_private_key(privkey_str)
                        pubkey = private_key_to_public_key(privkey_bytes, is_compressed)
                        pubkey_hash = hash160(pubkey)
                    else:
                        raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, f"Invalid private key length: {len(privkey_str)}")

                    signing_keys.append({
                        'private_key': privkey_bytes,
                        'public_key': pubkey,
                        'pubkey_hash': pubkey_hash
                    })
                except Exception as e:
                    raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, f"Invalid private key format: {privkey_str}")

            # Prepare previous transactions data
            prev_tx_map = {}
            if prevtxs:
                for prevtx in prevtxs:
                    if 'txid' in prevtx and 'vout' in prevtx:
                        txid = bytes.fromhex(prevtx['txid'])
                        prev_tx_map[(txid, prevtx['vout'])] = prevtx

            # Sign each input
            signed_inputs = []
            errors = []

            for i, txin in enumerate(tx.vin):
                try:
                    # Find the UTXO or use provided prevtx data
                    prevout = txin.prevout
                    utxo_info = None

                    # Check if we have provided previous transaction data
                    prevtx_key = (prevout.hash, prevout.n)
                    if prevtx_key in prev_tx_map:
                        utxo_info = prev_tx_map[prevtx_key]
                    else:
                        # Try to find in UTXO set
                        if self.chain_state and prevout in self.chain_state.utxo_set.utxos:
                            utxo = self.chain_state.utxo_set.utxos[prevout]
                            utxo_info = {
                                'scriptPubKey': utxo.tx_out.scriptPubKey.data.hex(),
                                'value': utxo.tx_out.nValue / 100_000_000  # Convert to BTC
                            }

                    if not utxo_info:
                        errors.append({
                            'txid': prevout.hash.hex(),
                            'vout': prevout.n,
                            'error': 'Previous output not found'
                        })
                        continue

                    # Get the scriptPubKey
                    if 'scriptPubKey' in utxo_info:
                        script_pubkey_hex = utxo_info['scriptPubKey']
                        script_pubkey = CScript(bytes.fromhex(script_pubkey_hex))
                    else:
                        errors.append({
                            'txid': prevout.hash.hex(),
                            'vout': prevout.n,
                            'error': 'No scriptPubKey provided'
                        })
                        continue

                    # Calculate signature hash
                    sighash = signature_hash(tx, i, script_pubkey, sighash_flag)

                    # Try to find matching private key
                    matched_key = None
                    for key_info in signing_keys:
                        # For P2PKH, check if pubkey hash matches
                        if (script_pubkey.ops[0] == OP_DUP and
                            script_pubkey.ops[1] == OP_HASH160 and
                            isinstance(script_pubkey.ops[2], bytes) and
                            script_pubkey.ops[2] == key_info['pubkey_hash']):
                            matched_key = key_info
                            break

                    if not matched_key:
                        errors.append({
                            'txid': prevout.hash.hex(),
                            'vout': prevout.n,
                            'error': 'No matching private key for this input'
                        })
                        continue

                    # Sign the hash
                    signature, _ = sign_ecdsa(matched_key['private_key'], sighash)
                    signature_with_sighash = signature + bytes([sighash_flag])

                    # Build scriptSig based on script type
                    if (script_pubkey.ops[0] == OP_DUP and
                        script_pubkey.ops[1] == OP_HASH160 and
                        len(script_pubkey.ops) == 5):  # P2PKH

                        script_sig = ScriptBuilder.p2pkh_script_sig(signature_with_sighash, matched_key['public_key'])

                    elif script_pubkey.ops[0] == OP_CHECKSIG:  # P2PK
                        script_sig = ScriptBuilder.p2pk_script_sig(signature_with_sighash)

                    else:
                        # For other types, we'd need more complex handling
                        errors.append({
                            'txid': prevout.hash.hex(),
                            'vout': prevout.n,
                            'error': f'Unsupported script type: {script_pubkey.ops}'
                        })
                        continue

                    # Update the transaction input
                    tx.vin[i].scriptSig = script_sig
                    signed_inputs.append(i)

                except Exception as e:
                    errors.append({
                        'txid': prevout.hash.hex(),
                        'vout': prevout.n,
                        'error': f'Signing error: {str(e)}'
                    })
                    continue

            # Verify the signed transaction
            is_complete = len(signed_inputs) == len(tx.vin) and len(errors) == 0

            if not is_complete and len(signed_inputs) > 0:
                # Partial signing completed
                pass

            return {
                'hex': tx.serialize().hex(),
                'complete': is_complete,
                'errors': errors if errors else []
            }

        except Exception as e:
            raise JSONRPCError(JSONRPCRequestHandler.INVALID_PARAMS, f"Transaction signing failed: {str(e)}")


def start_rpc_server(chain_state: ChainState, node: 'BlockchainNode',
                    host: str = '127.0.0.1', port: int = 8332):
    """Convenience function to start RPC server"""
    rpc_server = JSONRPCServer(host, port, chain_state, node)
    rpc_server.start()
    return rpc_server
