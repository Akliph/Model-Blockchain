"""
Node.py is meant to handle most of the internal node logic as well as be the sole manager of mempool management.
Methods for validating incoming transactions and requests are defined here and mainly called from server.py.
Dynamic information like calculated block difficulty, median block time, block difficulty, UTXO(maybe), MEMPOOL, etc.
are all calculated and stored in a node config file here.


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
Entire supply mining time = 0.97 years | 354.16 days
Time fore each split = 20.83 days | 0.05 years


<-----Transaction Validation----->
-- COINBASE Transaction
The first transaction in a block should be added by the miner with a single input. The input should have the
previous_output holding a 'COINBASE' string.

The signature_script is arbitrary. The output should contain an
int with the coinbase reward plus the remainder of the unused input which will be considered fees.

-- Input/Output Validation
In a normal transaction all inputs previous_output should hold a list containing ['block header containing transaction,
index of transaction, index of output']. All of the inputs will be added up, and then the values of the outputs will be
added up. The transaction will only be valid if the value of the inputs is less than or equal to the value of the
outputs. The remainder of the inputs should be included in the value of the coinbase transaction's output by the miner.
"""


import os
import json
import blockchain

block_reward = 1000


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
        if len(tx_input['previous_output']) != 3:
            return "All transaction inputs 'previous output' key should contain a list with exactly 3 values"
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

    # Input/Output validation
    input_sum = 0
    output_sum = 0

    # Inputs validation
    for tx_input in transaction_dict['inputs']:

        # If this is the coinbase input make sure its the only input in the transaction
        if transaction_dict['inputs'].index(tx_input) == 0:
            if tx_input['previous_output'][0] == 'COINBASE':
                if len(transaction_dict['inputs']) > 1 or len(transaction_dict['outputs']) > 1:
                    return "The coinbase transaction should only have one input and one output"
                else:
                    return None

        # Check if block containing corresponding output exists
        output_block_index = 0
        with open('./blockchain/blockchain.json') as f:
            data = json.load(f)
            for block in data:
                if block['header'] == tx_input['previous_output']:
                    output_block_index = data.index(block)
                    data = None
                    f.close()
                    break
            if data is None:
                return f"output file in transaction {transaction_dict['tx_id']} not found"

        # Check that the corresponding output is addressed to the sender of this transaction
        with open('./blockchain/blockchain.json', 'r') as f:
            data = json.load(f)

            previous_transaction = data[output_block_index]['transactions'][tx_input['previous_output'][1]]
            previous_output = previous_transaction['outputs'][tx_input['previous_output'][2]]

            if previous_output['pk_script'] != transaction_dict['sender']:
                return f"An output of transaction {transaction_dict['tx_id']} is not addressed to the sender"

            input_sum += int(previous_output['value'])
            f.close()

        # Check all mempool transactions for double-spend
        with open('./mempool/mempool.json', 'r') as f:
            data = json.load(f)
            for tx in data:
                for mempool_previous_output in tx['inputs']:
                    if mempool_previous_output['previous_output'] == tx_input['previous_output']:
                        return f"Output in transaction [{transaction_dict['tx_id']}] is already redeemed in mempool"
            f.close()

        # Check all blockchain transactions for double-spend
        with open('./blockchain/blockchain.json', 'r') as f:
            data = json.load(f)
            for block in data:
                for tx in block['transactions']:
                    for blockchain_previous_output in tx['inputs']:
                        if blockchain_previous_output['previous_output'] == tx_input['previous_output']:
                            return f"Output in transaction [{transaction_dict['tx_id']}] " \
                                   f"is already redeemed in the blockchain"

    # Outputs validation
    for tx_output in transaction_dict['outputs']:
        output_sum += tx_output['value']

    # Output of transaction should not exceed input
    if output_sum > input_sum:
        return f"The total output [{output_sum}] is greater than the total input [{input_sum}] in " \
               f"transaction [{transaction_dict['tx_id']}]"

    return None


def find_transaction_sum(transaction_dict):
    input_sum = 0
    output_sum = 0

    for tx_input in transaction_dict['inputs']:
        # Check if block containing corresponding output exists
        output_block_index = 0
        with open('./blockchain/blockchain.json') as f:
            data = json.load(f)
            for block in data:
                if block['header'] == tx_input['previous_output']:
                    output_block_index = data.index(block)
                    data = None
                    break
            if data is None:
                return f"output file in transaction {transaction_dict['tx_id']} not found"

            # Find input sum
            data = json.load(f)

            previous_transaction = data[output_block_index]['transactions'][tx_input['previous_output'][1]]
            previous_output = previous_transaction['outputs'][tx_input['previous_output'][2]]

            input_sum += int(previous_output['value'])
            f.close()

        for tx_output in transaction_dict['outputs']:
            output_sum += tx_output['value']

    return input_sum, output_sum


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

    # Check that the first transaction in the block is the coinbase transaction
    if block_dict['transactions'][0]['inputs'][0]['previous_output'][0] != 'COINBASE':
        return "First transaction in block should be COINBASE transaction"

    # Verify that coinbase output has value of block_reward plus fees
    block_remainder = 0
    for transaction in block_dict['transactions']:

        # Skip this pass for the coinbase transaction
        if block_dict['transactions'].index(transaction) == 0:
            continue

        tx_input_sum, tx_output_sum = find_transaction_sum(transaction)

        block_remainder += (tx_input_sum - tx_output_sum)

    if block_dict['transactions'][0]['outputs'][0]['value'] != block_reward + block_remainder:
        return "COINBASE transaction should have single output with a value of the block reward plus the" \
               " remainder of all transactions in the block"

    # Check that header matches the previous block
        # Remove the first transaction in the previous block in the directory, hash it,
        # and make sure it matches the header of this block

    # Check that nonce is valid...
        # Hash this block without the coinbase transaction and make sure its within the node's threshold

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
        data = json.dumps(data, indent=4, sort_keys=False)
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
        if index < len(transactions) + 1:
            return None
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
