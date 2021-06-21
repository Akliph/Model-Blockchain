"""
Server.py is meant to run the flask server, route all of the requests, and call the necessary methods
for handling incoming data. As little internal logic as possible will be done in this file, it is meant
mostly to handle the networking part of this project.
"""

from flask import Flask, request
import json
import node
import blockchain

"""
Initialization
"""

app = Flask(__name__)
blockchain.initialize()
node.initialize()

"""
Routing
"""


# [GET] requests

# Returns the entire current blockchain as stringified json with code 200
@app.route('/node/chain/currentchain', methods=['GET'])
def return_current_chain():

    chain_data = blockchain.get_block(all_blocks=True)
    return chain_data, 200


# Returns the entire mempool as stringified json with code 200
@app.route('/node/tx/currentmempool', methods=['GET'])
def return_current_mempool():
    mempool_data = node.get_tx(all_tx=True)
    return json.dumps(mempool_data), 200


# Returns a formatted template block as stringified json with code 200
@app.route('/node/template/block', methods=['GET'])
def return_block_template():
    data = blockchain.get_block_template()
    return data, 200


# Returns a formatted template transaction as stringified json with code 200
@app.route('/node/template/tx', methods=['GET'])
def return_tx_template():
    data = blockchain.get_transaction_template()
    return data, 200


# Returns this nodes ip address
@app.route('/node/info/address', methods=['GET'])
def return_node_address():
    # returns this nodes address as a string with code 200
    pass


# Returns this nodes unique id
@app.route('/node/info/id', methods=['GET'])
def return_node_id():
    # returns this nodes UUID as a string with code 200
    pass

# [POST] requests

# Returns 200 if the block was valid and adds it to the blockchain, but 400 and an error message if it wasn't
@app.route('/node/chain/submit', methods=['POST'])
def submit_to_blockchain():
    # sends data to node.py for validation on blockchain. If valid it returns string 'valid' with code 200.
    # If not valid it returns string describing error with code 400.
    pass


# Returns 200 if the transaction was valid and adds it to the mempool, but 400 and an error message if it wasn't
@app.route('/node/tx/submit', methods=['POST'])
def submit_to_mempool():
    # sends data to node.py for validation in mempool. If valid it returns string 'valid' with code 200.
    # If not valid it returns string describing error with code 400.
    data = request.get_json(force=True)
    res = node.add_to_mempool(data)

    # Using the check_equal operator because any data type returns true, but only booleans == True
    if res and type(res) == bool:
        return 'valid', 200
    else:
        return res, 400


# Receives an entire stringified blockchain from another node and returns 200 if this node was updated
@app.route('/node/chain/broadcast', methods=['POST'])
def receive_chain_broadcast():
    # receives entire blockchain. If other nodes is longer and valid it returns string 'updated' with code 200
    # If not then it returns a string describing error with code 400.
    pass


# Receives an entire stringified mempool from another node and returns 200 if this node was updated
@app.route('/node/tx/broadcast', methods=['POST'])
def receive_tx_broadcast():
    # receives entire mempool. If other nodes is longer and valid it returns string 'updated' with code 200
    # If not then it returns a string describing error with code 400.
    pass


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=1337)

