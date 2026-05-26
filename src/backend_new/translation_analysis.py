from transformers.utils import quantization_config
from accelerate import Accelerator

class Translator:
    def __init__(self) -> None:
        # TODO ask use to choose what model
        self._llm = None
        # model save loc
        import os
        from pathlib import Path
        self._script_dir = Path(__file__).resolve().parent
        self._base_dir = self._script_dir.parents[0]
        self._model_dir = Path(self._base_dir / "models/hugging_face")
        os.environ["HF_HOME"] = str(self._model_dir)

        from transformers import AutoTokenizer
        self._model_id = str(self._model_dir / "shisa-v2.1-qwen3-8b-awq")

    # region batched inference
    # TODO trying out batched, maybe add a feature where it monitors GPU usage and changes batch size
    def init_model(self) -> None:
        from vllm import LLM

        self._llm = LLM(model = self._model_id,
                   quantization="awq",
                   dtype="float16",
                   enforce_eager=True,
                   gpu_memory_utilization=0.85,
                   max_model_len=2048)

if __name__ == "__main__":
    llm_model = Translator()
    llm_model.init_model()