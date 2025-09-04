from jisho_api.kanji import Kanji
from jisho_api.word import Word
from jisho_api import scrape, word
from jisho_api.tokenize import Tokens
from jisho_api.sentence import Sentence
import json
import splittag
import re
from concurrent.futures import ThreadPoolExecutor
import requests
import time
import random

ly = ['[ギヴン「冬のはなし」歌詞]', '', '[ヴァース 1]', 'まだ溶けきれずに残った', '日陰の雪みたいな', '想いを抱いて生きてる', 'ねぇ、 僕はこの恋を', 'どんな言葉でとじたらいいの', '', '[コーラス]', 'あなたのすべてが', '明日を失くして', '永遠の中を彷徨っているよ', 'さよならできずに', '立ち止まったままの', '僕と一緒に', '', '[ヴァース 2]', 'まだ解けない魔法のような', 'それとも呪いのような', '重い荷物を抱えてる', 'ねぇ、僕はこの街で', 'どんな明日を探せばいいの', '嗚呼', '', '[ブリッジ]', '冷たい涙が空で凍てついて', 'やさしい振りして舞い落ちる頃に', '離れた誰かと誰かがいたこと', 'ただそれだけのはなし', '', '[コーラス]', 'あなたのすべてが', 'かたちを失くしても', '永遠に僕の中で生きてくよ', 'さよならできずに', '歩き出す僕と', 'ずつと一緒に']
# ly = ['嗚呼']
tag = [None, None, None, ['まだ', '溶け', 'きれ', 'ず', 'に', '残っ', 'た'], ['日陰', 'の', '雪', 'みたい', 'な'], ['想い', 'を', '抱い', 'て', '生き', 'てる'], ['ねぇ', '、', '僕', 'は', 'この', '恋', 'を'], ['どんな', '言葉', 'で', 'とじ', 'たら', 'いい', 'の'], None, None, ['あなた', 'の', 'すべて', 'が'], ['明日', 'を', '失くし', 'て'], ['永遠', 'の', '中', 'を', '彷徨っ', 'て', 'いる', 'よ'], ['さよなら', 'でき', 'ず', 'に'], ['立ち止まっ', 'た', 'まま', 'の'], ['僕', 'と', '一緒', 'に'], None, None, ['まだ', '解け', 'ない', '魔法', 'の', 'よう', 'な'], ['それ', 'と', 'も', '呪い', 'の', 'よう', 'な'], ['重い', '荷物', 'を', '抱え', 'てる'], ['ねぇ', '、', '僕', 'は', 'この', '街', 'で'], ['どんな', '明日', 'を', '探せ', 'ば', 'いい', 'の'], ['嗚呼'], None, None, ['冷たい', '涙', 'が', '空', 'で', '凍てつい', 'て'], ['やさしい', '振り', 'し', 'て', '舞い落ちる', '頃', 'に'], ['離れ', 'た', '誰', 'か', 'と', '誰', 'か', 'が', 'い', 'た', 'こと'], ['ただ', 'それ', 'だけ', 'の', 'はなし'], None, None, ['あなた', 'の', 'すべて', 'が'], ['かたち', 'を', '失くし', 'て', 'も'], ['永遠', 'に', '僕', 'の', '中', 'で', '生き', 'てく', 'よ'], ['さよなら', 'でき', 'ず', 'に'], ['歩き', '出す', '僕', 'と'], ['ずつと', '一緒', 'に']]
ftag = [None, None, None, [['まだ', 'adverb'], ['溶け', 'verb (general)'], ['きれ', 'verb (non-independent)'], ['ず', 'auxiliary verb'], ['に', 'case particle'], ['残っ', 'verb (general)'], ['た', 'auxiliary verb']], [['日陰', 'common noun'], ['の', 'case particle'], ['雪', 'common noun'], ['みたい', 'adjectival noun stem'], ['な', 'auxiliary verb']], [['想い', 'common noun'], ['を', 'case particle'], ['抱い', 'verb (general)'], ['て', 'conjunctive particle'], ['生き', 'verb (general)'], ['てる', 'auxiliary verb']], [['ねぇ', 'interjection'], ['、', 'punctuation (comma)'], ['僕', 'pronoun'], ['は', 'binding particle'], ['この', 'adnominal'], ['恋', 'common noun (verbal noun)'], ['を', 'case particle']], [['どんな', 'adnominal'], ['言葉', 'common noun'], ['で', 'case particle'], ['とじ', 'verb (general)'], ['たら', 'auxiliary verb'], ['いい', 'adjective (non-independent)'], ['の', 'sentence-ending particle']], None, None, [['あなた', 'pronoun'], ['の', 'case particle'], ['すべて', 'common noun (adverbial use)'], ['が', 'case particle']], [['明日', 'common noun (adverbial use)'], ['を', 'case particle'], ['失くし', 'verb (general)'], ['て', 'conjunctive particle']], [['永遠', 'common noun'], ['の', 'case particle'], ['中', 'common noun (adverbial use)'], ['を', 'case particle'], ['彷徨っ', 'verb (general)'], ['て', 'conjunctive particle'], ['いる', 'verb (non-independent)'], ['よ', 'sentence-ending particle']], [['さよなら', 'interjection'], ['でき', 'verb (non-independent)'], ['ず', 'auxiliary verb'], ['に', 'case particle']], [['立ち止まっ', 'verb (general)'], ['た', 'auxiliary verb'], ['まま', 'common noun (adverbial use)'], ['の', 'case particle']], [['僕', 'pronoun'], ['と', 'case particle'], ['一緒', 'common noun (verbal noun)'], ['に', 'case particle']], None, None, [['まだ', 'adverb'], ['解け', 'verb (general)'], ['ない', 'auxiliary verb'], ['魔法', 'common noun'], ['の', 'case particle'], ['よう', 'adjectival noun stem'], ['な', 'auxiliary verb']], [['それ', 'pronoun'], ['と', 'case particle'], ['も', 'binding particle'], ['呪い', 'common noun'], ['の', 'case particle'], ['よう', 'adjectival noun stem'], ['な', 'auxiliary verb']], [['重い', 'adjective'], ['荷物', 'common noun'], ['を', 'case particle'], ['抱え', 'verb (general)'], ['てる', 'auxiliary verb']], [['ねぇ', 'interjection'], ['、', 'punctuation (comma)'], ['僕', 'pronoun'], ['は', 'binding particle'], ['この', 'adnominal'], ['街', 'common noun'], ['で', 'auxiliary verb']], [['どんな', 'adnominal'], ['明日', 'common noun (adverbial use)'], ['を', 'case particle'], ['探せ', 'verb (general)'], ['ば', 'conjunctive particle'], ['いい', 'adjective (non-independent)'], ['の', 'sentence-ending particle']], [['嗚呼', 'interjection']], None, None, [['冷たい', 'adjective'], ['涙', 'common noun (verbal noun)'], ['が', 'case particle'], ['空', 'common noun'], ['で', 'case particle'], ['凍てつい', 'verb (general)'], ['て', 'conjunctive particle']], [['やさしい', 'adjective'], ['振り', 'common noun (counter-like)'], ['し', 'verb (non-independent)'], ['て', 'conjunctive particle'], ['舞い落ちる', 'verb (general)'], ['頃', 'common noun (adverbial use)'], ['に', 'case particle']], [['離れ', 'verb (general)'], ['た', 'auxiliary verb'], ['誰', 'pronoun'], ['か', 'sentence-ending particle'], ['と', 'case particle'], ['誰', 'pronoun'], ['か', 'adverbial particle'], ['が', 'case particle'], ['い', 'verb (non-independent)'], ['た', 'auxiliary verb'], ['こと', 'common noun']], [['ただ', 'conjunction'], ['それ', 'pronoun'], ['だけ', 'adverbial particle'], ['の', 'case particle'], ['はなし', 'common noun (verbal noun)']], None, None, [['あなた', 'pronoun'], ['の', 'case particle'], ['すべて', 'common noun (adverbial use)'], ['が', 'case particle']], [['かたち', 'common noun'], ['を', 'case particle'], ['失くし', 'verb (general)'], ['て', 'conjunctive particle'], ['も', 'binding particle']], [['永遠', 'common noun'], ['に', 'case particle'], ['僕', 'pronoun'], ['の', 'case particle'], ['中', 'common noun (adverbial use)'], ['で', 'case particle'], ['生き', 'verb (general)'], ['てく', 'auxiliary verb'], ['よ', 'sentence-ending particle']], [['さよなら', 'interjection'], ['でき', 'verb (non-independent)'], ['ず', 'auxiliary verb'], ['に', 'case particle']], [['歩き', 'verb (general)'], ['出す', 'verb (non-independent)'], ['僕', 'pronoun'], ['と', 'case particle']], [['ずつと', 'adverb'], ['一緒', 'common noun (verbal noun)'], ['に', 'case particle']]]

def safe_request_word(word: str, retries: int = 15, backoff: float = 0.7):
    for attempt in range(1, retries + 1):
        try:
            response = Word.request(word)
            # Make sure we got usable data
            if response and getattr(response, "data", None):
                return response
            else:
                print(f"[warn] Empty response for '{word}', attempt {attempt}/{retries}")
        except requests.exceptions.JSONDecodeError:
            print(f"[warn] Invalid JSON for '{word}', attempt {attempt}/{retries}")
        except Exception as e:
            print(f"[warn] Error for '{word}': {e}, attempt {attempt}/{retries}")

        # exponential backoff + jitter
        sleep_time = backoff * (2 ** (attempt - 1)) + random.random()
        time.sleep(sleep_time)

    print(f"[error] Failed to fetch definition for '{word}' after {retries} retries")
    raise Exception(f"Failed to fetch definition for '{word}'")


def tokenize(lyric: str) -> tuple[list, list]:
    # get all tokens
    response = str(Tokens.request(lyric))

    if response == 'None':
        tagged = splittag.full_parse_jp_text(lyric)

        all_words = []
        all_pos = []

        for item in tagged:
            all_words.append(item[0])
            all_pos.append(splittag.translate_pos(item[1]))

    else:
        all_words = re.findall(r"\'([\u3040-\u30FF\u4E00-\u9FFF]+?)\'", response)
        all_pos = re.findall(r"(?:\<PosTag\.\w+?\:\s)\'([a-zA-Z]+?)\'", response)

    return all_words, all_pos

def get_definition(word: str, pos: str):
    print(word)
    response = safe_request_word(word)

    meanings = []

    for entry in response.data:
        # show kanji + hiragana readings
        for jp in entry.japanese:
            if jp.reading == word or entry.slug == word or splittag.lemmatize(word) == jp.reading or splittag.lemmatize(word) == entry.slug or pos is None:
                for sense in entry.senses:
                    for sub_sense in sense.parts_of_speech:
                        if pos.lower() in sub_sense.lower() or pos is None:
                            if sub_sense.lower() != 'wikipedia definition':
                                meanings.append(sense.english_definitions)
            else: continue

        continue

    if len(meanings) == 0:
        response = safe_request_word(word)

        for entry in response.data:

            for sense in entry.senses:
                for sub_sense in sense.parts_of_speech:
                    if sub_sense.lower() != 'wikipedia definition':
                        meanings.append(sense.english_definitions)

    if len(meanings) == 0:
        response = safe_request_word(word)

        for entry in response.data:
            for sense in entry.senses:
                    if 'wikipedia definition' not in str(sense.parts_of_speech).lower():
                        meanings.append(sense.english_definitions)

    unique_meanings = []

    for item in meanings:
        if item not in unique_meanings:
            unique_meanings.append(item)

    print(f"Got definition for {word}")
    return unique_meanings

def get_line_meaning_tag(lyric: str) -> tuple[list, list, list]:
    if '[' in lyric or lyric == '':
        return None

    words, pos = tokenize(lyric)

    if len(words) == 0 and len(pos) == 0:
        words, pos = [lyric], []

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(get_definition, words, pos))

    return words, pos, results

def get_meaning_full(lyrics: list[str]):
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(get_line_meaning_tag, lyrics))

    return results

if __name__ == '__main__':
    yup = get_meaning_full(ly)
    for item in yup:
        print(item)
