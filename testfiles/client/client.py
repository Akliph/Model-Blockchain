"""
This file is meant to be a fully working mining client to interact with the REST api defined in the node-files
directory. Other client software can be written to mine and transact with the API however.
"""
import json
import sys
import os
import requests
import time
import ecdsa
from hashlib import sha256
from pprint import pprint
from uuid import uuid4


NODE_URL = 'http://127.0.0.1:1337/'
CLIENT_MODE = ''
TRANSACTION_GOAL = 10


# Initialize client RSA credentials
def initialize():
    # Set global key consts
    global sk
    global vk

    if not os.path.exists('./credentials'):
        print("Generating new keys...")
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()
        print("SECP256k1 Eliptic Curve keys have been generated...")

        # Create the directory
        os.mkdir('./credentials')

        # Create new file and close it
        with open('./credentials/key.pem', 'wb+') as f:
            f.write(sk.to_pem())
            f.close()

        print("Keys written...")

    else:
        with open('./credentials/key.pem', 'r') as f:
            print("Reading Keys...")
            sk = ecdsa.SigningKey.from_pem(f.read())
            f.close()

        vk = sk.get_verifying_key()

        print("Keys loaded")

    # Create the client_stats.json file
    if not os.path.isfile('./mining_benchmarks/client_stats.json'):
        with open('../mining_benchmarks/client_stats.json', 'w+') as f:
            data = []
            json.dump(data, f)
            f.close()

    print(f"Your public key address is: {vk.to_string().hex()}")


"""
Transaction Submission
"""


# Creates a new transaction dict
def create_transaction(outputs, fee):
    # output = [value, pk]
    # Find and store utxo of this client's pk
    utxo = requests.post(f'{NODE_URL}/node/chain/utxo', vk.to_string().hex()).json()
    print("UTXO of this key")
    pprint(utxo)

    # Get a transaction template
    transaction = requests.get(f'{NODE_URL}/node/template/tx').json()
    del transaction['inputs'][0]
    del transaction['outputs'][0]

    # Iterate over inputs until there is enough to cover the sum of all outputs
    sum_of_outputs = 0
    for output in outputs:
        sum_of_outputs += output[0]

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

    # Find the remainder of the client funds
    remainder = sum_of_inputs - (sum_of_outputs + fee)
    for output in outputs:
        transaction['outputs'].append(
            {
                'value': output[0],
                'pk_script': str(output[1])
            }
        )

    # Pay the client funds back to this client
    if remainder > 0:
        transaction['outputs'].append(
            {
                'value': remainder,
                'pk_script': vk.to_string().hex()
            }
        )

    print(f"Remainder of {remainder} will be payed back to this key ({vk.to_string().hex()})")

    # Fill out the remainder fields
    transaction['tx_id'] = str(uuid4().hex)

    # Remove the user data object and create a hash of the transaction
    transaction_hash = transaction.copy()
    del transaction_hash['user_data']
    transaction_hash = hash_transaction(transaction_hash)

    return transaction, transaction_hash


# Add a user_data dict to the end of the transaction with a valid signature
def sign_transaction(transaction, transaction_hash):
    signature = sk.sign(bytes(transaction_hash))
    transaction['user_data']['pk'] = vk.to_string().hex()
    transaction['user_data']['signature'] = signature.hex()

    return transaction


# Creates a new transaction output
def create_transaction_output(value, receiver):
    return [value, receiver]


"""
Block Submission
"""


def create_block():
    # To create a block...
    # Request all mempool transactions
    mempool_transactions = requests.get(f'{NODE_URL}/node/tx/currentmempool').json()

    # Request all node parameters
    node_parameters = requests.get(f"{NODE_URL}/node/info/parameters").json()
    print("CURRENT PARAMETERS--")
    print(node_parameters)
    print('--------------------')
    # Request the entire blockchain
    current_blockchain = requests.get(f"{NODE_URL}/node/chain/currentchain").json()

    # Find enough transactions to satisfy the node tx_threshold parameter
    current_transactions = []
    for tx in mempool_transactions:
        if len(current_transactions) >= TRANSACTION_GOAL or len(current_transactions) >= node_parameters['tx_maximum']:
            break
        current_transactions.append(tx)
        print(f"TRANSACTION [{tx['tx_id']}] WILL BE ADDED TO BLOCK")

    # Find the most recent block and hash it to get the header of this block
    last_block = current_blockchain[-1]
    last_block_hash = hash_dict(last_block)

    # Create a coinbase transaction and add it to the block first
    coinbase_transaction = requests.get(f"{NODE_URL}/node/template/coinbase").json()

    # Request a new block template
    block = requests.get(f"{NODE_URL}/node/template/block").json()
    block['header'] = last_block_hash
    block['height'] = last_block['height'] + 1

    # Add all of the transactions pulled from the mempool
    for tx in current_transactions:
        block['transactions'].append(tx)

    # Find the block fees by subtracting the sum of all transaction inputs by the sum of all transaction outputs
    total_input = 0
    total_output = 0

    for tx in block['transactions']:
        tx_sum = find_transaction_sum(tx, current_blockchain)

        total_input += int(tx_sum[0])
        total_output += int(tx_sum[1])

    print("BLOCK TOTAL INPUT AND OUTPUT--")
    print(f"INPUT: {total_input} :: OUTPUT: {total_output}")
    print(f"FEES: {total_input - total_output}")

    # Make the value of the coinbase transaction output equal to the block reward plus the block fees
    coinbase_transaction['inputs'][0]['previous_output'] = ["COINBASE"]
    coinbase_transaction['outputs'][0]['value'] = node_parameters['reward'] + (total_input - total_output)
    coinbase_transaction['outputs'][0]['pk_script'] = vk.to_string().hex()
    coinbase_transaction['tx_id'] = str(uuid4().hex)

    # Insert the coinbase transaction at the top of the block
    block['transactions'].insert(0, coinbase_transaction)

    # Find the nonce based on this nodes block difficulty
    hash_string = ""
    for i in range(node_parameters['difficulty']):
        hash_string += "0"

    # Mine the block and record the time it took
    start_time = time.time()
    while hash_dict(block)[:node_parameters['difficulty']] != hash_string:
        block['nonce'] += 1
    end_time = time.time()

    print("HASH FOUND--")
    print(f"TIME: {end_time-start_time}")
    print(f"NONCE: {block['nonce']}")
    print(f"HASH: {hash_dict(block)}")
    print("--------------------")

    # Submit the block
    print("BLOCK COMPLETED")
    print("SUBMITTING BLOCK...")
    print("-------------------")
    block_result = requests.post(f"{NODE_URL}/node/chain/submit", json.dumps(block)).text
    print("BLOCK RESULT--")
    pprint(block_result)

    # If the result was valid write information about how the client solved this block
    if block_result == 'valid':
        data = json.load(open('../mining_benchmarks/client_stats.json', 'r'))

        average_time = 0
        for entry in data:
            average_time += entry['block_time']

        average_time += end_time - start_time
        average_time = average_time/(len(data) + 1)

        client_data = {
            'block_time': end_time-start_time,
            'difficulty': node_parameters['difficulty'],
            'nonce': block['nonce'],
            'hash': hash_dict(block),
            'average_time': average_time
        }
        data.append(client_data)

        with open('../mining_benchmarks/client_stats.json', 'w+') as f:
            json.dump(data, f, indent=4)
            f.close()
        return True
    return False


"""
Misc Functions
"""


# Returns the input and output sum of the transaction
def find_transaction_sum(transaction_dict, current_chain):
    input_sum = 0
    output_sum = 0

    for tx_input in transaction_dict['inputs']:
        # Check if block containing corresponding output exists
        data = current_chain
        for block in data:
            if block['height'] == tx_input['previous_output'][0]:
                output_block = block
                break

        # Find input sum
        data = current_chain

        previous_transaction = output_block['transactions'][tx_input['previous_output'][1]]
        previous_output = previous_transaction['outputs'][tx_input['previous_output'][2]]

        input_sum += int(previous_output['value'])

    for tx_output in transaction_dict['outputs']:
        output_sum += tx_output['value']
        print(f"Adding {tx_output} to output sum for output #{transaction_dict['outputs'].index(tx_output)} "
              f"in transaction {transaction_dict['tx_id']}")

    return input_sum, output_sum


# Returns a hash hex digest of any dict object
def hash_dict(dictionary):
    # Turn dict into string and return its hash
    dict_data = json.dumps(dictionary, sort_keys=True)
    dict_hash = sha256(dict_data.encode()).hexdigest()

    return str(dict_hash)


# Returns a hash digest of any dict object
def hash_transaction(transaction):
    tx_data = json.dumps(transaction, sort_keys=True)
    dict_hash = sha256(tx_data.encode()).digest()

    return dict_hash


initialize()


print("UTXO OF THIS CLIENT IS...")
print(requests.post(f"{NODE_URL}/node/chain/utxo", str(vk.to_string().hex())).json())

while CLIENT_MODE not in ['MINE', 'TRANSACT', 'CANCEL']:
    CLIENT_MODE = str(input("Choose client mode: [TRANSACT/MINE] "))
    print("Client mode: " + CLIENT_MODE)

if CLIENT_MODE == 'MINE':
    block_loop = 0
    while block_loop < 1:
        try:
            block_loop = int(input("Number of blocks to mine: "))
        except:
            print("Enter a whole number value greater than 0...")

    i = block_loop
    while i > 0:
        print("Constructing Block...")
        if create_block():
            i -= 1
        print(block_loop - i)

if CLIENT_MODE == 'TRANSACT':
    output_count = None
    output_list = []
    transaction_fee = None

    # Get the amount of outputs in this transaction
    while type(output_count) is not int:
        try:
            output_count = int(input("Enter the number of outputs in your transaction: "))
        except:
            print("Enter a whole number...")
            continue
        break

    # Add all outputs to output list
    for j in range(output_count):
        output_value = None
        output_receiver = None

        while type(output_value) is not int:
            try:
                output_value = int(input("Enter the value of this output as a whole number: "))
            except:
                print("Enter a whole number...")
                continue

        while type(output_receiver) is not int:
            try:
                output_receiver = int(input("Enter the recipient's address as a whole number: "))
            except:
                print("Enter a whole number address...")
                continue

        output_list.append(create_transaction_output(output_value, output_receiver))

    # Get the desired mining fee
    while type(transaction_fee) is not int:
        try:
            transaction_fee = int(input("Enter a whole number for the mining fee: "))
        except:
            print("Enter a whole number address...")
            continue
        break

    final_transaction = create_transaction(output_list, transaction_fee)

    if len(final_transaction) == 2 and type(final_transaction) is tuple:
        final_transaction = sign_transaction(final_transaction[0], final_transaction[1])
        print(f"Transaction submitted: {json.dumps(final_transaction, indent=4)}")
    else:
        print(f"[ERROR]: {final_transaction}")

    print("Transaction Signed...")

    res = requests.post(f"{NODE_URL}/node/tx/submit", json.dumps(final_transaction))

    print("[RESPONSE]")
    print(res.text)

print("CURRENT BALANCE: ")
print(requests.post(f"{NODE_URL}/node/chain/utxo", str(vk.to_string().hex())).json())
print("UTXO OF ADDRESS (1): ")
print(requests.post(f"{NODE_URL}/node/chain/utxo", '1').json())
print("UTXO OF ADDRESS (2): ")
print(requests.post(f"{NODE_URL}/node/chain/utxo", '2').json())
