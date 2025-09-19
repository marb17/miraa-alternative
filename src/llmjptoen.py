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
llm_translate_use_context = config['llm_translate_use_context']

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
        if llm_translate_use_context:
            prompt_list.append(f"""
You are a professional translator of Japanese song lyrics. 
You must strictly follow the output format. 
Do not provide explanations, extra commentary, or anything outside the required format. 

If the lyric line contains [Verse] or [Bridge] or anything similar, output this only strictly:
**Translation:**

Use the full lyrics for context:
{full_lyrics}

### STRICT OUTPUT FORMAT ###
**Translation:** <English translation of the lyric line>

Translate only the following lyric line into natural, fluent English, including implicit meanings and emotional nuances:
Lyric: {lyric}
""")
        else:
            prompt_list.append(f"""
                        You are a professional Japanese-to-English lyric translator.  
                        Translate exactly one lyric line into natural English.  
                        Do not use any external context — translate only the provided lyric line.  

                        ### RULES ###
                        - Translate **only** the lyric line.  
                        - Do not provide multiple translations.  
                        - Do not comment or add extra text outside the strict format.  
                        - Do NOT add any other explanations outside the strict format.  
                        - Strictly output in this format:  
                        **Translation:** <English translation of the lyric line>  
                        <END_EXPLANATION>  
                        ### END OF RULES ###

                        Lyric line to translate: {lyric}  
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
            if llm_translate_use_context:
                if lyric == '':
                    results.append('')
                else:
                    results.append((re.sub(r'\*|\:', '', (re.findall(r'Translation(?:[\:\*\s]*?)(.+?)(?:\n|$)', item)[2]))).strip())
            else:
                results.append((re.sub(r'\*|\:', '', (re.findall(r'Translation(?:[\:\*\s]*?)(.+?)(?:\n|$)', item)[1]))).strip())
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