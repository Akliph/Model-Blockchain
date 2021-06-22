"""
This file is meant to be a fully working mining client to interact with the REST api defined in the node-files
directory. Other client software can be written to mine and transact with the API however.
"""
import json
from hashlib import sha256
import requests
import pprint
from random import randint


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


inputs = [create_transaction_input([0, 0, 0], '0')]
outputs = [create_transaction_output(100, str(sha256('yo'.encode()).hexdigest()))]
tx = create_transaction('0', 0, '0', inputs, outputs)


response = requests.post('http://127.0.0.1:1337/node/tx/submit', json.dumps(tx))
print(response.text)

# The get_json() method in flask can parse json into a dict from a request object or a string
# This method cannot parse a dict object send through a request back into a dict object
# So once you add all of the data to your valid dict, stringify it before you post it.
