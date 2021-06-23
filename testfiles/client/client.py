"""
This file is meant to be a fully working mining client to interact with the REST api defined in the node-files
directory. Other client software can be written to mine and transact with the API however.
"""
import json
import rsa
import os
import requests
from hashlib import sha256
from pprint import pprint
from time import sleep
from uuid import uuid4
from sys import argv

NODE_URL = 'http://127.0.0.1:1337/'
CLIENT_MODE = 'MINER'
TRANSACTION_GOAL = 10
PUBKEY, PRIVKEY = (None, None)

if not os.path.exists('./credentials'):
    PUBKEY, PRIVKEY = rsa.newkeys(512)

    # Create the directory
    os.mkdir('./credentials')

    # Create new file and close it
    f = open('./credentials/private-key.pem', 'w+')
    f.close()

    # Open the file in write-bytes mode and securely store the sk
    priv_key_file = open('./credentials/private-key.pem', 'wb+')
    priv_key_file.write(PRIVKEY.save_pkcs1('PEM'))
    priv_key_file.close()

    # Create new file and close it
    f = open('./credentials/public-key.pem', 'w+')
    f.close()

    # Open the file in write-bytes mode and securely store the pk
    priv_key_file = open('./credentials/public-key.pem', 'wb+')
    priv_key_file.write(PUBKEY.save_pkcs1('PEM'))
    priv_key_file.close()

else:
    with open('./credentials/private-key.pem', 'rb') as f:
        keydata = f.read()
        PRIVKEY = rsa.PrivateKey.load_pkcs1(keydata)
        f.close()
    with open('./credentials/public-key.pem', 'rb') as f:
        keydata = f.read()
        PUBKEY = rsa.PublicKey.load_pkcs1(keydata)
        f.close()

"""
Transaction Submission
"""


def create_transaction(outputs, fee):
    # output = [value, pk]
    # Find and store utxo of this client's pk
    utxo = requests.post(f'{NODE_URL}/node/chain/utxo', PUBKEY.save_pkcs1().decode('utf-8')).json()
    pprint(utxo)

    # Get a transaction template
    transaction = requests.get(f'{NODE_URL}/node/template/tx').json()
    del transaction['inputs'][0]
    del transaction['outputs'][0]

    # Iterate over inputs until there is enough to cover the sum of all outputs
    sum_of_outputs = 0
    for output in outputs:
        sum_of_outputs += output[0]

    # Check if the sum of all outputs is more than the entire sum of this client's UTXO
    if sum_of_outputs + fee > utxo['sum']:
        return f"Transaction failed, your account has [{utxo['sum']}] and the total output is [{sum_of_outputs}]"

    # Keep adding inputs until the sum is equal to or greater than the output
    # Keep track of the remainder so you can pay it back to yourself
    sum_of_inputs = 0
    for utxo_input in utxo['transactions']:
        transaction['inputs'].append(
            {
                'previous_output': utxo_input[0],
                'signature_script': '0'
            }
        )
        sum_of_inputs += utxo_input[1]

        pprint(json.dumps(utxo_input))

        if sum_of_inputs >= sum_of_outputs + fee:
            break

    print("INPUTS ADDED TO TRANSACTION..")
    pprint(transaction['inputs'])
    print("--------------------")

    # Pay the remainder to this client's pk
    remainder = sum_of_inputs - (sum_of_outputs + fee)
    for output in outputs:
        transaction['outputs'].append(
            {
                'value': output[0],
                'pk_script': output[1]
            }
        )

    transaction['outputs'].append(
        {
            'value': remainder,
            'pk_script': PUBKEY.save_pkcs1().decode('utf-8')
        }
    )

    print("OUTPUTS ADDED TO TRANSACTION..")
    pprint(transaction['outputs'])
    print(f"The remainder of the inputs is {remainder} which is paid back to this key")
    print("--------------------")

    # Fill out the remainder fields
    transaction['sender'] = PUBKEY.save_pkcs1().decode('utf-8')
    transaction['tx_id'] = str(uuid4().hex)

    # Remove the user data object and create a hash of the transaction

    transaction_hash = transaction
    del transaction_hash['user_data']
    transaction_hash = hash_dict(transaction_hash)
    sig = rsa.sign(transaction_hash.encode('utf-8'), PRIVKEY, 'SHA-256')
    # print("TRANSACTION SIGNED..")
    # print(str(sig))

    # Sign the transaction in the user data object and add it back
    user_data = {
        'pk': PUBKEY.save_pkcs1().decode('utf-8'),
        'signature': str(sig)
    }
    transaction['user_data'] = user_data

    pprint(transaction)
    # Submit the transaction
    signing_result = requests.post(f"{NODE_URL}/node/tx/submit", json.dumps(transaction))
    print(signing_result.text)


"""
Block Submission
"""


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
        if len(current_transactions) >= TRANSACTION_GOAL or len(current_transactions) >= node_parameters['tx_maximum']:
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
    coinbase_transaction['outputs'][0]['pk_script'] = PUBKEY.save_pkcs1('PEM').decode('utf-8')

    # Insert the coinbase transaction at the top of the block
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


"""
Misc Functions
"""


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


#create_block()
create_transaction([(10, '0')], 0)
#print("REQUESTING UTXO...")
#res = requests.post(f'{NODE_URL}/node/chain/utxo', PUBKEY.save_pkcs1().decode('utf-8'))
#print(res.json())
