from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList, BitsAndBytesConfig
import torch
import bitsandbytes
import json
import gc
import re
from transformers import GenerationConfig
from tqdm import tqdm
import accelerate
import globalfuncs

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

local_dir = config['jp_en_model_name']
precision_level = config['jp_model_precision_level']

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

gen_config = GenerationConfig.from_pretrained(local_dir)
gen_config.use_cache = True

# main functions
def create_model(precision='fp16') -> None:
    global tokenizer, model
    # tokenizer
    tokenizer = AutoTokenizer.from_pretrained(local_dir)

    globalfuncs.logger.verbose(f"{tokenizer.eos_token} | {tokenizer.eos_token_id}")

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    # set precision level
    if precision == 'fp16':
        model = AutoModelForCausalLM.from_pretrained(
            local_dir,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            attn_implementation="sdpa"
        )
        model = torch.compile(model)
    if precision == 'b8':
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)

        model = AutoModelForCausalLM.from_pretrained(
            local_dir,
            quantization_config=bnb_config,
            llm_int8_enable_fp32_cpu_offload=True,
            device_map="auto",
            attn_implementation="sdpa"
        )
    if precision == 'b4':
        bnb_config = BitsAndBytesConfig(load_in_4bit=True)

        model = AutoModelForCausalLM.from_pretrained(
            local_dir,
            quantization_config=bnb_config,
            device_map="auto",
            attn_implementation="sdpa"
        )

def generate_response(text: str, tokens: int, temp: float, nucleus: float, reppen: float, dosample: bool) -> tuple:
    global tokenizer, model

    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs,
                             max_new_tokens=tokens,
                             temperature=temp,
                             top_p=nucleus,
                             repetition_penalty=reppen,
                             do_sample=dosample,
                             eos_token_id=tokenizer.eos_token_id,
                             pad_token_id=tokenizer.eos_token_id,)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return response

def batch_generate_response(prompts: list, tokens: int, temp: float, nucleus: float, reppen: float, dosample: bool) -> list:
    global tokenizer, model

    inputs = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True).to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=tokens,
        temperature=temp,
        top_p=nucleus,
        repetition_penalty=reppen,
        do_sample=dosample,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id,
    )

    responses = [tokenizer.decode(o, skip_special_tokens=True) for o in outputs]

    return responses

def clear_model() -> None:
    global model
    if "model" in globals() and model is not None:
        del model
        model = None
        torch.cuda.empty_cache()
        gc.collect()

def explain_word_in_line(input_data) -> list:
    global tokenizer, model

    prompt_list = []

    for prompt in input_data:
        prompt_list.append(f"""You are analyzing Japanese lyrics.  
    Given a lyric line, a target word, and its part of speech, output a concise explanation with exactly this structure without adding extra information that isn't part of the structure given below:

    **Meaning:** <short literal meaning without any explanations. only output the meaning of the word in the current tense>  
    **Grammatical Role:** <part of speech in context>  
    **Nuance:** <emotional / implicit connotation, in less than 2 sentences>  
    **Impact on Meaning:** <how it changes the lyric’s emotional tone or imagery, less than 3 sentences>  

    **Summary:** <one-sentence summary around 50 words, weaving the above into a cohesive interpretation>  

    Do not include any other commentary, headers, or revisions.
    Always end with <END_EXPLANATION>  
    Output this structure once only.  
    
    Full lyrics (for context): {prompt[3]}  
    Lyric line: {prompt[0]}  
    Target word: {prompt[1]}  
    Part of speech: {prompt[2]}  
    """)

    output = batch_generate_response(prompt_list, 200, 0.8, 0.9, 1.15, True)

    results = []

    for result in output:
        results.append(list(pull_info_from_llm(result)))

    return results

    # return output


def get_definition_of_phrase(phrase: str) -> str:
    global tokenizer, model

    prompt = f"""
You are a concise Japanese-to-English dictionary assistant.  
Given a Japanese word, output its information in exactly this format:

**Meaning:** <short English definition>  

Word: {phrase}
[END]
    """

    globalfuncs.logger.info(f"Finding definition of {phrase} using LLM")
    output = generate_response(prompt, 20, 0.35, 0.95, 1.15, True)
    # output = str(output).split("[END]")[1]

    output = (re.findall(r'Meaning:(?:[\*\s]*?)([\w\s\S]+?)(?:\n|\[|E|\])', output)[1]).strip()
    output = re.sub(r'\*', '', output)
    globalfuncs.logger.success(f"Found definition of {phrase} using LLM: {output}")

    return output

def batch_translate_lyric_to_en(input_data: list) -> list:
    global tokenizer, model

    prompt_list = []
    lyric_list = []
    for full_lyrics, lyric, full_en_lyrics in input_data:
        lyric_list.append(lyric)

        prompt_list.append(f"""
You are a professional translator of Japanese song lyrics specializing in capturing emotional depth and cultural nuance.
You must strictly follow the output format with NO exceptions.

TRANSLATION PHILOSOPHY:
- Capture the FEELING and emotional resonance, not just literal words
- Consider cultural context and implicit meanings in Japanese
- Use natural, flowing English that sounds like it was written by a native speaker
- Preserve poetic elements, metaphors, and imagery
- Consider how the line would feel when sung, not just read

CRITICAL RULES:
1. Translate ONLY the single line specified in "Lyric:" below
2. Output exactly ONE translation - do not repeat "**Translation:**" multiple times
3. Do not provide alternatives, parenthetical explanations, or multiple interpretations
4. If the line contains [Verse], [Chorus], [Bridge], [Outro], [Intro], or any bracket notation, output exactly: **Translation:**
5. If the line is empty, contains only punctuation, or is metadata/credits, output exactly: **Translation:**
6. Do not add any text after your translation (no explanations, no commentary, nothing)
7. Your response must be exactly one line: "**Translation:** <your translation>"

EXAMPLES OF EMOTIONAL NUANCE:
Lyric: 君がいない夜は長すぎる
**Translation:** The nights without you stretch on forever

Lyric: 心の奥で泣いている
**Translation:** I'm crying deep inside my soul

Lyric: 桜が散る時のように
**Translation:** Like cherry blossoms falling away

Lyric: もう一度だけ
**Translation:** Just one more time

Lyric: [Chorus]
**Translation:**

Use the full lyrics for context:
{full_lyrics}

### STRICT OUTPUT FORMAT ###
**Translation:** <English translation with emotional depth>

Translate the following lyric line into natural, emotionally resonant English that captures both the literal meaning and the deeper feeling:
Lyric: {lyric}

OUTPUT EXACTLY: **Translation:** <translation>
STOP IMMEDIATELY after the translation.
""")

    output = batch_generate_response(prompt_list, 30, 0.4, 0.95, 1.15, True)

    results = []

    for item, lyric in zip(output, lyric_list):
        globalfuncs.logger.spam(f"{item}")
        for line in item.split('\n'):
            if 'Translation' in line:
                globalfuncs.logger.verbose(line)
            if 'Lyric line to translate' in line:
                globalfuncs.logger.verbose(line)
        try:
            if lyric == '':
                results.append('')
            elif re.match(r'^(?:\[|-)(.+?)(?:\]|-)$', lyric):
                results.append('')
            else:
                results.append((re.sub(r'\*|\:', '', (re.findall(r'Translation(?:[\:\*\s]*?)(.+?)(?:\n|$)', item)[5]))).strip())
        except:
            globalfuncs.logger.verbose(item)
            raise Exception

    return results


def translate_lyric_to_en(full_lyrics: str, lyric: str) -> str:
    global tokenizer, model

    prompt = f"""
    You are a professional translator and lyric analyst.  
    Translate the selected Japanese lyric into natural, poetic English using the full lyrics as context.  
    Preserve tone, mood, and implied emotion.

    Lyrics:
    {full_lyrics}
    
    Lyric to be translated:
    {lyric}

    ### OUTPUT FORMAT (strict JSON) ###
    "en": "<English translation>"

    Rules:
    - Translate every line individually.
    - Do not merge, omit, or add lines.
    - No commentary or romanization.
    - Output valid JSON only.
    """

    output = generate_response(prompt, 30, 0.65, 0.95, 1.15, True)

    return re.findall(r'"en":\s?"(.*?)"', output)[1]

def batch_explain_tokens(input_list: list) -> list:
    global tokenizer, model

    prompt_list = []

    for item in input_list:
        prompt_list.append(f"""
You are a Japanese language expert and linguist. I will give you a sentence that has been tokenized, with part-of-speech (POS) and dependency (DEP) annotations for each token. I want you to explain **what each token means in English**, including:

1. The literal meaning of the token.
2. Its part of speech in English.
3. Its dependency function in the sentence.
4. Any grammatical notes (e.g., tense, auxiliary function, particle usage).

Output the result in **JSON format**, using the following structure:

[
  {{
    "token": "<token text>",
    "meaning": "<literal English meaning>",
    "pos": "<POS in English>",
  }},
  ...
]

Here is the tokenized sentence:
{item}
""")

    output = batch_generate_response(prompt_list, 30, 0.4, 0.95, 1.15, True)

    return output


def pull_info_from_llm(text: str):
    # ? text = re.findall(r'\[END\]([\s\S]*?)(?:\[END]|---|Lyric line:)', text)[0]

    print(text)

    text = re.sub(r'\*', '', text)

    meaning = (re.findall(r'Meaning:(?:[\*\s]*?)(.+?)\n', text)[2]).strip()
    grammar = (re.findall(r'Gramm?atica?l? Role:(?:[\*\s]*?)(.+?)\n', text)[1]).strip()
    nuance = (re.findall(r'Nuance:(?:[\*\s]*?)(.+?)\n', text)[1]).strip()
    impact = (re.findall(r'Impact on Meaning:(?:[\*\s]*?)(.+?)\n', text)[1]).strip()
    try:
        summary = (re.findall(r'Summary:(?:[\*\s]*?)(.+?)(?:\n|[<]?END[\\\_]+?EXPLANATION[>]?)', text)[1]).strip()
    except IndexError:
        summary = (re.findall(r'Summary:(?:[\*\s]*?)(.*)', text)[1]).strip()

    return meaning, grammar, nuance, impact, summary