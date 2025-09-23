from jamdict import Jamdict
from jisho_api.kanji import Kanji
from jisho_api.word import Word
from jisho_api import scrape, word
from jisho_api.tokenize import Tokens
from jisho_api.sentence import Sentence
import json
import splittag
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import requests
import time
import random
import llmjptoen
import functools
import threading
import globalfuncs
import jamdict, jamdict_data

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

_llm_lock = threading.Lock()

cache_responses = {}

# region jisho website functions
def call_llm():
    if not hasattr(call_llm, "counter"):
        call_llm.counter = 0

    if call_llm.counter == 0:
        llmjptoen.create_model()
    else:
        globalfuncs.logger.debug("Skipping LLM initialization")

    call_llm.counter += 1

# region local pull
def get_meaning_full_jamdict(input_lyrics: list[str]):
    results = []

    @functools.lru_cache(maxsize=None)
    def get_definition_local(word: str, pos: str) -> str:
        def use_llm():
            with _llm_lock:
                if word in get_definition_local.llm_cache:
                    globalfuncs.logger.debug(f"Using LLM cached word '{word}'")
                    return get_definition_local.llm_cache[word]

                call_llm()
                while True:
                    try:
                        meaning = str(llmjptoen.get_definition_of_phrase(word))
                        break
                    except Exception as e:
                        globalfuncs.logger.notice(f"Error while fetching definition of '{word}' using LLM, retrying")
                if word not in get_definition_local.llm_cache:
                    get_definition_local.llm_cache.update({word: meaning})
                    cache_responses[word] = meaning
                return meaning

        jmd = Jamdict()

        if word == '':
            return None

        if re.match(r'\[|\]|\(|\)|\.|\,|\?|\"|\'|\}|\{|\「|\」|\『|\』|\【|\】|\？|\-|\_|\+|\=|\&|\!|\、', word):
            return None

        if re.match(r'[a-zA-Z0-9]', word):
            return None

        meaning = jmd.lookup(word).entries

        entries = []

        if re.search(r'No entries', str(meaning)):
            use_llm()
        else:
            jamdict_output = []
            for entry in meaning:
                translated_pos = str(splittag.jamdict_translate_pos(pos))
                if re.search(f"{translated_pos}", str(entry)):
                    formatted_entry = re.sub(r'(.*?):', '', str(entry)).strip()
                    formatted_entry = re.split(r'([0-9]+\.\s?.*?)', formatted_entry) # its a list now

                    for item in formatted_entry:
                        item = re.sub(r'(\(.*\))', '', item).strip()
                        if item != '' and not re.match(r'\d+\.', item):
                            jamdict_output.append(item)

            entries = jamdict_output

            if len(entries) == 0:
                entries.append(use_llm())

            return entries

    get_definition_local.llm_cache = {}

    def get_definition_line_local(lyric: str) -> str:
        tagged_lyrics = splittag.full_parse_jp_text(lyric)

        globalfuncs.logger.verbose(f"'{lyric}' | {tagged_lyrics}")

        pos = [x[1] for x in tagged_lyrics]
        tagged_lyrics = [x[0] for x in tagged_lyrics]

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(get_definition_local, tagged_lyrics, pos))

        return results

    globalfuncs.logger.verbose(input_lyrics)

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(get_definition_line_local, input_lyrics))

        globalfuncs.logger.success(results)


# endregion

if __name__ == '__main__':
    get_meaning_full_jamdict(['見えそうで見えない秘密は蜜の味', "今日何食べた？好きな本は？"])
    # uhhuh = [("たい", "助動詞"), ('犬', '名詞'), ('静か', '形状詞'), ('あの', '感動詞'), ('ある', '連体詞'), ('ない', '形容詞'), ('は', '助詞'), ('すぐ', '副詞'), ('食べる', '動詞'), ('私', '代名詞'), ('ます', '助動詞'), ('そして', '接続詞'), ('匹', '接尾辞'), ('本', '接頭辞')]
    #
    # for word, pos in uhhuh:
    #     print(get_meaning_full_jamdict([word]))