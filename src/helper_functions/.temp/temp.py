import pprint
import json
import re
import ast

data = {'type': 'structured-content', 'content': [{'tag': 'span', 'content': '飽きてうるさく煩わしく感じられる様子。我慢の限界を超えて嫌気がさし、やる気を失う様子。\n'}, {'tag': 'span', 'content': '「デート中も仕事や対人面の不満ばかりだと彼もウンザリ」\n'}, {'tag': 'span', 'style': {'fontWeight': 'bold'}, 'content': '類義語'}, {'tag': 'span', 'content': '「'}, {'tag': 'span', 'content': 'うざうざ'}, {'tag': 'span', 'content': '」'}, {'tag': 'span', 'content': '\n'}, {'tag': 'span', 'content': '小さい物がうるさいくらい密集する様子（「うじゃうじゃ」とも）。「'}, {'tag': 'span', 'content': {'tag': 'ruby', 'content': ['う', {'tag': 'rt', 'content': '･'}]}}, {'tag': 'span', 'content': 'ん'}, {'tag': 'span', 'content': {'tag': 'ruby', 'content': ['ざ', {'tag': 'rt', 'content': '･'}]}}, {'tag': 'span', 'content': 'り」とは中心となる音「うざ」が共通。これは「ぼやぼや」と「ぼんやり」の関係と同じ。現代語で「煩わしい」という意の「うざったい」「うざい」なども、「うざ」から派生した語。\n'}, {'tag': 'span', 'content': '➜'}, {'tag': 'span', 'content': '「'}, {'tag': 'span', 'content': {'tag': 'a', 'href': '?query=げんなり&wildcards=off', 'content': 'げんなり'}}, {'tag': 'span', 'content': '」'}, {'tag': 'span', 'content': '\n'}]}



data = re.sub("false", "False", repr(data))
data = ast.literal_eval(data)

print(json.dumps(data, indent=4, ensure_ascii=False))