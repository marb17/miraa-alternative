import pprint
import json

data = {'tag': 'div', 'lang': 'ja', 'data': {'content': 'redirect-glossary'}, 'content': ['⟶', {'tag': 'a', 'href': '?query=%E6%AF%8E%E6%97%A5%E6%AF%8E%E6%97%A5&wildcards=off&primary_reading=%E3%81%BE%E3%81%84%E3%81%AB%E3%81%A1%E3%81%BE%E3%81%84%E3%81%AB%E3%81%A1', 'content': [{'tag': 'ruby', 'content': ['毎', {'tag': 'rt', 'content': 'まい'}]}, {'tag': 'ruby', 'content': ['日', {'tag': 'rt', 'content': 'にち'}]}, {'tag': 'ruby', 'content': ['毎', {'tag': 'rt', 'content': 'まい'}]}, {'tag': 'ruby', 'content': ['日', {'tag': 'rt', 'content': 'にち'}]}]}]}





print(json.dumps(data, indent=4, ensure_ascii=False))