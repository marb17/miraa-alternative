from transformers import BitsAndBytesConfig, AutoTokenizer, AutoModelForCausalLM
import torch
from dotenv import load_dotenv
import os
import json
import sentencepiece
import tiktoken
import accelerate
import gc
import bitsandbytes
import re
from colorama import Fore, Back, Style, init

# global config

init(autoreset=True) # for console colors

with open('globalconfig.json', 'r') as f:
    config = json.load(f)

model_name = config['large_model_name']

# bnb_config = BitsAndBytesConfig(load_in_4bit=True)
bnb_config = BitsAndBytesConfig(load_in_8bit=True)

# device setup
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# patterns for regex
META_PATTERNS = [
    r'(?i)\blyrics\b', r'歌詞', r'(?i)\bofficial\s*(video|audio)\b', r'(?i)\bmv\b',
    r'(?i)\bcolor\s*coded\b', r'(?i)\bver(\.|sion)?\b', r'(?i)\bfull\s*version\b',
    r'(?i)\bhd\b', r'(?i)\b4k\b', r'(?i)\blive\b', r'(?i)\bvisualizer\b',
    r'(?i)\bkan\|rom\|eng\b', r'(?i)\bromaji\b', r'(?i)\benglish\b', r'(?i)\bsubs?\b',
]

SEP_PATTERN = r'\s*[-–—\|]\s*'  # common "Artist - Title" separators

# main functions
def has_non_latin(s: str) -> bool:
    # returns True if string has chars that not latin
    return bool(re.search(r'[^\x00-\x7F]', s))

def strip_known_meta(s: str) -> str:
    # remove common junk tokens anywhere
    for pat in META_PATTERNS:
        s = re.sub(pat, '', s)
    # omit unesseary words
    s = re.sub(r'[\(\[\{]\s*(?i:from|official|mv|ver|version|lyrics|歌詞).*?[\)\]\}]', '', s)
    # collapse whitespace
    s = re.sub(r'\s{2,}', ' ', s).strip(' -–—|')
    return s.strip()

def clean_brackets_keep_core(s: str) -> str:
    # remove all bracketed content
    s = re.sub(r'[\(\[\{].*?[\)\]\}]', '', s)
    s = re.sub(r'\s{2,}', ' ', s).strip(' -–—|')
    return s.strip()

def pick_artist(chunk: str) -> str:
    chunk = chunk.strip()
    # if japanese in brackets, choose that first
    m = re.search(r'\(([^)]{1,60})\)', chunk)
    if m:
        inner = m.group(1).strip()
        if has_non_latin(inner):
            return inner
    # keep main text if no brackets
    no_paren = clean_brackets_keep_core(chunk)
    return no_paren or chunk

def pick_title(chunk: str) -> str:
    # remove metadata junk
    s = strip_known_meta(chunk)

    # collect bracketed stuff
    parens = re.findall(r'[\(\[\{](.*?)[\)\]\}]', s)

    # remove all parens
    base = clean_brackets_keep_core(s)

    # prefer japanese inside brackets
    for p in parens:
        if re.search(r'[\u3040-\u30FF\u4E00-\u9FFF]', p):  # Hiragana/Katakana/Kanji
            return p.strip()

    # 2. if base has japanese return that
    if re.search(r'[\u3040-\u30FF\u4E00-\u9FFF]', base):
        return base

    # 3. if base has romaji use
    if re.search(r'[A-Za-z]', base):
        return base

    # 4. final fallback
    for p in parens:
        if p.strip():
            return p.strip()
    return base


def extract_title_artist(text: str) -> str:
    t = text.strip()
    # fast path split on the first dash separator
    parts = re.split(SEP_PATTERN, t, maxsplit=1)
    if len(parts) == 2:
        left, right = parts[0], parts[1]
        artist = pick_artist(left)
        title = pick_title(right)
    else:
        # fallback heuristics if no dash found using by as split
        by = re.split(r'(?i)\s+by\s+', t, maxsplit=1)
        if len(by) == 2:
            title = pick_title(by[0])
            artist = pick_artist(by[1])
        else:
            # last-ditch treat leading quote as title
            m = re.search(r'“([^”]+)”|"([^"]+)"|『([^』]+)』|『([^』]+)』', t)
            if m:
                title = pick_title(next(g for g in m.groups() if g))
                rest = t.replace(m.group(0), '')
                artist = pick_artist(rest)
            else:
                # give up
                return clean_brackets_keep_core(strip_known_meta(t))
    return f"{title} - {artist}"

def create_model() -> None:
    global tokenizer, model
    # tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)

    # padding thing
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # load model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        # quantization_config=bnb_config,
        dtype=torch.float16,
    ).to("cuda")

def generate_word_by_word_exp(prompt, max_tokens):
    model_inputs = tokenizer(prompt, return_tensors='pt').to('cuda')
    generated_ids = model.generate(
        model_inputs['input_ids'].to("cuda"),
        max_new_tokens=max_tokens,
        num_return_sequences=1,
        temperature=0.001,
        top_p=1,
        attention_mask=model_inputs["attention_mask"]
    )
    output = tokenizer.decode(generated_ids[0], skip_special_tokens=True)

    return output

def clear_model() -> None:
    global model
    if "model" in globals() and model is not None:
        del model
        model = None
        torch.cuda.empty_cache()
        gc.collect()

def get_title_from_song(input_text, strict: bool, artist: bool):
    print(Fore.MAGENTA + input_text)

    input_text = extract_title_artist(input_text)

    print(Fore.MAGENTA + input_text)

    prompt =f"""You are a strict text parser.

Task:
- Extract the song title and artist from the input string.

Rules:
1. Never translate, romanize, reword, or guess. Keep text exactly as written in the input.
2. If there is both a title and an artist → output in the exact format: Title - Artist
3. If there is only a title → output only the title
4. Do not output anything else besides the final result (no explanations, no extra characters).
5. Remove only metadata or junk text, including but not limited to:
   - Lyrics / 歌詞
   - Official Video / Audio / MV
   - Color Coded
   - Kan|Rom|Eng
   - Full Version / Version
   - From "..."
   - HD, 4K, Live, Visualizer
6. If the artist text contains both a Latin name and a non-Latin name in parentheses (e.g. ABC (ギヴン)):
   - Always keep the non-Latin text (ギヴン).
7. For the title:
   - Remove subtitle translations in parentheses (e.g. (A Winter Story)), but keep the original core title.

Format:
- Exactly "Title - Artist" or "Title" with no extra characters.

Input:
{input_text}

Output:
"""

    response = generate_word_by_word_exp(prompt, max_tokens=18)

    match = re.search(r'Output:\s*(.+)', response)
    if match:
        result = match.group(1).strip()
    else:
        raise Exception("regex failed")

    if strict:
        result = re.sub(r'[\(\[\{（【〈《「『](.*?)[\)\]\}）】〉》」』]', r'\1', result).strip()

    if not artist:
        result = re.sub(r"\s*-\s*.*", "", result).strip()

    return result

if __name__ == "__main__":
    create_model()
    print(get_title_from_song('GIVEN (ギヴン) - Fuyu no hanashi (冬のはな) (A Winter Story) (Kan|Rom|Eng) Lyrics/歌詞', False, True))