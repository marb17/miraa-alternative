import MeCab
import unidic_lite
import unidic
import fugashi
import re
from sudachipy import tokenizer, dictionary
import spacy
import ginza

# main functions
# tag type
wakati = MeCab.Tagger("-Owakati")

# half tagger, only splits
def morphemes_tag(text):
    return wakati.parse(text).split()

# full tag
tagger = MeCab.Tagger()
def full_parse_jp_text(text):
    if text is None:
        return None
    parsed = tagger.parse(text)
    parsed = re.sub(r'\t', ' ', parsed)
    parsed = re.sub(r'EOS', ' ', parsed)
    parsed = parsed.split('\n')
    result = []
    for item in parsed:
        if len(item) < 5:
            continue
        else:
            item = item.split(' ')
            word, _, _, _, type_of_word, *_ = item
            result.append([word, type_of_word])
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
        "補助記号-読点": "punctuation (comma)",
    }

    if pos in pos_map:
        return pos_map[pos]

    # fallback if not found in dictionary
    # if pos.startswith("名詞"):
    #     return "noun"
    # elif pos.startswith("動詞"):
    #     return "verb"
    # elif pos.startswith("形容詞"):
    #     return "adjective"
    # elif pos.startswith("形状詞"):
    #     return "adjectival noun"
    # elif pos.startswith("副詞"):
    #     return "adverb"
    # elif pos.startswith("助詞"):
    #     return "particle"
    # elif pos.startswith("助動詞"):
    #     return "auxiliary verb"
    # elif pos.startswith("接続詞"):
    #     return "conjunction"
    # elif pos.startswith("感動詞"):
    #     return "interjection"
    # elif pos.startswith("連体詞"):
    #     return "adnominal"
    # elif pos.startswith("補助記号"):
    #     return "symbol/punctuation"

    # fall back
    return pos

lem_tagger = fugashi.Tagger('-Owakati')
def lemmatize(text: str) -> str:
    for word in lem_tagger(text):
        return word.feature.lemma

nlp = spacy.load("ja_core_news_sm")

if __name__ == '__main__':
    pass