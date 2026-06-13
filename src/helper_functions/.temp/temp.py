import pprint
import json
import re
import ast

data = {'tag': 'div', 'content': '«漫画家»', 'style': {'fontWeight': 'bold', 'fontSize': '1.3em', 'color': '#e5007f'}, 'data': {'pixiv': 'series'}}





data = re.sub("false", "False", repr(data))
data = ast.literal_eval(data)

print(json.dumps(data, indent=4, ensure_ascii=False))