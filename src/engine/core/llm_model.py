import gc
import os
import time
from itertools import batched
from math import ceil
from pathlib import Path
from typing import Any, Generator
import platform

from engine.utils.classes.abc import BaseLLMModel
from engine.utils.functions.filesystem import read_json_file
from engine.utils.logger import Logger

logger = Logger(__name__)

if platform.system() == "Windows":
    from lmdeploy import GenerationConfig
    class WindowsLLMModel(BaseLLMModel):
        def __init__(self) -> None:
            self._pipe = None

            # model save loc
            current_dir = Path(__file__).resolve().parent
            while current_dir.name != "src" and current_dir != current_dir.parent:
                current_dir = current_dir.parent
            self._base_dir = current_dir

            self._model_dir = Path(self._base_dir / "models/hugging_face")
            # TODO ask use to choose what model
            # TODO automatically download model and quantize when not downloaded yet
            self._model_id = str(self._model_dir / "shisa-v2.1-llama3.2-3b-int4")
            # self._model_id = str(self._model_dir / "shisa-v2.1-llama3.2-3b-fp8")
            # self._model_id = str(self._model_dir / "shisa-v2.1-llama3.2-3b")
            # self._model_id = str(self._model_dir / "shisa-v2.1-qwen3-8b-int4")
            os.environ["HF_HOME"] = str(self._model_dir)

            self._free_vram: float = 0
            self._initialized = True

            # model parameters
            """
            Embeddings = Vocab_Size * Hidden_Size * 2
            Attention  = Num_Hidden_Layers * (4 * (Hidden_Size ^ 2))
            MLP_SwiGLU = Num_Hidden_Layers * (3 * (Hidden_Size * Intermediate_Size))
            
            Total_Parameters = Embeddings + Attention + MLP_SwiGLU
            
            Model_Weights_Bytes = Total_Parameters * (Quantization_Bits / 8) * 1.2
            Model_Weights_GB    = Model_Weights_Bytes / (1024 ^ 3)
            """
            model_data = read_json_file(
                Path(self._model_id) / "config.json"
            )

            vocab_size = model_data["vocab_size"]
            hidden_size = model_data["hidden_size"]
            num_hidden_layers = model_data["num_hidden_layers"]
            intermediate_size = model_data["intermediate_size"]
            num_kv_heads = model_data.get(
                "num_key_value_heads", model_data.get("num_attention_heads", 32)
            )
            head_dim = model_data.get(
                "head_dim", hidden_size // model_data.get("num_attention_heads", 32)
            )
            bits = model_data.get("quantization_config", {}).get("bits", 4)

            embeddings = vocab_size * hidden_size * 2
            attention = num_hidden_layers * (4 * (hidden_size ** 2))
            mlp_swiglu = num_hidden_layers * (
                    3 * (hidden_size * intermediate_size)
            )
            parameter_count = embeddings + attention + mlp_swiglu

            self._model_weight = (
                    1.2 * (parameter_count * bits / 8) / (1024 ** 3)
            )
            """
            KV_Cache_Bytes = 2 * Num_Hidden_Layers * Num_KV_Heads * Head_Dim * Batch_Size * Output_Tokens * Precision_Bytes
    
            Where Precision_Bytes is:
            - 2 (for FP16 / BF16)
            - 1 (for INT8 cache)
            - 0.5 (for INT4 cache)
            
            KV_Cache_GB = KV_Cache_Bytes / (1024 ^ 3)
            """
            self._kv_cache_base = (
                    2 * num_hidden_layers * num_kv_heads * head_dim * 2
            )
            """
            Where Precision_Bytes is:
            - 2 (for FP16 / BF16)
            - 1 (for INT8 cache)
            - 0.5 (for INT4 cache)
            
            Bytes Per Token per Batch = Hidden * Layers * Precision Bytes = Bytes
            """
            self._gb_per_token = (
                                         hidden_size * num_hidden_layers * 2
                                 ) / (1024 ** 3)

        def __enter__(self):
            if self._pipe is None:
                self.init_model()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._close()
            return False

        @staticmethod
        def _clean_memory():
            import gc
            import torch

            gc.collect()
            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                torch.cuda.reset_peak_memory_stats()

        def _close(self) -> None:
            if self._pipe is not None:
                logger.debug("Closing LMDeploy pipeline...")

                self._pipe.close()

                if hasattr(self._pipe, 'engine') and self._pipe.engine is not None:
                    try:
                        self._pipe.engine.close()
                        del self._pipe.engine
                    except Exception as e:
                        logger.warning(f"Error while closing internal engine: {e}")

                del self._pipe
                self._pipe = None

            self._clean_memory()

        # region batched inference
        def _calculate_prompt_cost(self, prompt: list[str], estimated_output_token_cost: int) -> float:
            """
            LMDEPLOY uses Chunked Pre-Fill so each prompt is processed in smaller batches 512 tokens?
            yeah i still havent read the documentation so idk if this is right

            Context_Activation_GB = Batch_Size * Input_Tokens * (GB per Token)
            """
            CHUNK_SIZE = 512

            max_prompt_chars = max([len(text) for text in prompt]) if prompt else 0
            max_prompt_tokens = max_prompt_chars * 0.75

            batch_size = len(prompt)

            active_prefill_tokens = min(max_prompt_tokens, CHUNK_SIZE)

            context_cost = active_prefill_tokens * self._gb_per_token * batch_size

            generation_cost = (self._kv_cache_base * estimated_output_token_cost) / (1024 ** 3)
            total_generation_cost = generation_cost * batch_size

            return context_cost + total_generation_cost

        def init_model(self) -> None:
            """
            Starts the model up, ready to be used
            """
            # get available VRAM
            import torch
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is not available on this system.")

            device = torch.cuda.current_device()

            free_bytes, total_bytes = torch.cuda.mem_get_info(device)
            self._free_vram = free_bytes / (1024 ** 3)
            logger.debug(f"Available VRAM: {self._free_vram}")

            cache_ratio = 0.5 if self._free_vram > (self._model_weight * 1.4) else 0.1
            logger.debug(f"Cache Ratio: {cache_ratio}")

            if self._pipe is None:
                from lmdeploy import pipeline, TurbomindEngineConfig

                logger.debug(f"Initializing model: {self._model_id}")

                now = time.time()

                backend_config = TurbomindEngineConfig(
                    #todo seems to affect stability, need to test more cuz i keep getting 0xC0000409 exit codes
                    cache_max_entry_count=cache_ratio,
                    tp=1,
                    session_len=8192
                )

                self._pipe = pipeline(self._model_id,
                                      backend_config=backend_config,
                                      log_level="WARNING",)
                logger.debug(f"Loaded model in {(time.time() - now):.2f} seconds")
            else:
                logger.debug("Model already initialized, skipping")

        def batch_inference(self, prompts: list[str],
                            batch_size: int = -1,
                            estimated_output_cost: int = 2048,
                            gen_config: GenerationConfig | None = None) -> list[Any]:
            """
            Performs inference on a batch of prompts.
            :param gen_config: A generation config object to change how the LLM generates
            :type gen_config: GenerationConfig | None
            :param prompts: List of prompts to infer
            :type prompts: list[str]
            :param batch_size: How much prompts to send each batch
                Possible Values:
                * '0' - Not batched
                * '-1' - Auto sized
            :type batch_size: int
            :param estimated_output_cost: Estimated how many tokens are used for each output
            :type estimated_output_cost: int
            :return: A list of all the responses
            :rtype: list[str]
            """
            import torch
            from lmdeploy import GenerationConfig

            if gen_config is None:
                gen_config = GenerationConfig()
            else:
                gen_config = gen_config

            if self._pipe is None:
                self.init_model()

            logger.debug(f"How many prompts to process: {len(prompts)}")
            # region batch sizing
            if batch_size > 1:
                logger.debug(f"Manual Batch size of {batch_size}")
                pass
            if batch_size == 0:
                logger.debug("No batching")
                batch_size = len(prompts)
            if batch_size == -1:
                # automatic sizing
                available_vram = self._free_vram - self._model_weight
                total_prompt_cost = self._calculate_prompt_cost(prompts, estimated_output_cost)

                num_batches = ceil(total_prompt_cost / available_vram * 1.3)
                num_prompts = len(prompts)

                batch_size = ceil(num_prompts / num_batches)

                logger.debug("Automatic Batch Sizing")
                logger.debug(f"Estimated Prompt Cost: {total_prompt_cost}")
                logger.debug(f"Model Weight: {self._model_weight}")
                logger.debug(f"Number of batches: {num_batches}")
                logger.debug(f"Batch size: ~{batch_size}")

            batched_prompts = list(batched(prompts, batch_size))
            # endregion

            results = []
            now = time.time()
            for idx, batch in enumerate(batched_prompts, start=1):
                batch_now = time.time()
                results.extend([response.text for response in self._pipe(list(batch), gen_config)])
                self._clean_memory()
                logger.debug(f"Completed Batch {idx} in {(time.time() - batch_now):.2f} seconds")

            logger.debug(f"Completed Batch Inference in {(time.time() - now):.2f} seconds")

            return results


elif platform.system() == "Darwin":
    pass
    # raise NotImplementedError

class LLMModel:
    def __init__(self):
        self.platform = platform.system()

    def __enter__(self):
        if self.platform == "Windows":
            return WindowsLLMModel()
        elif self.platform == "Darwin":
            pass
            raise NotImplementedError
        raise NotImplementedError

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.platform == "Windows":
            import torch
            gc.collect()
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        elif self.platform == "Darwin":
            raise NotImplementedError
        return False
