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

    pos_map = {
        # ===== NOUNS =====
        "名詞-普通名詞-一般": "noun (common) (futsuumeishi)",
        "名詞-普通名詞-副詞可能": "noun (common) (futsuumeishi)",  # Still a common noun
        "名詞-普通名詞-助数詞可能": "counter",  # Counter-like nouns
        "名詞-普通名詞-サ変可能": "noun or participle which takes the aux. verb suru",
        "名詞-固有名詞": "noun (common) (futsuumeishi)",  # No specific proper noun category in target

        # ===== PRONOUNS =====
        "代名詞": "pronoun",

        # ===== VERBS =====
        # Map to general verb categories since we don't know the specific conjugation class
        "動詞-一般": "verb unspecified",
        "動詞-非自立可能": "auxiliary verb",  # Non-independent verbs are usually auxiliary

        # ===== ADJECTIVES =====
        "形容詞-一般": "adjective (keiyoushi)",
        "形容詞-非自立可能": "auxiliary adjective",  # Non-independent adjectives
        "形状詞-助動詞語幹": "adjectival nouns or quasi-adjectives (keiyodoshi)",

        # ===== ADVERBIALS =====
        "連体詞": "pre-noun adjectival (rentaishi)",  # This is the exact match
        "副詞": "adverb (fukushi)",

        # ===== PARTICLES =====
        "助詞-格助詞": "particle",
        "助詞-副助詞": "particle",
        "助詞-接続助詞": "particle",
        "助詞-終助詞": "particle",
        "助詞-係助詞": "particle",
        "助詞": "particle",  # General fallback

        # ===== AUXILIARY =====
        "助動詞": "auxiliary verb",

        # ===== CONJUNCTION =====
        "接続詞": "conjunction",

        # ===== INTERJECTION =====
        "感動詞-一般": "interjection (kandoushi)",

        # ===== SYMBOLS/PUNCTUATION =====
        "補助記号-読点": "unclassified",  # No punctuation category in target, so unclassified

        # ===== ADDITIONAL MAPPINGS (in case you encounter them) =====
        # Numbers
        "名詞-数詞": "numeric",

        # Prefixes and suffixes
        "接頭詞": "prefix",
        "接尾詞": "suffix",

        # Other possible verb forms you might encounter
        "動詞-サ変": "suru verb - included",
        "動詞-カ変": "Kuru verb - special class",

        # Other adjective forms
        "形容動詞": "adjectival nouns or quasi-adjectives (keiyodoshi)",

        # Expressions
        "フィラー": "expressions (phrases, clauses, etc.)",
        "言いよどみ": "expressions (phrases, clauses, etc.)",

        # Symbols and punctuation
        "記号": "unclassified",
        "補助記号": "unclassified",
        "空白": "unclassified",
    }

    if pos in pos_map:
        return pos_map[pos]

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

lyrics = [
                "[YOASOBI「アイドル」歌詞]",
                "",
                "[Intro]",
                "無敵の笑顔で荒らすメディア",
                "知りたいその秘密ミステリアス",
                "抜けてるとこさえ彼女のエリア",
                "完璧で嘘つきな君は",
                "天才的なアイドル様",
                "(You're my savior, you're my saving grace)",
                "",
                "[Verse 1]",
                "今日何食べた？好きな本は？",
                "遊びに行くならどこに行くの？",
                "何も食べてない それは内緒",
                "何を聞かれてものらりくらり",
                "そう淡々と だけど燦々と",
                "見えそうで見えない秘密は蜜の味",
                "あれもないないない これもないないない",
                "好きなタイプは？相手は？さあ答えて",
                "",
                "[Pre-Chorus]",
                "「誰かを好きになること",
                "なんて私分からなくてさ」",
                "嘘か本当か知り得ない",
                "そんな言葉にまた一人堕ちる",
                "また好きにさせる",
                "",
                "[Chorus]",
                "誰もが目を奪われていく",
                "君は完璧で究極のアイドル",
                "金輪際現れない",
                "一番星の生まれ変わり",
                "Ah, その笑顔で愛してるで",
                "誰も彼も虜にしていく",
                "その瞳がその言葉が",
                "嘘でもそれは完全なアイ",
                "",
                "[Verse 2]",
                "はいはいあの子は特別です",
                "我々はハナからおまけです",
                "お星様の引き立て役 B です",
                "全てがあの子のお陰なわけない",
                "洒落臭い",
                "妬み嫉妬なんてないわけがない",
                "これはネタじゃない",
                "からこそ許せない",
                "完璧じゃない君じゃ許せない",
                "自分を許せない",
                "誰よりも強い君以外は認めない",
                "",
                "[Chorus]",
                "誰もが信じ崇めてる",
                "まさに最強で無敵のアイドル",
                "弱点なんて見当たらない",
                "一番星を宿している",
                "弱いとこなんて見せちゃダメダメ",
                "知りたくないとこは見せずに",
                "唯一無二じゃなくちゃイヤイヤ",
                "それこそ本物のアイ",
                "",
                "[Bridge]",
                "得意の笑顔で沸かすメディア",
                "隠しきるこの秘密だけは",
                "愛してるって嘘で積むキャリア",
                "これこそ私なりの愛だ",
                "流れる汗も綺麗なアクア",
                "ルビーを隠したこの瞼",
                "歌い踊り舞う私はマリア",
                "そう嘘はとびきりの愛だ",
                "",
                "[Pre-Chorus]",
                "誰かに愛されたことも",
                "誰かのこと愛したこともない",
                "そんな私の嘘がいつか本当になること",
                "信じてる",
                "",
                "[Chorus]",
                "いつかきっと全部手に入れる",
                "私はそう欲張りなアイドル",
                "等身大でみんなのこと",
                "ちゃんと愛したいから",
                "今日も嘘をつくの",
                "この言葉がいつか本当になる日を願って",
                "それでもまだ",
                "君と君にだけは言えずにいたけど",
                "",
                "[Outro]",
                "あぁ、やっと言えた",
                "これは絶対嘘じゃない",
                "愛してる",
                "(You're my savior, my true savior, my saving grace)"
            ]

if __name__ == '__main__':
    print(full_output_split('君と君にだけは言えずにいたけど')[0])
    # pos = set()
    #
    # for lyric in lyrics:
    #     for item in full_output_split(lyric)[1]:
    #         pos.add(item)
    #     print(full_output_split(lyric)[1])
    #
    # print()
    #
    # print(pos)
    #
    # print()
    #
    # print(natural_split('お星様の引き立て役 B です'))