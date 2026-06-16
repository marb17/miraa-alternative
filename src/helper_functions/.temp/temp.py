import pprint
import json
import re
import ast

data = {'tag': 'span', 'style': {'fontWeight': 'bold'}, 'data': {'name': '見出仮名'}, 'content': ['ち', {'tag': 'span', 'data': {'name': '活用分節'}, 'content': '・'}, 'ぶ']}





data = re.sub("false", "False", repr(data))
data = ast.literal_eval(data)

print(json.dumps(data, indent=4, ensure_ascii=False))