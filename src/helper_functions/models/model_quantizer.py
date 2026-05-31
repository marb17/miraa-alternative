import os
from pathlib import Path
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

# 1. Coordinate paths dynamically on your D: drive
script_dir = Path(__file__).resolve().parent
base_dir = script_dir.parents[0] if "src" in script_dir.parts else script_dir
hf_cache_dir = Path(base_dir / "models/hugging_face")

# Redirect Hugging Face downloads to your D drive custom folder
os.environ["HF_HOME"] = str(hf_cache_dir)

# 2. Define Model Identifiers
model_id = "shisa-ai/shisa-v2.1-qwen3-8b"
output_dir = str(base_dir / "models/hugging_face/shisa-v2.1-qwen3-8b-awq")

# 3. Define Quantization Settings (INT4 configuration)
quant_config = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4,
    "version": "GEMM",
}

def main():
    print(f"Loading tokenizer for {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

    print(f"Loading unquantized model weights (utilizing CPU offload)...")
    # safetensors=True saves disk space and loads faster
    model = AutoAWQForCausalLM.from_pretrained(
        model_id, low_cpu_mem_usage=True
    )

    print("Beginning AWQ quantization process...")
    # This checks how weights react to activations using a standard text corpus
    model.quantize(tokenizer, quant_config=quant_config)

    print(f"Saving quantized INT4 model to: {output_dir}")
    model.save_quantized(output_dir)
    tokenizer.save_pretrained(output_dir)

    print("Quantization complete!")


if __name__ == "__main__":
    main()