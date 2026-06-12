import pprint
import json

data = {'tag': 'span', 'title': 'spelling and reading variants', 'data': {'class': 'tag', 'content': 'forms-label'}, 'content': 'forms'}


print(json.dumps(data, indent=4, ensure_ascii=False))