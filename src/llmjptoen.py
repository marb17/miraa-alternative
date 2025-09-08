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


def clear_model() -> None:
    global model
    if "model" in globals() and model is not None:
        del model
        model = None
        torch.cuda.empty_cache()
        gc.collect()

def explain_word_in_line(lyric: str, word: str, pos: str, full_song: str) -> tuple[str, str, str, str, str]:
    global tokenizer, model

    prompt = f"""You are analyzing Japanese lyrics.  
Given a lyric line, a target word, and its part of speech, output a concise explanation with exactly this structure:

**Meaning:** <short literal meaning without any explanations. only output the meaning of the word in the current tense>  
**Grammatical Role:** <part of speech in context>  
**Nuance:** <emotional / implicit connotation, in less than 2 sentences>  
**Impact on Meaning:** <how it changes the lyric’s emotional tone or imagery, ≤2 sentences>  

**Summary:** <one-sentence summary around 50 words, weaving the above into a cohesive interpretation>  

Do not include any other commentary or headers. Keep it concise and poetic, but analytical.

Full lyrics (for context): {full_song}
Lyric line: {lyric}  
Target word: {word}  
Part of speech: {pos}

[END]
"""

    output = generate_response(prompt, 200, 0.9, 0.9, 1.15, True)

    return pull_info_from_llm(output)

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

def pull_info_from_llm(text: str):
    text = re.findall(r'\[END\]([\s\S]*?)(?:\[END]|---|Lyric line:)', text)[0]

    meaning = (re.findall(r'Meaning:\w?(.+?)\n', text)[0]).strip()
    grammar = (re.findall(r'Grammatical Role:\w?(.+?)\n', text)[0]).strip()
    nuance = (re.findall(r'Nuance:\w?(.+?)\n', text)[0]).strip()
    impact = (re.findall(r'Impact on Meaning:\w?(.+?)\n', text)[0]).strip()
    summary = (re.findall(r'Summary:\w?(.+?)\n', text)[0]).strip()

    return meaning, grammar, nuance, impact, summary