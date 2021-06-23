"""
This file is meant to be a fully working mining client to interact with the REST api defined in the node-files
directory. Other client software can be written to mine and transact with the API however.
"""
import json
from hashlib import sha256
import requests
from pprint import pprint
from time import sleep
from random import randint

NODE_URL = 'http://127.0.0.1:1337/'
USER_PK = str(sha256(str("Alex Giberson").encode()).hexdigest())


def create_transaction(tx_id, locktime, sender, inputs, outputs):
    res = requests.get('http://127.0.0.1:1337/node/template/tx').json()
    res['tx_id'] = str(tx_id)
    res['locktime'] = float(locktime)
    res['sender'] = str(sender)
    res['inputs'] = inputs
    res['outputs'] = outputs

    return res


def create_transaction_input(previous_output, sig_script):
    if type(previous_output) != list or len(previous_output) != 3:
        return "previous_output argument should be list of [output's block index, outputs tx index, outputs index]"

    tx_input = {
        'previous_output': previous_output,
        'signature_script': sig_script
    }

    return tx_input


def create_transaction_output(value, pk_script):
    tx_output = {
        'value': int(value),
        'pk_script': pk_script
    }

    return tx_output


# Returns the input and output sum of the transaction
def find_transaction_sum(transaction_dict, current_chain):
    input_sum = 0
    output_sum = 0

    for tx_input in transaction_dict['inputs']:
        # Check if block containing corresponding output exists
        output_block_index = 0
        data = current_chain
        for block in data:
            if data.index(block) == tx_input['previous_output'][0]:
                output_block_index = data.index(block)
                break

        # Find input sum
        data = current_chain

        previous_transaction = data[output_block_index]['transactions'][tx_input['previous_output'][1]]
        previous_output = previous_transaction['outputs'][tx_input['previous_output'][2]]

        input_sum += int(previous_output['value'])

        for tx_output in transaction_dict['outputs']:
            output_sum += tx_output['value']

    return input_sum, output_sum


# Returns a hash object of any dict object
def hash_dict(dictionary):
    # Turn dict into string and return its hash
    dict_data = json.dumps(dictionary, sort_keys=True)
    dict_hash = sha256(dict_data.encode()).hexdigest()

    return str(dict_hash)


def create_block():
    # To create a block...
    # Request all mempool transactions
    mempool_transactions = requests.get(f'{NODE_URL}/node/tx/currentmempool').json()
    print("CURRENT MEMPOOL--")
    print(type(mempool_transactions))
    pprint(mempool_transactions)
    print('--------------------')
    # Request all node parameters
    node_parameters = requests.get(f"{NODE_URL}/node/info/parameters").json()
    print("CURRENT PARAMETERS--")
    print(type(node_parameters))
    pprint(node_parameters)
    print('--------------------')
    # Request the entire blockchain
    current_blockchain = requests.get(f"{NODE_URL}/node/chain/currentchain").json()
    print("CURRENT BLOCKCHAIN--")
    print(type(current_blockchain))
    pprint(current_blockchain)
    print('--------------------')

    # Find enough transactions to satisfy the node tx_threshold parameter
    print("FINDING TRANSACTIONS TO ADD TO BLOCK")
    current_transactions = []
    for tx in mempool_transactions:
        if len(current_transactions) > node_parameters['tx_threshold']:
            break
        current_transactions.append(tx)
        print(f"TRANSACTION [{tx['tx_id']}] WILL BE ADDED TO BLOCK")
        print("**")
    print("--------------------")

    # Find the most recent block and hash it to get the header of this block
    last_block = current_blockchain[-1]
    last_block_hash = hash_dict(last_block)
    print(f"THE HASH OF THE MOST RECENT BLOCK IS [{last_block_hash}]")
    print("--------------------")

    # Create a coinbase transaction and add it to the block first
    coinbase_transaction = requests.get(f"{NODE_URL}/node/template/coinbase").json()
    print("REQUESTED NEW COINBASE TRANSACTION--")
    pprint(coinbase_transaction)
    print("--------------------")

    # Request a new block template
    block = requests.get(f"{NODE_URL}/node/template/block").json()
    block['header'] = last_block_hash
    print("REQUESTED NEW BLOCK TEMPLATE--")
    pprint(block)
    print("-------------------")

    # Add all of the transactions pulled from the mempool
    for tx in current_transactions:
        block['transactions'].append(tx)
    print("ADDED ALL PENDING TRANSACTIONS TO BLOCK")
    print("-------------------")

    # Find the block fees by subtracting the sum of all transaction inputs by the sum of all transaction outputs
    total_input = 0
    total_output = 0

    for tx in block['transactions']:
        tx_sum = find_transaction_sum(tx, current_blockchain)

        total_input += int(tx_sum[0])
        total_output += int(tx_sum[1])

    print("FOUND BLOCK TOTAL INPUT AND OUTPUT--")
    print(f"INPUT: {total_input} :: OUTPUT: {total_output}")
    print(f"FEES: {total_input - total_output}")
    print("-------------------")

    # Make the value of the coinbase transaction output equal to the block reward plus the block fees
    coinbase_transaction['inputs'][0]['previous_output'] = ["COINBASE"]
    coinbase_transaction['outputs'][0]['value'] = node_parameters['reward'] + (total_input - total_output)
    coinbase_transaction['outputs'][0]['pk_script'] = USER_PK

    block['transactions'].insert(0, coinbase_transaction)

    # Block should be complete
    print("BLOCK IS COMPLETED--")
    pprint(block)
    print("--------------------")

    # Find the nonce based on this nodes block difficulty
    mining_timer = 3
    hash_string = ""
    for i in range(node_parameters['difficulty']):
        hash_string += "0"

    for i in range(mining_timer + 1):
        print("Starting mining in: " + str(mining_timer - i))
        sleep(1)

    while hash_dict(block)[:node_parameters['difficulty']] != hash_string:
        print(f"Nonce: {block['nonce']} :: Hash: {hash_dict(block)}")
        block['nonce'] += 1

    print("HASH FOUND--")
    print(f"NONCE: {block['nonce']}")
    print(f"HASH: {hash_dict(block)}")
    print("--------------------")

    # Submit the block
    print("BLOCK COMPLETED")
    pprint(block)
    print("SUBMITTING BLOCK...")
    print("-------------------")
    block_result = requests.post(f"{NODE_URL}/node/chain/submit", json.dumps(block)).text
    print("BLOCK RESULT--")
    pprint(block_result)


create_block()

