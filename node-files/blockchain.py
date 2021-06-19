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


class Blockchain:

    # Initialization of file paths
    @staticmethod
    def initialize():
        # Create blockchain directory
        if not os.path.exists('./blockchain'):
            os.mkdir('./blockchain')

        if not os.path.isfile('./blockchain/0.json'):
            create_genesis()

    # Add a block to the blockchain directory
    @staticmethod
    def add_block(block_dict):
        filename = block_dict['header']

        with open(filename + '.json', 'w+') as f:
            f.write(json.dumps(block_dict, indent=4))
            f.close()

    # Returns data from the blockchain directory (all blocks, by index, or by header string)
    @staticmethod
    def get_block(all_blocks=False, index=-1, header=None):
        files = os.listdir('./blockchain')

        # Writes all blocks to one json file and returns it
        if all_blocks:
            all_blocks = []
            for filename in files:
                f = open('./blockchain/' + filename, 'r')
                f_data = json.loads(f.read())
                all_blocks.append(f_data)
                f.close()
            return json.dumps(all_blocks)

        # If index is specified and header is not then return file at index
        if index >= 0 and header is None:
            data = json.load(open('./blockchain/' + files[index]))
            return data

        # If header is specified and index is not then find file with name header
        elif header is not None and index < 0:
            for filename in files:
                if filename == header:
                    data = json.load(open('./blockchain/' + filename))
                    return data
            return None

        return None

    # Returns a properly formatted json block with default values
    @staticmethod
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
    @staticmethod
    def get_transaction_template():
        # Returns a transaction template with all of the dict keys
        tx_data = json.load('/example-json/transaction.json')

        # Set default transaction data
        tx_data['tx_id'] = 0
        tx_data['locktime'] = 0
        tx_data['inputs'] = []
        tx_data['outputs'] = []

        return tx_data

    # Returns a hash object of any dict object
    @staticmethod
    def hash_dict(dictionary):
        # Turn dict into string and return its hash
        dict_data = json.dumps(dictionary, sort_keys=True)
        dict_hash = sha256(dict_data.encode())

        return dict_hash


# Defines how to create the seed block which is called in the initialization function
def create_genesis():
    # If the blockchain dir is empty, create a genesis block with no transactions
    template_block = Blockchain.get_block_template()
    filename = str(template_block['header'])

    with open('./blockchain/' + filename + '.json', 'w+') as f:
        f.write(json.dumps(template_block, indent=4, sort_keys=True))
        f.close()
