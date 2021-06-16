"""
Server.py is meant to run the flask server, route all of the requests, and call the necessary methods
for handling incoming data. As little internal logic as possible will be done in this file, it is meant
mostly to handle the networking part of this project.
"""

from flask import Flask, request
import json

"""
Initialization
"""

app = Flask(__name__)

"""
Routing
"""


# [GET] requests
@app.route('node/chain/currentchain', ['GET'])
def return_current_chain():
    # returns the entire current blockchain as a json file with code 200
    pass


@app.route('node/tx/currentmempool', ['GET'])
def return_current_mempool():
    # returns the entire current mempool as a json file with code 200
    pass


@app.route('node/info/address', ['GET'])
def return_node_address():
    # returns this nodes address as a string with code 200
    pass


@app.route('node/info/id', ['GET'])
def return_node_id():
    # returns this nodes UUID as a string with code 200
    pass


# [POST] requests

@app.route('node/chain/submit', ['POST'])
def submit_to_blockchain():
    # sends data to node.py for validation on blockchain. If valid it returns string 'valid' with code 200.
    # If not valid it returns string describing error with code 400.
    pass


@app.route('node/chain/broadcast', ['POST'])
def receive_broadcast():
    # receives entire blockchain. If other nodes is longer and valid it returns string 'updated' with code 200
    # If not then it returns a string describing error with code 400.
    pass


@app.route('node/tx/submit', ['POST'])
def submit_to_mempool():
    # sends data to node.py for validation in mempool. If valid it returns string 'valid' with code 200.
    # If not valid it returns string describing error with code 400.
    pass


@app.route('node/tx/broadcast', ['POST'])
def receive_broadcast():
    # receives entire mempool. If other nodes is longer and valid it returns string 'updated' with code 200
    # If not then it returns a string describing error with code 400.
    pass


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=1337)
