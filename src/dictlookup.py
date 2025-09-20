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

dict_retries = config['dictlookup_retries']
dict_backoff = config['dictlookup_backoff']

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

def timeout_word_request(word_input, timeout=15):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(Word.request, word_input)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            globalfuncs.logger.notice(f"[warn] Word.request('{word}') timed out after {timeout}s")
            raise TimeoutError

def safe_request_word(word: str, retries: int = dict_retries, backoff: float = dict_backoff, try_llm=True, empty_ins_break=True):
    if word in cache_responses:
        globalfuncs.logger.debug(f"Using main cached word '{word}'")
        return cache_responses

    for attempt in range(1, retries + 1):
        try:
            # response = Word.request(word)
            response = timeout_word_request(word)
            # Make sure we got usable data
            if response and getattr(response, "data", None):
                cache_responses[word] = response
                return response
            else:
                globalfuncs.logger.notice(f"[warn] Empty response for '{word}', attempt {attempt}/{retries}")
                if empty_ins_break:
                    break
        except requests.exceptions.JSONDecodeError:
            globalfuncs.logger.notice(f"[warn] Invalid JSON for '{word}', attempt {attempt}/{retries}")
        except TimeoutError:
            globalfuncs.logger.notice(f"[warn] Timeout for '{word}', attempt {attempt}/{retries}")
        except Exception as e:
            globalfuncs.logger.warning(f"[warn] Error for '{word}': {e}, attempt {attempt}/{retries}")

        # exponential backoff + jitter
        sleep_time = backoff * (2 ** (attempt - 1)) + random.random()
        time.sleep(sleep_time)

    # use llm to find def for fallback
    if try_llm:
        globalfuncs.logger.notice(f"[warn] No response found for '{word}', trying to use LLM")
        with _llm_lock:
            if word in safe_request_word.llm_cache:
                globalfuncs.logger.debug(f"Using LLM cached word '{word}'")
                return safe_request_word.llm_cache[word]

            call_llm()
            llm_output = str(llmjptoen.get_definition_of_phrase(word))
            if word not in safe_request_word.llm_cache:
                safe_request_word.llm_cache.update({word: llm_output})
                cache_responses[word] = llm_output
            return llm_output
    else:
        globalfuncs.logger.warning(f"[warn] No response found for '{word}', returning None")
        return 'No definition found'


def tokenize(lyric: str) -> tuple[list, list]:
    # get all tokens
    response = str(Tokens.request(lyric))

    # fall back parsing
    if response == 'None':
        globalfuncs.logger.notice(f"Tokenizing fail, falling back for: {str(lyric)}")
        tagged = splittag.full_parse_jp_text(lyric)

        all_words = []
        all_pos = []

        for item in tagged:
            all_words.append(item[0])
            all_pos.append(splittag.translate_pos(item[1]))

    else:
        all_words = re.findall(r"\'([\u3040-\u30FF\u4E00-\u9FFF]+?)\'", response)
        all_pos = re.findall(r"(?:\<PosTag\.\w+?\:\s)\'([a-zA-Z]+?)\'", response)

    globalfuncs.logger.spam(f'{all_words} | {all_pos}')

    return all_words, all_pos

def get_definition(word: str, pos: str):
    if re.search(r'[\[\]\(\)\{\}\.\,]', word):
        globalfuncs.logger.verbose(f"Word isn't in japanese: {word}")
        return None
    # check if english
    if re.search(r'[a-zA-Z]', word):
        globalfuncs.logger.verbose(f"Word isn't in japanese: {word}")
        return None

    globalfuncs.logger.spam(f"Finding definition for {word}")
    response = safe_request_word(word)

    if response == 'None' or response is None or response == '':
        globalfuncs.logger.notice(f"[warn] Error while fetching definition of '{word}' using library, trying to use LLM")
        with _llm_lock:
            if word in safe_request_word.llm_cache:
                globalfuncs.logger.debug(f"Using LLM cached word '{word}'")
                return safe_request_word.llm_cache[word]

            call_llm()
            llm_output = str(llmjptoen.get_definition_of_phrase(word))
            if word not in safe_request_word.llm_cache:
                safe_request_word.llm_cache.update({word: llm_output})
                cache_responses[word] = response

    if response == 'No definition found':
        return 'No definition found'

    # fallback system from safe_request_word()
    if type(response) is str:
        return list(response)
    meanings = []

    # find words that are properly fit in context using pos checks and reading checks
    for entry in response.data:
        for jp in entry.japanese:
            if jp.reading == word or entry.slug == word or splittag.lemmatize(word) == jp.reading or splittag.lemmatize(word) == entry.slug or pos is None:
                for sense in entry.senses:
                    for sub_sense in sense.parts_of_speech:
                        if pos.lower() in sub_sense.lower() or pos is None:
                            if sub_sense.lower() != 'wikipedia definition':
                                meanings.append(sense.english_definitions)
            else: continue

        continue

    # looser checks to find more definitions
    if len(meanings) == 0:
        response = safe_request_word(word)

        for entry in response.data:

            for sense in entry.senses:
                for sub_sense in sense.parts_of_speech:
                    if sub_sense.lower() != 'wikipedia definition':
                        meanings.append(sense.english_definitions)

    # find all definitions for fallback
    if len(meanings) == 0:
        response = safe_request_word(word)

        for entry in response.data:
            for sense in entry.senses:
                    if 'wikipedia definition' not in str(sense.parts_of_speech).lower():
                        meanings.append(sense.english_definitions)

    unique_meanings = []

    # delete duplicates
    for item in meanings:
        if item not in unique_meanings:
            unique_meanings.append(item)

    globalfuncs.logger.success(f"Got definition for {word}: {unique_meanings}")
    return unique_meanings

def get_line_meaning_tag(lyric: str, timeout=15) -> tuple[list, list, list]:
    words, pos = tokenize(lyric)

    if len(words) == 0 and len(pos) == 0:
        words, pos = [lyric], []

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(get_definition, words, pos))

    return words, pos, results

def get_meaning_full(lyrics: list[str]):
    call_llm.counter = 0
    safe_request_word.llm_cache = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(get_line_meaning_tag, lyrics))

    safe_request_word.cache_clear()
    llmjptoen.clear_model()
    return results
# endregion

# region local pull
def get_meaning_full_jamdict(input_lyrics: list[str], use_jisho_tokenization=False):
    results = []

    if not use_jisho_tokenization:
        @functools.lru_cache(maxsize=None)
        def get_definition_local(word: str) -> str:
            jmd = Jamdict()

            if word == '':
                return None

            if re.match(r'\[|\]|\(|\)|\.|\,|\?|\"|\'|\}|\{|\「|\」|\『|\』|\【|\】|\？|\-|\_|\+|\=|\&|\!|\、', word):
                return None

            if re.match(r'[a-zA-Z0-9]', word):
                return None

            meaning = jmd.lookup(word)
            globalfuncs.logger.spam(f"'{word}' | {meaning}")

            if re.match(r'No entries', str(meaning)):
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
            else:
                return meaning

        get_definition_local.llm_cache = {}

        def get_definition_line_local(lyric: str) -> str:
            tagged_lyrics = splittag.full_parse_jp_text(lyric)

            globalfuncs.logger.verbose(f"'{lyric}' | {tagged_lyrics}")

            tagged_lyrics = [x[0] for x in tagged_lyrics]

            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(get_definition_local, tagged_lyrics))

            return results

        print(input_lyrics)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(get_definition_line_local, input_lyrics))

            print(results)

    if use_jisho_tokenization: #! NOT RECOMMENDED
        with ThreadPoolExecutor(max_workers=200) as executor:
            results = list(executor.map(tokenize, input_lyrics))
            print(results)
# endregion