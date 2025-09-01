import MeCab
import unidic_lite

# tag type
wakati = MeCab.Tagger("-Owakati")

# half tagger, only splits
def parse_jp_text(text):
    return wakati.parse(text).split()

# full tag
tagger = MeCab.Tagger()
def full_parse_jp_text(text):
    return tagger.parse(text).split()