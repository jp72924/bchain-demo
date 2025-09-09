"""
JSON-RPC 2.0 server for Bitcoin node API.
Provides external control and querying capabilities.
"""
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Callable, Any, Optional
from urllib.parse import urlparse, parse_qs
import threading

from crypto import hash160
from chainstate import ChainState
from script_utils import ScriptBuilder

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
        # Placeholder for future methods:
        # self.register_method('sendtoaddress', self.send_to_address)
        # self.register_method('getnewaddress', self.get_new_address)
        # self.register_method('listtransactions', self.list_transactions)

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
            'blocks': chain.tip.height if chain.tip else 0,
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


def start_rpc_server(chain_state: ChainState, node: 'BlockchainNode',
                    host: str = '127.0.0.1', port: int = 8332):
    """Convenience function to start RPC server"""
    rpc_server = JSONRPCServer(host, port, chain_state, node)
    rpc_server.start()
    return rpc_server
