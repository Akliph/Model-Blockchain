"""
Node.py is meant to handle most of the internal node logic as well as be the sole manager of mempool management.
Methods for validating incoming transactions and requests are defined here and mainly called from server.py.
Dynamic information like calculated block difficulty, mean block time, block difficulty, UTXO, MEMPOOL, etc.
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

-- Digital signature
All transactions will include a 'user-data' component containing the public key 'pk' and 'signature' of the hash of this
transaction without the 'user-data' component.

The signing algorithm used is the Elliptic Curve Digital Signing Algorithm with the SECP256k1 curve. This is more secure
than using RSA and is in line with Bitcoin's BIP32 protocol.

Public Keys double as addresses to send coins to. If there are inputs in a transaction that do not belong to the public
key provided in the 'user-data' or if the signature of the transaction cannot be verified with the Public Key provided,
then the transaction is invalid.

"""

import os
import json
import blockchain
import ecdsa

block_reward = 1000
block_difficulty = None
block_transaction_minimum = None
block_transaction_maximum = None


# Create directories and assign node parameters
def initialize(difficulty=1, tx_min=0, tx_max=10):
    # Setting the values of the node parameters
    # (I know using global state is bad but these arent constants and need to be accessible by this entire module...)
    # (in order for it to adjust over time. So for this purpose I think global state is a reasonable design choice.)
    # (And idk when nodes start communicating with each other this will probably be removed in place of nodes just...)
    # (calculating the parameters based on the current state of the blockchain.cd)
    global block_difficulty
    global block_transaction_minimum
    global block_transaction_maximum

    block_difficulty = difficulty
    block_transaction_minimum = tx_min
    block_transaction_maximum = tx_max

    # Create mempool directory
    if not os.path.isdir('./mempool'):
        os.mkdir('./mempool')

    if not os.path.isfile('./mempool/mempool.json'):
        with open('./mempool/mempool.json', 'w+') as f:
            data = []
            f.write(json.dumps(data))
            f.close()


"""
Data Verification
"""


# Returns a string describing the transaction verification error, otherwise returns None
def verify_transaction(transaction_dict):
    # Verify that the data is a dict
    if type(transaction_dict) is not dict:
        return "Must submit a stringified python dict!"

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

    # Check that transaction ID is a real number
    if len(transaction_dict['tx_id']) != 32:
        return f"Transaction id should be a hexadecimal uuid with 32 characters " \
               f"instead it was {transaction_dict['tx_id']}"

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
        transaction_found = False
        with open('./blockchain/blockchain.json') as f:
            data = json.load(f)
            for block in data:
                if data.index(block) == tx_input['previous_output'][0]:
                    output_block_index = data.index(block)
                    transaction_found = True
                    break

            if not transaction_found:
                return None

        # Check that the corresponding output is addressed to the sender of this transaction
        with open('./blockchain/blockchain.json', 'r') as f:
            data = json.load(f)

            previous_transaction = data[output_block_index]['transactions'][tx_input['previous_output'][1]]
            previous_output = previous_transaction['outputs'][tx_input['previous_output'][2]]

            if previous_output['pk_script'] != transaction_dict['user_data']['pk']:
                return f"An output of transaction {transaction_dict['tx_id']} is not addressed to the sender " \
                       f"[{transaction_dict['user_data']['pk']}]"

            input_sum += int(previous_output['value'])
            f.close()

        # Check all mempool transactions for double-spend
        with open('./mempool/mempool.json', 'r+') as f:
            data = json.load(f)
            for mempool_tx in data:

                # Skip this pass if this is the transaction being verified and remove it from the mempool
                if mempool_tx == transaction_dict:
                    del data[data.index(mempool_tx)]
                    continue

                for mempool_transaction_input in mempool_tx['inputs']:
                    if mempool_transaction_input['previous_output'] == tx_input['previous_output']:
                        return f"Output in transaction [{transaction_dict['tx_id']}] is already redeemed in mempool"
            f.seek(0)
            f.write(json.dumps(data, indent=4))
            f.truncate()
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
        # If an output value is less than 1 return error
        if tx_output['value'] < 1:
            return f"Output {tx_output} cannot have a value of less than 1"

        # If an output has more than 2 decimal places raise and error
        if '.' in str(tx_output['value']):
            if len(str(tx_output['value'])[str(tx_output['value']).index('.') + 1:]) > 2:
                return f"Value in output {tx_output} should be up to 2 decimal places long, " \
                       f"but it was {len(str(tx_output['value'])[str(tx_output['value']).index('.') + 1:])}"

        output_sum += tx_output['value']

    # Output of transaction should not exceed input
    if output_sum > input_sum:
        return f"The total output [{output_sum}] is greater than the total input [{input_sum}] in " \
               f"transaction [{transaction_dict['tx_id']}]"

    # RSA signature validation
    signing_error = verify_signature(transaction_dict)
    if signing_error is not None:
        return signing_error

    return None


# Returns a string describing the coinbase transaction verification error, otherwise returns None
def verify_coinbase_transaction(coinbase_dict):
    # Verify that the data is a dict
    if type(coinbase_dict) is not dict:
        return "Must submit a stringified python dict!"

    coinbase_example_dict = blockchain.get_coinbase_template()
    coinbase_example_keys = list(coinbase_example_dict.keys())

    # Root key check
    for key in coinbase_example_keys:
        if key not in coinbase_example_keys:
            return "Not all required keys in coinbase transaction"

        if type(coinbase_example_dict[key]) != type(coinbase_dict[key]):
            return f"Dict key, {key} should be {type(coinbase_example_dict[key])}, not {type(coinbase_dict[key])}"

    # Nested key check: inputs
    for key in list(coinbase_example_dict['inputs'][0].keys()):
        if key not in list(coinbase_example_dict['inputs'][0].keys()):
            return "Not all required keys in coinbase transaction inputs"

        if type(coinbase_example_dict['inputs'][0][key]) != type(coinbase_dict['inputs'][0][key]):
            return f"Dict key, {key} should be {type(coinbase_example_dict['inputs'][0][key])}, " \
                   f"not {type(coinbase_dict['inputs'][0][key])}"

    # Nested key check: outputs
    for key in list(coinbase_example_dict['outputs'][0].keys()):
        if key not in list(coinbase_example_dict['outputs'][0].keys()):
            return "Not all required keys in coinbase transaction inputs"

        if type(coinbase_example_dict['outputs'][0][key]) != type(coinbase_dict['outputs'][0][key]):
            return f"Dict key, {key} should be {type(coinbase_example_dict['outputs'][0][key])}, " \
                   f"not {type(coinbase_dict['outputs'][0][key])}"

    if len(coinbase_dict['inputs']) != 1 or len(coinbase_dict['outputs']) != 1:
        return "The coinbase transaction should have exactly one input and one output"

    # Output verification
    for tx_output in coinbase_dict['outputs']:
        if tx_output['value'] < 1:
            return f"The coinbase output value [{tx_output['value']}] should be a positive number"

        # If an output has more than 2 decimal places raise and error
        if '.' in str(tx_output['value']):
            if len(str(tx_output['value'])[str(tx_output).index('.') + 1:]) > 2:
                return f"Value in output {tx_output} should be up to 2 decimal places long, " \
                       f"but it was {len(str(tx_output['value'])[str(tx_output).index('.') + 1:])}"


    return None


# Returns the input and output sum of the transaction
def find_transaction_sum(transaction_dict):
    input_sum = 0
    output_sum = 0

    for tx_input in transaction_dict['inputs']:
        # Check if block containing corresponding output exists
        transaction_found = False
        with open('./blockchain/blockchain.json') as f:
            data = json.load(f)
            for block in data:
                if block['height'] == tx_input['previous_output'][0]:
                    output_block = block
                    transaction_found = True
                    break

            if not transaction_found:
                return None

            # Find input sum
            previous_transaction = output_block['transactions'][tx_input['previous_output'][1]]
            previous_output = previous_transaction['outputs'][tx_input['previous_output'][2]]

            input_sum += int(previous_output['value'])
            f.close()

    for tx_output in transaction_dict['outputs']:
        output_sum += tx_output['value']

    return input_sum, output_sum


# Returns a string describing the block verification error, otherwise returns None
def verify_block(block_dict):
    # Verify that the data is a dict
    if type(block_dict) is not dict:
        return "Must submit a stringified python dict!"
    block_keys = list(block_dict.keys())
    example_dict = blockchain.get_block_template()
    example_keys = list(example_dict.keys())

    # Root key check
    for key in example_keys:
        if key not in block_keys:
            return "Not all required keys present. Check the example-json folder."

    # Verify transaction in blocks
    for transaction in block_dict['transactions']:
        # Skip this pass for the coinbase transaction
        if block_dict['transactions'][0] == transaction:
            continue

        verification_error = verify_transaction(transaction)
        if verification_error is not None:
            return verification_error

    # Verify that block height is correct
    current_chain = json.loads(blockchain.get_block(all_blocks=True))
    if block_dict['height'] != current_chain[-1]['height'] + 1:
        return "Block should contain block height of index in blockchain"

    # Check for minimum amount of transactions
    if len(block_dict['transactions']) - 1 < block_transaction_minimum:
        return f"This node requires that a block have at least [{block_transaction_minimum}] transaction(s)"
    elif len(block_dict['transactions']) - 1 > block_transaction_maximum:
        return f"This node requires that a block have at most [{block_transaction_maximum}] transaction(s)"

    # Check that the first transaction in the block is the coinbase transaction
    if block_dict['transactions'][0]['inputs'][0]['previous_output'][0] != 'COINBASE':
        return "First transaction in block should be COINBASE transaction"

    # Find the block fees
    block_remainder = 0
    for transaction in block_dict['transactions']:

        # Skip this pass for the coinbase transaction
        if block_dict['transactions'][0] == transaction:
            continue

        # Get the input and output of this transaction
        tx_sum = find_transaction_sum(transaction)

        if tx_sum is not None:
            tx_input_sum, tx_output_sum = tx_sum

        # Add the unaccounted difference to the block remainder
        block_remainder += (tx_input_sum - tx_output_sum)

    # Validate data in coinbase transaction
    verify_coinbase_transaction(block_dict['transactions'][0])

    # Ensure coinbase output has a value of fees + reward
    if block_dict['transactions'][0]['outputs'][0]['value'] != block_reward + block_remainder:
        return f"COINBASE transaction should have a single output with a value of the block reward [{block_reward}] " \
               f"plus the remainder [{block_remainder}] of all transactions " \
               f"in the block for a total of [{block_remainder + block_reward}]"

    # Make sure proof-of-work data included in block is valid
    with open('./blockchain/blockchain.json') as f:
        # Check that header matches the previous block
        data = json.load(f)

        # Hash the previous block in the directory
        previous_block = data[len(data) - 1]

        # Make sure it matches the header of this block
        previous_block_hash = blockchain.hash_dict_hex(previous_block)
        if block_dict['header'] != previous_block_hash:
            return f"Header of block does not match hash [{previous_block_hash}] of previous block"

        # Check that nonce is valid...
        block_hash = blockchain.hash_dict_hex(block_dict)
        # Hash this block with the nonce and make sure its within the node's threshold
        for character in block_hash[:block_difficulty]:
            if str(character) != '0':
                return f"Nonce [{block_dict['nonce']}] is invalid, hash of block must " \
                       f"start with [{block_difficulty}] zeroes"

    return None


# Verifies the signature of a transaction
def verify_signature(transaction_dict):
    transaction_hash = transaction_dict.copy()
    del transaction_hash['user_data']
    transaction_hash = blockchain.hash_dict_bytes(transaction_hash)

    vk = ecdsa.VerifyingKey.from_string(bytes.fromhex(transaction_dict['user_data']['pk']), curve=ecdsa.SECP256k1)
    sig = bytes.fromhex(transaction_dict['user_data']['signature'])
    if not vk.verify(sig, transaction_hash):
        return "Signature is invalid."

    return None


"""
Add data to directories
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
        return None


# Takes a block dict and adds it to the blockchain if verified
def add_to_blockchain(block):
    verification_error = verify_block(block)
    if verification_error is not None:
        return verification_error

    blockchain.add_block(block)
    return None


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


# Returns all of the current node parameters to the miner
def get_node_parameters():
    parameters = {
        'reward': block_reward,
        'difficulty': block_difficulty,
        'tx_minimum': block_transaction_minimum,
        'tx_maximum': block_transaction_maximum
    }

    return parameters


# Find UTXO of public key on blockchain or blockchain and mempool
# modes = ['confirmed', 'unconfirmed']
def get_utxo(public_key, mode):
    # Valid type check
    if type(public_key) is not str:
        return f"Public key must be type [{str}] but got [{type(public_key)}]"

    if mode not in ['confirmed', 'unconfirmed']:
        return "['mode'] must be equal to ['confirmed'], or ['unconfirmed']"

    unspent_transactions = []
    utxo_sum = 0

    # Check just the blockchain
    if mode == 'confirmed':
        with open('./blockchain/blockchain.json') as f:
            data = json.load(f)

            for block in data:
                for tx in block['transactions']:
                    # For every transaction output, if it is addressed to this public key, add it to the list
                    for output in tx['outputs']:
                        tx_output_sum = 0
                        if output['pk_script'] == public_key:
                            unspent_transactions.append(([data.index(block), block['transactions'].index(tx),
                                                          tx['outputs'].index(output)], output['value']))

                    # For every transaction input, if it already exists on the blockchain and it is in the list, then
                    # remove it from the list
                    for tx_input in tx['inputs']:
                        for unspent_transaction in unspent_transactions:
                            if tx_input['previous_output'] == unspent_transaction[0]:
                                unspent_transactions.remove(unspent_transaction)

            for unspent_transaction in unspent_transactions:
                utxo_sum += unspent_transaction[1]

            f.close()

    # Check the mempool and the blockchain
    elif mode == 'unconfirmed':
        with open('./blockchain/blockchain.json') as f:
            data = json.load(f)

            for block in data:
                for tx in block['transactions']:
                    # For every transaction output, if it is addressed to this public key, add it to the list
                    for output in tx['outputs']:
                        tx_output_sum = 0
                        if output['pk_script'] == public_key:
                            unspent_transactions.append(([data.index(block), block['transactions'].index(tx),
                                                         tx['outputs'].index(output)], output['value']))

                    # For every transaction input, if it already exists on the blockchain and it is in the list, then
                    # remove it from the list
                    for tx_input in tx['inputs']:
                        for unspent_transaction in unspent_transactions:
                            if tx_input['previous_output'] == unspent_transaction[0]:
                                unspent_transactions.remove(unspent_transaction)

            for unspent_transaction in unspent_transactions:
                utxo_sum += unspent_transaction[1]

            f.close()

        last_unspent_transaction_index = len(unspent_transactions)

        with open('./mempool/mempool.json') as f:
            data = json.load(f)

            # Mark the index of the last unspent transaction in the blockchain so you don't loop over all of them again
            # when adding the mempool transactions to the utxo_sum
            for tx in data:
                for output in tx['outputs']:
                    tx_output_sum = 0
                    if output['pk_script'] == public_key:
                        unspent_transactions.append(([tx['outputs'].index(output)], output['value']))

                    # For every transaction input, if it already exists on the blockchain and it is in the list, then
                    # remove it from the list
                    for tx_input in tx['inputs']:
                        for unspent_transaction in unspent_transactions:
                            if tx_input['previous_output'] == unspent_transaction[0]:
                                unspent_transactions.remove(unspent_transaction)

            for unspent_transaction in unspent_transactions[last_unspent_transaction_index:]:
                utxo_sum += unspent_transaction[1]

            f.close()

    utxo_dict = {
        'transactions': unspent_transactions,
        'sum': utxo_sum
    }

    return utxo_dict


# Find the maximum hash of the block to adjust the difficulty
