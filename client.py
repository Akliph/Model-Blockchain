import requests
import json

data = requests.get('http://127.0.0.1:1337/node/tx/currentmempool')
print(data.json())
# The get_json() method in flask can parse json into a dict from a request object or a string
# This method cannot parse a dict object send through a request back into a dict object
# So once you add all of the data to your valid dict, stringify it before you post it.

