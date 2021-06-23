"""
Blockchain.py is meant to parse, read, and write data to the blockchain directory. There will be less
internal logic here than in Node.py. It will use only Node.py as an entry point, there will be no data
validation here. Information about the blockchain can be easily returned via functions in this file:
Blocks in total, transactions in block, transactions in total, etc.
"""

from datetime import datetime
from hashlib import sha256
import os
import json

"""
Initialization Functions
"""


# Initialization of file paths
def initialize():
    # Create blockchain directory
    if not os.path.exists('./blockchain'):
        os.mkdir('./blockchain')

    if not os.path.isfile('./blockchain/blockchain.json'):
        with open('./blockchain/blockchain.json', 'w+') as f:
            data = []
            json.dump(data, f)
            f.close()

        create_genesis()


# Writes a seed block with default values to the blockchain directory
def create_genesis():
    # If the blockchain json is empty, create a genesis block with no transactions
    template_block = get_block_template()

    with open('./blockchain/blockchain.json', 'r+') as f:
        data = json.load(f)
        data.append(template_block)
        data = json.dumps(data, indent=4)
        f.seek(0)
        f.write(data)
        f.truncate()
        f.close()


"""
Block getters and setters
"""


# Add a block to the blockchain directory
def add_block(block_dict):
    with open('./blockchain/blockchain.json', 'r+') as f:
        data = json.load(f)
        data.append(block_dict)
        data = json.dumps(data, indent=4)
        f.seek(0)
        f.write(data)
        f.truncate()
        f.close()


# Returns list or dict from the blockchain directory (all blocks, by index, or by header string)
def get_block(all_blocks=False, index=-1, header=None):
    # Writes all blocks to one json file and returns it
    if all_blocks:
        with open('./blockchain/blockchain.json', 'r') as f:
            data = f.read()
            f.close()
            return data

    # If index is specified and header is not then return file at index
    if index >= 0 and header is None:
        data = json.load(open('./blockchain/blockchain.json', 'r'))
        return data

    # If header is specified and index is not then find file with name header
    elif header is not None and index < 0:
        data = json.load(open('./blockchain/blockchain.json', 'r'))
        for block in data:
            if block['header'] == header:
                return block

        return None

    return None


"""
Template Getters
"""


# Returns a properly formatted json block with default values
def get_block_template():
    # Creates a block template with all of the dict keys
    # Load block
    block_data = json.load(open('../example-json/block.json', 'r'))

    # Set default block data
    block_data['header'] = 0
    block_data['height'] = 0
    block_data['timestamp'] = datetime.timestamp(datetime.now())
    block_data['transactions'] = []
    block_data['nonce'] = 0

    return block_data


# Returns a properly formatted json transaction with default values
def get_transaction_template():
    # Returns a transaction template with all of the dict keys
    tx_data = json.load(open('../example-json/transaction.json', 'r'))

    # Set default transaction data
    tx_data['tx_id'] = ''
    tx_data['locktime'] = 0.0
    tx_data['sender'] = ''
    tx_data['inputs'][0]['previous_output'] = []
    tx_data['inputs'][0]['signature_script'] = ''
    tx_data['outputs'][0]['value'] = 0
    tx_data['outputs'][0]['pk_script'] = ''
    tx_data['user_data']['pk'] = ''
    tx_data['user_data']['signature'] = ''

    return tx_data


# Returns a template of a coinbase transaction
def get_coinbase_template():
    coinbase_data = json.load(open('../example-json/coinbase_transaction.json'))

    coinbase_data['tx_id'] = ''
    coinbase_data['locktime'] = 0.0
    coinbase_data['sender'] = ''
    coinbase_data['inputs'][0]['previous_output'] = ['COINBASE']
    coinbase_data['inputs'][0]['signature_script'] = None
    coinbase_data['outputs'][0]['value'] = 0
    coinbase_data['outputs'][0]['pk_script'] = ''

    return coinbase_data


"""
Hashing Functions
"""


# Returns a hash object of any dict object
def hash_dict(dictionary):
    # Turn dict into string and return its hash
    dict_data = json.dumps(dictionary, sort_keys=True)
    dict_hash = sha256(dict_data.encode()).hexdigest()

    return str(dict_hash)
