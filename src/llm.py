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

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

model_name = config['large_model_name']

# bnb_config = BitsAndBytesConfig(load_in_4bit=True)
bnb_config = BitsAndBytesConfig(load_in_8bit=True)

# device setup
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

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

def get_title_from_song(input_text):
    prompt = f"""
You are a text parser. Your only job is to extract the song title and artist from the given input.

Rules:
- If both title and artist exist → output exactly in the format: Title - Artist
- If only a title exists → output only the title
- Never invent, translate, or guess missing information
- Do not add explanations, filler words, or extra characters
- Keep the title exactly as given, except remove extra metadata like (From "..."), (Full Version), etc.

Input:
{input_text}

Output:
"""
    return generate_word_by_word_exp(prompt, max_tokens=18)

create_model()
output = get_title_from_song('Kamado Tanjirou no Uta (From "Demon Slayer: Kimetsu no Yaiba") (Full Version)')
print(output)
output = get_title_from_song("GIVEN (ギヴン) - Fuyu no hanashi (冬のはな) (A Winter Story)")
print(output)
output = get_title_from_song("Take Me Home, Country Roads - John Denver | Fingerstyle Guitar")
print(output)