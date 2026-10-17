import os
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from llmcompressor import oneshot
from llmcompressor.modifiers.quantization import QuantizationModifier
from engine.utils.paths import SRC_DIR

# 1. Coordinate paths dynamically on your D: drive
base_dir = SRC_DIR / "models/hugging_face"
hf_cache_dir = Path(base_dir / "models/hugging_face")

# Redirect Hugging Face downloads to your D drive custom folder
os.environ["HF_HOME"] = str(hf_cache_dir)

# 2. Define Model Identifiers & Output Directory
model_id = "shisa-ai/shisa-v2.1-llama3.2-3b"
# model_id = "shisa-ai/shisa-v2.1-qwen3-8b"
output_dir = str(base_dir / "models/hugging_face/shisa-v2.1-llama3.2-3b-fp8")

# 3. Define Quantization Recipe (FP8 float-quantized compression)
recipe = QuantizationModifier(
    targets="Linear",
    scheme="FP8",
    ignore=["lm_head"]
)


def main():
    print(f"Loading tokenizer and model for {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

    # Load model with automated device mapping/offloading to handle memory efficiently
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype="auto",
        trust_remote_code=True
    )

    print("Beginning LLM-Compressor oneshot FP8 quantization process...")
    oneshot(
        model=model,
        dataset="open_platypus",
        recipe=recipe,
        max_seq_length=2048,
        num_calibration_samples=256,
    )

    print(f"Saving quantized FP8 model to: {output_dir}")
    model.save_pretrained(output_dir, save_compressed=True)
    tokenizer.save_pretrained(output_dir)

    print("Quantization complete!")


if __name__ == "__main__":
    main()