import pprint
import json
import re
import ast

data = [{'type': 'structured-content', 'content': [{'tag': 'span', 'content': '①子供などが声を張り上げて泣く声。甘えがある。\n'}, {'tag': 'span', 'content': '「犬に噛まれたと言って、子供のように『ああん、ああん』と泣きながら」\n'}, {'tag': 'span', 'content': '②口を大きく開ける様子。歯の治療時などに医者に言われる。\n'}, {'tag': 'span', 'content': '「さあ、口をあーんと開いて」\n'}, {'tag': 'span', 'style': {'fontWeight': 'bold'}, 'content': '類義語'}, {'tag': 'span', 'content': '「'}, {'tag': 'span', 'content': {'tag': 'a', 'href': '?query=わーん&wildcards=off', 'content': 'わーん'}}, {'tag': 'span', 'content': '」'}, {'tag': 'span', 'content': '「'}, {'tag': 'span', 'content': {'tag': 'a', 'href': '?query=あんあん&wildcards=off', 'content': 'あんあん'}}, {'tag': 'span', 'content': '」'}, {'tag': 'span', 'content': '\n'}, {'tag': 'span', 'content': '共に、①の類義語。「わーん」には甘えが少ない。「あんあん」は声の張り上げ方が弱い。\n'}]}]



data = re.sub("false", "False", repr(data))
data = ast.literal_eval(data)

print(json.dumps(data, indent=4, ensure_ascii=False))