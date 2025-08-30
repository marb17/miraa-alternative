import MeCab
import unidic_lite

wakati = MeCab.Tagger("-Owakati")

def parse_jp_text(text):
    return wakati.parse(text).split()

tagger = MeCab.Tagger()
def full_parse_jp_text(text):
    return tagger.parse(text).split()