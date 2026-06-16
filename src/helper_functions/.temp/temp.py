import pprint
import json
import re
import ast

data = {'tag': 'span', 'data': {'name': '参照G'}, 'content': ['→', {'tag': 'span', 'data': {'name': '参照'}, 'content': {'tag': 'span', 'data': {'name': 'ref'}, 'content': {'tag': 'a', 'href': '?query=鈴&wildcards=off', 'content': ['れい', {'tag': 'span', 'data': {'name': '参照漢字'}, 'content': '（鈴）'}]}}}]}








data = re.sub("false", "False", repr(data))
data = ast.literal_eval(data)

print(json.dumps(data, indent=4, ensure_ascii=False))