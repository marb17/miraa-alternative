import pprint
import json
import re
import ast

data = {'type': 'structured-content', 'content': [{'tag': 'span', 'data': {'name': '見出部'}, 'content': [{'tag': 'span', 'style': {'fontWeight': 'bold'}, 'data': {'name': '見出仮名'}, 'content': ['つむ', {'tag': 'span', 'style': {'marginRight': 0.5}, 'data': {'name': '語構成'}}, 'がた']}, {'tag': 'span', 'style': {'fontSize': '0.7em', 'verticalAlign': 'super', 'marginRight': 0.25, 'marginLeft': 0.25}, 'data': {'name': 'アクセントG'}, 'content': {'tag': 'span', 'data': {'name': 'アクセント'}, 'content': {'tag': 'span', 'data': {'name': 'accent'}, 'content': '[0]'}}}, {'tag': 'span', 'data': {'name': '表記G'}, 'content': ['【', {'tag': 'span', 'data': {'name': '標準表記'}, 'content': [{'tag': 'span', 'data': {'name': '熟字訓'}, 'content': '〈紡錘〉'}, '形']}, '】']}]}, {'tag': 'div', 'data': {'name': '解説部'}, 'content': {'tag': 'div', 'data': {'name': '大語義'}, 'content': {'tag': 'div', 'data': {'name': '準大語義'}, 'content': {'tag': 'div', 'data': {'name': '中語義'}, 'content': {'tag': 'div', 'data': {'name': '語義G'}, 'content': {'tag': 'span', 'data': {'name': '語釈'}, 'content': '紡錘に糸を巻いたときの形。ぼうすいけい。'}}}}}}]}





data = re.sub("false", "False", repr(data))
data = ast.literal_eval(data)

print(json.dumps(data, indent=4, ensure_ascii=False))