from transformers.utils import quantization_config


class Translator:
    def __init__(self) -> None:
        # TODO ask use to choose what model
        self._model_id = "shisa-ai/shisa-v2.1-qwen3-8b"

    def _init_model(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        # TODO allow user to change quantization config
        self._quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16
        )

        self._tokenizer = AutoTokenizer.from_pretrained(self._model_id)
        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_id,
            quantization_config=quantization_config,
            device_map="auto"
        )