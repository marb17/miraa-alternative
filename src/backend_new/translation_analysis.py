from transformers.utils import quantization_config
from accelerate import Accelerator

class Translator:
    def __init__(self) -> None:
        # TODO ask use to choose what model
        from transformers import AutoTokenizer

        self._model_id = "shisa-ai/shisa-v2.1-qwen3-8b"
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_id)

    # TODO donno if works
    def _init_model(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig

        # TODO allow user to change quantization config
        self._quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16
        )

        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_id,
            quantization_config=quantization_config,
            device_map="auto"
        )

    # region batched inference
    # TODO trying out batched, maybe add a feature where it monitors GPU usage and changes batch size
    def _batched_init_model(self) -> None:
        from vllm import LLM

        _llm = LLM(model = self._model_id)
        _llm.apply_model(lambda model: print((type(self._model_id))))


llm_model = Translator()
llm_model._batched_init_model()