"""
Node.py is meant to handle most of the internal node logic. Methods for validating incoming transactions
and requests are defined here, and use server.py as an entry point. Dynamic information like calculated
block difficulty, median block time, block difficulty, UTXO(maybe), MEMPOOL, etc. are all calculated and stored
in a node config file here.


**NOTE
Various user-defined parameters are available via vargs to allow the ledger protocol to change based on
votes cast with computational power contributed to the system. "If you like the way a node does things,
you send your blocks to it for validation, therefore endorsing its protocol."
"""
import os
import json
from blockchain import Blockchain


class Node:
    @staticmethod
    def initialize():
        # Create mempool directory
        if not os.path.isdir('./mempool'):
            os.mkdir('./mempool')

        if not os.path.isfile('./mempool/mempool.json'):
            with open('./mempool/mempool.json', 'w+') as f:
                data = []
                f.write(json.dumps(data))
                f.close()

    @staticmethod
    def add_to_mempool(transaction_dict):

        # Data validation pass
        example_dict = Blockchain.get_transaction_template()
        example_keys = list(example_dict.keys())
        transaction_keys = list(transaction_dict.keys())

        # Root keys check
        for key in example_keys:
            if key not in transaction_keys:
                return "[Improper formatting] Not all required keys present. Check the example-json folder."
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

        # Add to mempool file
        with open('./mempool/mempool.json', 'r+') as f:
            data = json.load(f)
            data.append(transaction_dict)
            data = json.dumps(data, indent=4)
            f.seek(0)
            f.write(data)
            f.truncate()
            f.close()
            return True

    @staticmethod
    def get_tx_from_mempool(all_tx=False, index=-1, tx_id=None):
        # Writes all blocks to one json file and returns it
        if all_tx:
            transactions = json.load(open('./mempool/mempool.json', 'r'))
            return transactions

        # If index is specified and header is not then return file at index
        if index >= 0 and tx_id is None:
            transactions = json.load(open('./mempool/mempool.json', 'r'))
            return transactions

        # If header is specified and index is not then find file with name header
        elif tx_id is not None and index < 0:
            transactions = json.load(open('./mempool/mempool.json', 'r'))
            for tx in transactions:
                if id == tx['tx_id']:
                    return tx
            return None

        return None
