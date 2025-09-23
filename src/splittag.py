import MeCab
import unidic
from fugashi import Tagger
import re

# main functions
def full_output_split(text: str) -> tuple:
    lem_tagger = Tagger('-Owakati')
    return [word.surface for word in lem_tagger(text)], [word.feature.pos1 for word in lem_tagger(text)], [
        word.feature.lemma for word in lem_tagger(text)]

# full tag
def full_parse_jp_text(text):
    tagger = MeCab.Tagger()
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

def lemmatize(text: str) -> tuple:
    lem_tagger = Tagger('-Owakati')
    for word in lem_tagger.parse(text):
        return word.feature.lemma

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

if __name__ == '__main__':
    japanese_words_by_pos = [
        # 1 Nouns (名詞)
        ["犬", "学校", "本", "時間", "友達"],

        # 2 Proper nouns (固有名詞)
        ["東京", "太郎", "日本", "富士山", "マイクロソフト"],

        # 3 Pronouns (代名詞)
        ["私", "僕", "彼", "彼女", "あなた"],

        # 4 Numerals (数詞)
        ["一", "二", "三", "十", "百"],

        # 5 Counters (助数詞)
        ["人", "本", "匹", "枚", "回"],

        # 6 Ichidan verbs (一段動詞)
        ["食べる", "見る", "起きる", "信じる", "教える"],

        # 7 Godan verbs (五段動詞)
        ["書く", "遊ぶ", "話す", "待つ", "死ぬ"],

        # 8 Irregular verbs (不規則動詞)
        ["する", "来る", "行く", "ある", "おる"],

        # 9 Transitive verbs (他動詞)
        ["読む", "閉める", "始める", "止める", "作る"],

        # 10 Intransitive verbs (自動詞)
        ["開く", "始まる", "止まる", "眠る", "落ちる"],

        # 11 Auxiliary verbs (助動詞)
        ["ます", "たい", "ない", "られる", "た"],

        # 12 Copula / 判定詞
        ["だ", "です", "である", "だろう", "ではない"],

        # 13 I-adjectives (い形容詞)
        ["高い", "新しい", "暑い", "面白い", "大きい"],

        # 14 Na-adjectives (な形容詞 / 形容動詞)
        ["静か", "有名", "便利", "安全", "元気"],

        # 15 Taru-adjectives (古語・タル形)
        ["堂々たる", "断固たる", "確固たる", "勇敢たる", "崇高たる"],

        # 16 Adverbs (副詞)
        ["すぐに", "よく", "ときどき", "はっきり", "たまに"],

        # 17 Degree adverbs (程度副詞)
        ["とても", "かなり", "少し", "まったく", "ほとんど"],

        # 18 Conjunctions (接続詞)
        ["そして", "しかし", "だから", "また", "それに"],

        # 19 Case particles (格助詞)
        ["は", "が", "を", "に", "で"],

        # 20 Listing / coordination particles (並立助詞)
        ["と", "や", "か", "とか", "やら"],

        # 21 Auxiliary particles (副助詞)
        ["しか", "だけ", "こそ", "さえ", "まで"],

        # 22 Sentence-final particles (終助詞)
        ["ね", "よ", "ぞ", "か", "な"],

        # 23 Conjunctive particles (接続助詞)
        ["から", "ので", "けれど", "ながら", "つつ"],

        # 24 Pre-nominal words (連体詞)
        ["この", "その", "あの", "ある", "どの"],

        # 25 Prefixes (接頭辞)
        ["お", "ご", "不", "非", "超"],

        # 26 Suffixes (接尾辞)
        ["さん", "ちゃん", "さま", "的", "化"],

        # 27 Onomatopoeia (擬音語/擬態語)
        ["ドキドキ", "ワクワク", "ぺらぺら", "ごろごろ", "さらさら"],

        # 28 Interjections (感動詞)
        ["はい", "いいえ", "ああ", "おお", "やった"],

        # 29 Auxiliary nouns / nominalizers (補助名詞)
        ["こと", "もの", "ところ", "はず", "ため"],

        # 30 Honorific verbs (尊敬語)
        ["いらっしゃる", "なさる", "おっしゃる", "召し上がる", "ご覧になる"],

        # 31 Humble verbs (謙譲語)
        ["申す", "伺う", "差し上げる", "拝見する", "いたす"],

        # 32 Polite expressions (丁寧語 / 慣用表現)
        ["ありがとうございます", "すみません", "お願いします", "失礼します", "お疲れ様です"]
    ]
    pos_set = set()
    yup = []

    for pos in japanese_words_by_pos:
        for word in pos:
            for item, item2 in zip(full_output_split(word)[0], full_output_split(word)[1]):
                pos_set.add(item2)
                yup.append([item, item2])

    pos_set = list(pos_set)

    def uhhuh(pos):
        results = []
        counter = 1
        for item, item2 in yup:
            if pos == item2:
                if counter == 2:
                    return item, item2
                else:
                    counter += 1

    poop = []

    for item in pos_set:
        poop.append(uhhuh(item))

    print(poop)


