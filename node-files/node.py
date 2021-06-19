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
