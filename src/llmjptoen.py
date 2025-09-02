from llama_stack.core.ui.page.playground.chat import repetition_penalty
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import json
import gc
import re

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

local_dir = config['jp_en_model_name']

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def create_model() -> None:
    global tokenizer, model
    # tokenizer
    tokenizer = AutoTokenizer.from_pretrained(local_dir)

    model = AutoModelForCausalLM.from_pretrained(
        local_dir,
        dtype=torch.float16,
        device_map="auto",
        attn_implementation="sdpa"
    )

    model = torch.compile(model)

def generate_response(text: str, tokens: int, temp: float, nucleus: float, reppen: float, dosample: bool) -> str:
    global tokenizer, model

    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=tokens, temperature=temp, top_p=nucleus, repetition_penalty=reppen, do_sample=dosample)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return response


def clear_model() -> None:
    global model
    if "model" in globals() and model is not None:
        del model
        model = None
        torch.cuda.empty_cache()
        gc.collect()

create_model()
yup = generate_response("can you please translate 'hello' into japanese?", 100, 1.1, 0.95, 1, True)
print(yup)
clear_model()
