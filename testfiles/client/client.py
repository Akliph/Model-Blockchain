"""
This file is meant to be a fully working mining client to interact with the REST api defined in the node-files
directory. Other client software can be written to mine and transact with the API however.
"""
import json
from Crypto.PublicKey import RSA
import os
import requests
from hashlib import sha256
from pprint import pprint
from time import sleep
from uuid import uuid4
from sys import argv

NODE_URL = 'http://127.0.0.1:1337/'
CLIENT_MODE = ''
TRANSACTION_GOAL = 10
PUBKEY, PRIVKEY, EXPKEY = (None, None, None)

if not os.path.exists('./credentials'):
    print("Generating new keys...")
    keys = RSA.generate(bits=2048)
    print("2048 bit keys have been generated...")

    EXPKEY = keys.e
    PRIVKEY = keys.d
    PUBKEY = keys.n

    # Create the directory
    os.mkdir('./credentials')

    # Create new file and close it
    with open('./credentials/key.pem', 'wb+') as f:
        passcode = str(input("Please enter a password to encode your keys (THEY CANNOT BE RECOVERED IF YOU LOSE IT): "))
        f.write(keys.export_key('PEM', passphrase=passcode))
        f.close()

    print("Keys written...")

else:
    with open('./credentials/key.pem', 'r') as f:
        print("Reading Keys...")
        while True:
            try:
                passcode = str(input("Please enter your password: "))
                keys = RSA.import_key(f.read(), passphrase=passcode)
            except:
                print("Wrong password, please try again.")
                continue
            break

        f.close()

    EXPKEY = keys.e
    PRIVKEY = keys.d
    PUBKEY = keys.n

    print("Keys loaded")

print(f"Your public key is: {PUBKEY}")
print(f"Your exponent is:  {EXPKEY}")

"""
Transaction Submission
"""


# Creates a new transaction dict
def create_transaction(outputs, fee):
    # output = [value, pk]
    # Find and store utxo of this client's pk
    utxo = requests.post(f'{NODE_URL}/node/chain/utxo', str(PUBKEY)).json()
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
                'pk_script': output[1]
            }
        )

    # Pay the client funds back to this client
    if remainder > 0:
        transaction['outputs'].append(
            {
                'value': remainder,
                'pk_script': PUBKEY
            }
        )

    print(f"Remainder of {remainder} will be payed back to this key ({PUBKEY})")

    # Fill out the remainder fields
    transaction['sender'] = PUBKEY
    transaction['tx_id'] = str(uuid4().hex)

    # Remove the user data object and create a hash of the transaction
    transaction_hash = transaction.copy()
    del transaction_hash['user_data']
    transaction_hash = hash_transaction(transaction_hash)

    return transaction, transaction_hash


# Add a user_data dict to the end of the transaction with a valid signature
def sign_transaction(transaction, transaction_hash):
    signature = pow(int.from_bytes(transaction_hash, byteorder='big'), PRIVKEY, PUBKEY)
    transaction['user_data']['pk'] = [PUBKEY, EXPKEY]
    transaction['user_data']['signature'] = signature

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
    block['height'] = last_block['height'] + 1
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
    coinbase_transaction['outputs'][0]['pk_script'] = PUBKEY
    coinbase_transaction['tx_id'] = str(uuid4().hex)

    # Insert the coinbase transaction at the top of the block
    block['transactions'].insert(0, coinbase_transaction)

    # Block should be complete
    print("BLOCK IS COMPLETED--")
    pprint(block)
    print("--------------------")

    # Find the nonce based on this nodes block difficulty
    mining_timer = 2
    hash_string = ""
    for i in range(node_parameters['difficulty']):
        hash_string += "0"

    for i in range(mining_timer + 1):
        print("Starting mining in: " + str(mining_timer - i))
        sleep(1)

    while hash_dict(block)[:node_parameters['difficulty']] != hash_string:
        print(f"Nonce: {block['nonce']} ")
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


print("UTXO OF THIS CLIENT IS...")
print(requests.post(f"{NODE_URL}/node/chain/utxo", str(PUBKEY)).json())

while CLIENT_MODE != 'MINE' and CLIENT_MODE != 'TRANSACT' and CLIENT_MODE != 'CANCEL':
    CLIENT_MODE = str(input("Choose client mode: [TRANSACT/MINE] "))
    print("Client mode: " + CLIENT_MODE)

if CLIENT_MODE == 'MINE':
    print("Constructing Block...")
    sleep(0.5)
    create_block()

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
print(requests.post(f"{NODE_URL}/node/chain/utxo", str(PUBKEY)).json())
print("UTXO OF ADDRESS (1): ")
print(requests.post(f"{NODE_URL}/node/chain/utxo", '1').json())
print("UTXO OF ADDRESS (2): ")
print(requests.post(f"{NODE_URL}/node/chain/utxo", '2').json())
