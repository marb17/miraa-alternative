import MeCab
import unidic
from fugashi import Tagger
import re

# main functions
def full_output_split(text: str) -> tuple:
    lem_tagger = Tagger('-Owakati')
    return [word.surface for word in lem_tagger(text)], [word.feature.pos1 for word in lem_tagger(text)], [
        word.feature.lemma for word in lem_tagger(text)]
    del lem_tagger
# full tag
def full_parse_jp_text(text):
    if text is None:
        return None

    word, pos, _ = full_output_split(text)

    result = []
    for word, pos in zip(word, pos):
        result.append([word, pos])
    return result

def translate_pos(pos: str) -> str:
    pos_map = {
        # Common nouns
        "名詞-普通名詞-一般": "common noun",
        "名詞-普通名詞-副詞可能": "common noun (adverbial use)",
        "名詞-普通名詞-助数詞可能": "common noun (counter-like)",
        "名詞-普通名詞-サ変可能": "common noun (verbal noun)",

        # Pronoun
        "代名詞": "pronoun",

        # Proper noun (if it ever shows up)
        "名詞-固有名詞": "proper noun",

        # Verbs
        "動詞-一般": "verb (general)",
        "動詞-非自立可能": "verb (non-independent)",

        # Adjectives
        "形容詞-一般": "adjective",
        "形容詞-非自立可能": "adjective (non-independent)",

        # Adnominal (連体詞 is like "such", "this kind of")
        "連体詞": "adnominal",

        # Special "keiyoushi" form
        "形状詞-助動詞語幹": "adjectival noun stem",

        # Adverbs
        "副詞": "adverb",

        # Particles
        "助詞-格助詞": "case particle",
        "助詞-副助詞": "adverbial particle",
        "助詞-接続助詞": "conjunctive particle",
        "助詞-終助詞": "sentence-ending particle",
        "助詞-係助詞": "binding particle",
        "助詞": "particle",  # general fallback

        # Auxiliary verb
        "助動詞": "auxiliary verb",

        # Conjunction
        "接続詞": "conjunction",

        # Interjection
        "感動詞-一般": "interjection",

        # Symbols
        "補助記号-読点": "punctuation",
    }

    if pos in pos_map:
        return pos_map[pos]

    # fall back
    return pos

def jamdict_translate_pos(pos: str) -> str:
    pos_translation = {
        "助詞": "particle",
        "名詞": "noun",
        "動詞": "verb",
        "感動詞": "interjection",
        "連体詞": "pre-noun adjectival", #pre-nominal word (attributive)
        "形容詞": "adjective (keiyoushi)",
        "助動詞": "auxiliary", #auxiliary verb
        "接尾辞": "suffix",
        "代名詞": "pronoun",
        "副詞": "adverb",
        "形状詞": "adjectival nouns",
        "接続詞": "conjunction",
        "接頭辞": "prefix"
    }

    if pos in pos_translation:
        return pos_translation[pos]

    # fall back
    return pos

def natural_split(text: str) -> list:
    surface, pos, lemma = full_output_split(text)

    for _ in range(len(surface)):
        surface.append('')
        pos.append('')
        lemma.append('')

    final_output = []
    combined = 0

    pos_to_combine = [
        '助動詞',
        '接尾辞',
        '接頭辞'
    ]

    def is_in_pos_to_combine(pos: str) -> bool:
        if pos == 'None':
            return False
        for item in pos_to_combine:
            if re.match(item, pos):
                return True
        return False

    def is_prefix(pos: str) -> bool:
        if re.match(pos_to_combine[2], pos):
            return True
        return False

    for counter in range(len(surface) * 2):
        try:
            if is_in_pos_to_combine(pos[counter + combined + 1]):
                final_output.append(f"{surface[counter + combined]}{surface[counter + combined + 1]}")
                combined += 1
            elif is_prefix(pos[counter + combined]):
                final_output.append(f"{surface[counter + combined]}{surface[counter + combined + 1]}")
            else:
                final_output.append(surface[counter + combined])
        except IndexError:
            if is_in_pos_to_combine(pos[counter + combined]):
                final_output.append(surface[counter + combined])
            else:
                pass
            break

    return [str(token) for token in final_output if token != '']

def get_furigana(text: str) -> str:
    def kata_to_hira(katakana: str) -> str:
        # Convert all Katakana characters to Hiragana
        return ''.join(
            chr(ord(ch) - 0x60) if 'ァ' <= ch <= 'ン' else ch
            for ch in katakana
        )
    furi_tagger = Tagger('-Owakati')
    for word in furi_tagger(text):
        return kata_to_hira(word.feature.kana)

if __name__ == '__main__':
    pass