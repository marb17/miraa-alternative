from jamdict import Jamdict
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

llm_batch_size_dict_translation = config['llm_batch_size_dict_translation']

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
        jmd = Jamdict()

        # invalid checks
        if word == '':
            return None

        if re.match(r'\[|\]|\(|\)|\.|\,|\?|\"|\'|\}|\{|\「|\」|\『|\』|\【|\】|\？|\-|\_|\+|\=|\&|\!|\、', word):
            return None

        if re.match(r'[a-zA-Z0-9]', word):
            return None

        meaning = jmd.lookup(word).entries

        entries = []

        # empty check
        if re.search(r'No entries', str(meaning)):
            entries.append(True)
            globalfuncs.logger.notice("No entries found")
        else:
            # clean up output
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

            # empty check
            if len(entries) == 0:
                entries.append(True)
                globalfuncs.logger.notice(f"No entries found, len == 0 | {word} | {splittag.jamdict_translate_pos(pos)} | {meaning}")

            return entries

    get_definition_local.llm_cache = {}

    def get_definition_line_local(lyric: str) -> str:
        tagged_lyrics = splittag.full_parse_jp_text(lyric)

        globalfuncs.logger.verbose(f"'{lyric}' | {tagged_lyrics}")

        pos = [x[1] for x in tagged_lyrics]
        tagged_lyrics = [x[0] for x in tagged_lyrics]

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(get_definition_local, tagged_lyrics, pos))

        final_result = [tagged_lyrics, pos, results]
        return final_result

    globalfuncs.logger.verbose(input_lyrics)

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(get_definition_line_local, input_lyrics))

        globalfuncs.logger.success(results)

    # call llm for missing words
    def get_def_llm():
        nonlocal prompt_data

        counter = 0
        while True:
            try:
                call_llm()
                response = llmjptoen.batch_get_definition_of_phrase(prompt_data)
                break
            except Exception as e:
                globalfuncs.logger.notice(f"{e} | Error while fetching definition of '{prompt_data}'")

        prompt_data = []

        sub_break_off = False
        for main_counter in range(len(results)):
            lyric = input_lyrics[main_counter]
            words = [x[0] for x in splittag.full_parse_jp_text(lyric)]

            # find items that have true
            result_item = results[main_counter][2]
            for sub_counter in range(len(result_item)):
                if result_item[sub_counter] == [True] or result_item[sub_counter] == True or result_item[sub_counter] == ['True'] or result_item[sub_counter] == 'True':
                    # replace "true" items with llm meaning
                    result_item[sub_counter] = response[counter]
                    try:
                        if words[sub_counter] not in llm_cache:
                            llm_cache[f'{words[sub_counter]}'] = response[counter]
                    except Exception as e:
                        globalfuncs.logger.error(f"{words} | {result_item}")
                        raise Exception(f"{words} | {result_item}")
                    counter += 1
                    if counter == len(response):
                        sub_break_off = True
                        break
            if sub_break_off:
                break
            # write to main list
            results[main_counter][2] = result_item

    prompt_data = []
    llm_cache = {}
    while True:
        break_off = False
        finished = True

        for main_counter in range(len(results)):
            lyric = input_lyrics[main_counter]
            result_item = results[main_counter][2]
            words = [x[0] for x in splittag.full_parse_jp_text(lyric)]

            for sub_counter in range(len(result_item)):
                # caching system
                if words[sub_counter] in llm_cache and (result_item[sub_counter] == [True] or result_item[sub_counter] == True or result_item[sub_counter] == ['True'] or result_item[sub_counter] == 'True'):
                    globalfuncs.logger.verbose(f"Using cache for '{words[sub_counter]}'")
                    result_item[sub_counter] = llm_cache[words[sub_counter]]
                    results[main_counter][2] = result_item
                    prompt_data = []
                    break_off = True
                    break
                elif result_item[sub_counter] == [True] or result_item[sub_counter] == True or result_item[sub_counter] == ['True'] or result_item[sub_counter] == 'True':
                    # batching
                    prompt_data.append(words[sub_counter])
                    globalfuncs.logger.verbose(f"'{words[sub_counter]}'")

                if len(prompt_data) == llm_batch_size_dict_translation:
                    get_def_llm()
                    break_off = True
                    break

            if break_off:
                break

        if prompt_data:
            get_def_llm()

        # check if all defs have actual meanings
        for item in results[2]:
            for sub_item in item:
                if sub_item == [True]:
                    finished = False

        if finished:
            break

    return results

# endregion

if __name__ == '__main__':
    get_meaning_full_jamdict(['見えそうで見えない秘密は蜜の味', "今日何食べた？好きな本は？"])
    # uhhuh = [("たい", "助動詞"), ('犬', '名詞'), ('静か', '形状詞'), ('あの', '感動詞'), ('ある', '連体詞'), ('ない', '形容詞'), ('は', '助詞'), ('すぐ', '副詞'), ('食べる', '動詞'), ('私', '代名詞'), ('ます', '助動詞'), ('そして', '接続詞'), ('匹', '接尾辞'), ('本', '接頭辞')]
    #
    # for word, pos in uhhuh:
    #     print(get_meaning_full_jamdict([word]))