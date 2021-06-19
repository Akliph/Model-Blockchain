import json
import requests

data = requests.get('http://127.0.0.1:1337/node/template/tx')
print(data.json())
