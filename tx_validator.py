from interpreter import verify_script
from transaction import CTransaction
from utxo import UTXOSet


class TransactionValidationError(Exception): pass


def validate_transaction(tx: CTransaction, utxo_set: UTXOSet, block_height: int) -> bool:
    """Full transaction validation pipeline"""
    # Structural checks
    if not tx.is_coinbase():
        if not tx.vin:
            raise TransactionValidationError("No inputs in non-coinbase tx")
    
    # 1. Basic structural validation
    try:
        raw_tx = tx.serialize()
        if len(raw_tx) > 1000000:  # Bitcoin Core MAX_STANDARD_TX_WEIGHT
            raise TransactionValidationError("Oversized transaction")
    except Exception as e:
        raise TransactionValidationError(f"Serialization error: {str(e)}")

    # 2. Coinbase-specific checks
    if tx.is_coinbase():
        if not (2 <= len(tx.vin[0].scriptSig.data) <= 100):
            raise TransactionValidationError("Invalid coinbase scriptSig")
        return True  # Coinbase handled differently in block validation

    # 3. Input validation
    input_values = []
    for i, txin in enumerate(tx.vin):
        # Check UTXO existence
        prevout = txin.prevout
        if not utxo_set.is_unspent(prevout):
            raise TransactionValidationError(f"Input {i} spends non-existent UTXO")
        
        # Get referenced UTXO
        utxo = utxo_set.utxos.get(prevout)
        if not utxo:
            raise TransactionValidationError(f"Missing UTXO for {prevout}")
        
        # Check coinbase maturity
        if utxo.is_coinbase:
            if (block_height - utxo.block_height) < 100:
                raise TransactionValidationError("Immature coinbase spend")
        
        input_values.append(utxo.tx_out.nValue)

    # 4. Output validation
    output_values = [txout.nValue for txout in tx.vout]
    if any(v < 0 or v > 2100000000000000 for v in output_values):
        raise TransactionValidationError("Invalid output value")

    # 5. Fee calculation
    total_in = sum(input_values)
    total_out = sum(output_values)
    if total_in < total_out:
        raise TransactionValidationError("Insufficient input value")

    # 6. Script verification
    for i, txin in enumerate(tx.vin):
        utxo = utxo_set.utxos[txin.prevout]
        if not verify_script(txin.scriptSig, utxo.tx_out.scriptPubKey, tx, i):
            raise TransactionValidationError(f"Script verification failed for input {i}")

    # 7. Locktime check
    if tx.nLockTime != 0:
        locktime_met = (tx.nLockTime < block_height) if tx.nLockTime < 500000000 else (tx.nLockTime < int(time.time()))
        if not locktime_met:
            raise TransactionValidationError("Locktime not met")

    return True
