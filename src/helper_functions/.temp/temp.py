import pprint
import json
import re
import ast

data = [{'tag': 'span', 'data': {'name': '見出部'}, 'content': [{'tag': 'span', 'style': {'fontWeight': 'bold'}, 'data': {'name': '見出仮名'}, 'content': ['そう', {'tag': 'span', 'style': {'marginRight': 0.5}, 'data': {'name': '語構成'}}, 'りん']}, {'tag': 'span', 'style': {'fontSize': '0.6em'}, 'data': {'name': '歴史仮名'}, 'content': '(さう—)'}, {'tag': 'span', 'style': {'fontSize': '0.7em', 'verticalAlign': 'super', 'marginRight': 0.25, 'marginLeft': 0.25}, 'data': {'name': 'アクセントG'}, 'content': {'tag': 'span', 'data': {'name': 'アクセント'}, 'content': {'tag': 'span', 'data': {'name': 'accent'}, 'content': '[0]'}}}, {'tag': 'span', 'data': {'name': '表記G'}, 'content': ['【', {'tag': 'span', 'data': {'name': '標準表記'}, 'content': '相輪'}, '】']}]}, {'tag': 'div', 'data': {'name': '解説部'}, 'content': {'tag': 'div', 'data': {'name': '大語義'}, 'content': {'tag': 'div', 'data': {'name': '準大語義'}, 'content': {'tag': 'div', 'data': {'name': '中語義'}, 'content': {'tag': 'div', 'data': {'name': '語義G'}, 'content': {'tag': 'span', 'data': {'name': '語釈'}, 'content': ['仏塔の最上部にある装飾部分。下から露盤・伏鉢', {'tag': 'span', 'style': {'fontWeight': 'normal', 'fontSize': '0.6em', 'verticalAlign': 'super'}, 'data': {'name': 'ルビG'}, 'content': '(ふくばち)'}, '・請花', {'tag': 'span', 'style': {'fontWeight': 'normal', 'fontSize': '0.6em', 'verticalAlign': 'super'}, 'data': {'name': 'ルビG'}, 'content': '(うけばな)'}, '・九輪・水煙・竜舎・宝珠の七つから成る。相輪全体を九輪と称することもある。青銅製・鉄製・石製などがある。']}}}}}}, {'tag': 'div', 'style': {'marginTop': 0.5}, 'data': {'name': 'カットG'}, 'content': {'tag': 'div', 'data': {'name': 'カット'}, 'content': [{'tag': 'span', 'data': {'name': 'キャプション'}, 'content': '［相輪］'}, {'tag': 'span', 'data': {'name': 'image'}, 'content': {'tag': 'img', 'title': '', 'collapsible': True, 'collapsed': True, 'path': 'daijirin2/graphics/3djr_1469.png'}}]}}]





data = re.sub("false", "False", repr(data))
data = ast.literal_eval(data)

print(json.dumps(data, indent=4, ensure_ascii=False))