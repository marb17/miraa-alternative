import pprint
import json
import re
import ast

data = [{'tag': 'span', 'content': '使い方', 'style': {'fontSize': '0.85em', 'verticalAlign': 'text-bottom', 'borderStyle': 'solid', 'borderRadius': '0.18em', 'borderWidth': '0.03em', 'marginRight': '0.25em', 'padding': '0.1em 0.25em 0em 0.2em', 'cursor': 'default'}}, {'tag': 'ul', 'content': [{'tag': 'li', 'content': [{'tag': 'span', 'content': '吉田松陰先生は、薫陶成性することが上手だったようで、すぐれた人材を世に送り出している。'}]}, {'tag': 'li', 'content': [{'tag': 'span', 'content': '健太くんの空手の先生は、礼儀作法を教えることで薫陶成性する。'}]}, {'tag': 'li', 'content': [{'tag': 'span', 'content': 'より多くの生徒を薫陶成性することで、僕の教え子たちが世の中をよくし、僕のやっていることは間接的に世のためになる。'}]}, {'tag': 'li', 'content': [{'tag': 'span', 'content': '薫陶成性するつもりはないんだろうけど、ともこちゃんの教え子はみな優れている。'}]}, {'tag': 'li', 'content': [{'tag': 'span', 'content': '健太くんは、どんな不良生徒でも薫陶成性することができる高い徳を持っている。'}]}], 'style': {'listStyleType': 'circle'}}]



data = re.sub("false", "False", repr(data))
data = ast.literal_eval(data)

print(json.dumps(data, indent=4, ensure_ascii=False))