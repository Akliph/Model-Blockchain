"""
Node.py is meant to handle most of the internal node logic. Methods for validating incoming transactions
and requests are defined here and mainly called from server.py. Dynamic information like calculated
block difficulty, median block time, block difficulty, UTXO(maybe), MEMPOOL, etc. are all calculated and stored
in a node config file here.


**Node-Operator parameters (default in parentheses):
block_size = (10 transactions)
...

<-----Supply Timeline Constants (every node must follow these)----->
-- Independent variables
Smallest denomination = 10^-2 coins
Starting block reward = 1000 coins
Reward factor per split = 0.5x
Reward split = 1000 blocks

-- Dependent variables
Total supply of coins = 199940 coins or 19994000 "cents"
Total number of splits = 17
Entire supply mining time = 0.97 years | 354.16 years
Time fore each split = 20.83 days | 0.05 years
"""


import os
import json
import blockchain


def initialize():
    # Create mempool directory
    if not os.path.isdir('./mempool'):
        os.mkdir('./mempool')

    if not os.path.isfile('./mempool/mempool.json'):
        with open('./mempool/mempool.json', 'w+') as f:
            data = []
            f.write(json.dumps(data))
            f.close()


"""
Data verification
"""


# Returns a string describing the transaction verification error, otherwise returns None
def verify_transaction(transaction_dict):
    # Data formatting validation
    transaction_keys = list(transaction_dict.keys())
    example_dict = blockchain.get_transaction_template()
    example_keys = list(example_dict.keys())

    # Root key check
    for key in example_keys:
        if key not in transaction_keys:
            return "Not all required keys present. Check the example-json folder."
        # Root value type check
        if type(example_dict[key]) != type(transaction_dict[key]):
            return f"Dict key, {key} is type {type(transaction_dict[key])}, not {type(example_dict[key])}"

    # Nested key check: user-data
    for key in list(example_dict['user_data'].keys()):
        if key not in list(transaction_dict['user_data'].keys()):
            return ("[Improper formatting] Not all required keys present in 'user_data' dict." +
                    " Check the example-json folder.")
        # Nested value type check: user-data
        if type(example_dict['user_data'][key]) != type(example_dict['user_data'][key]):
            return (f"Dict key, {key} is type {type(transaction_dict['user_data'][key])}, " +
                    f"not {type(example_dict['user_data'][key])}")

    # Nested key check: inputs
    for tx_input in transaction_dict['inputs']:
        for key in list(example_dict['inputs'][0].keys()):
            if key not in list(tx_input.keys()):
                return f"Key {key} not found in an input of this transaction"
            # Nested value type check: inputs
            if type(example_dict['inputs'][0][key]) != type(tx_input[key]):
                return (f"Dict key {key} is type {type(tx_input[key])}, " +
                        f"not type {type(example_dict['inputs'][0][key])}")

    # Nested key check: outputs
    for tx_output in transaction_dict['outputs']:
        for key in list(example_dict['outputs'][0].keys()):
            if key not in list(tx_output.keys()):
                return f"Key {key} not found in an input of this transaction"
            # Nested value type check: outputs
            if type(example_dict['outputs'][0][key]) != type(tx_output[key]):
                return (f"Dict key {key} is type {type(tx_output[key])}, " +
                        f"not type {type(example_dict['outputs'][0][key])}")

    # RSA signature validation...

    return None


# Returns a string describing the block verification error, otherwise returns None
def verify_block(block_dict):
    block_keys = list(block_dict.keys())
    example_dict = blockchain.get_block_template()
    example_keys = list(example_dict.keys())

    # Root key check
    for key in example_keys:
        if key not in block_keys:
            return "Not all required keys present. Check the example-json folder."

    # Verify transaction in blocks
    for transaction in block_dict['transactions']:
        verification_error = verify_transaction(transaction)
        if verification_error is not None:
            return verification_error

    # Check that header matches the previous block...

    # Check that nonce is valid...

    return None


"""
Add data to blockchain once its verified
"""


# Takes a transaction dict and adds it to the mempool if verified
def add_to_mempool(transaction):
    # Validate transaction before adding it to the mempool
    verification_error = verify_transaction(transaction)
    if verification_error is not None:
        return verification_error

    # Add to mempool file
    with open('./mempool/mempool.json', 'r+') as f:
        data = json.load(f)
        data.append(transaction)
        data = json.dumps(data, indent=4)
        f.seek(0)
        f.write(data)
        f.truncate()
        f.close()
        return True


# Takes a block dict and adds it to the blockchain if verified
def add_to_blockchain(block):
    verification_error = verify_block(block)
    if verification_error is not None:
        return verification_error

    blockchain.add_block(block)


"""
Node Data Getters
"""


# Returns list or dict from the mempool directory (all transactions, by index, or by tx id)
def get_tx(all_tx=False, index=-1, tx_id=None):
    # Writes all blocks to one json file and returns it
    if all_tx:
        transactions = json.load(open('./mempool/mempool.json', 'r'))
        return transactions

    # If index is specified and header is not then return file at index
    if index >= 0 and tx_id is None:
        transactions = json.load(open('./mempool/mempool.json', 'r'))
        return transactions[index]

    # If header is specified and index is not then find file with name header
    elif tx_id is not None and index < 0:
        transactions = json.load(open('./mempool/mempool.json', 'r'))
        for tx in transactions:
            if id == tx['tx_id']:
                return tx
        return None

    return None

# Find utxo of public key on blockchain
# Find the maximum hash of the block to adjust the difficulty
