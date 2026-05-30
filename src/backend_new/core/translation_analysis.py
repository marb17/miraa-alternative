class LLMModel:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False

        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        from backend_new.utils import logger
        self._logger = logger.Logger()

        self._pipe = None

        # model save loc
        import os
        from pathlib import Path
        from backend_new.utils.helper_funcs import read_json_file

        current_dir = Path(__file__).resolve().parent
        while current_dir.name != "src" and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        self._base_dir = current_dir

        self._model_dir = Path(self._base_dir / "models/hugging_face")
        # TODO ask use to choose what model
        # TODO automatically download model and quantize when not downloaded yet
        self._model_id = str(self._model_dir / "shisa-v2.1-qwen3-8b-awq")
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
        model_data = read_json_file(self._model_dir / "shisa-v2.1-qwen3-8b-awq/config.json")
        parameter_count = ((model_data["vocab_size"] * model_data["hidden_size"] * 2) +
                           (4 * model_data["num_hidden_layers"] * (model_data["hidden_size"] ** 2)) +
                           (3 * model_data["hidden_size"] * model_data["intermediate_size"] * model_data["num_hidden_layers"]))
        self._model_weight = 1.2 * (parameter_count * model_data["quantization_config"]["bits"] / 8) / (1024 ** 3)
        """
        KV_Cache_Bytes = 2 * Num_Hidden_Layers * Num_KV_Heads * Head_Dim * Batch_Size * Output_Tokens * Precision_Bytes

        Where Precision_Bytes is:
        - 2 (for FP16 / BF16)
        - 1 (for INT8 cache)
        - 0.5 (for INT4 cache)
        
        KV_Cache_GB = KV_Cache_Bytes / (1024 ^ 3)
        """
        self._kv_cache_base = (2 * model_data["num_hidden_layers"] * model_data["num_key_value_heads"] * model_data["head_dim"] * 2)

        """
        Where Precision_Bytes is:
        - 2 (for FP16 / BF16)
        - 1 (for INT8 cache)
        - 0.5 (for INT4 cache)
        
        Bytes Per Token per Batch = Hidden * Layers * Precision Bytes = Bytes
        """
        self._gb_per_token = (model_data["hidden_size"] * model_data["num_hidden_layers"] * 2) / (1024 ** 3)

    def __del__(self) -> None:
        self._close()

    def __enter__(self):
        if self._pipe is None:
            self.init_model()
        return self

    def __exit__(self):
        self._close()
        return False

    def _close(self) -> None:
        self._pipe = None
        LLMModel._instance = None

        import gc
        import torch
        gc.collect()
        torch.cuda.empty_cache()

    # region batched inference
    def _calculate_prompt_cost(self, prompt: list[str], estimated_output_token_cost: int) -> float:
        """
        LMDEPLOY uses Chunked Pre-Fill so each prompt is processed in smaller batches 512 tokens?

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

    # TODO trying out batched, maybe add a feature where it monitors GPU usage and changes batch size
    def init_model(self) -> None:
        """
        Starts the model up, ready to be used
        """
        if self._pipe is None:
            from lmdeploy import pipeline
            import time

            self._logger.debug(f"Initializing model: {self._model_id}")

            now = time.time()

            self._pipe = pipeline(self._model_id)
            self._logger.debug(f"Loaded model in {(time.time() - now):.2f} seconds")

            # get available VRAM
            import torch
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is not available on this system.")

            device = torch.cuda.current_device()

            total_mem = torch.cuda.get_device_properties(device).total_memory

            allocated_mem = torch.cuda.memory_allocated(device)
            reserved_mem = torch.cuda.memory_reserved(device)

            free_mem_bytes = total_mem - (allocated_mem + reserved_mem)
            self._free_vram = free_mem_bytes / (1024 ** 3)
            self._logger.debug(f"Available VRAM: {self._free_vram}")
        else:
            self._logger.debug("Model already initialized, skipping")

    def batch_inference(self, prompts: list[str], batch_size: int = -1, estimated_output_cost: int = 2048) -> list[str]:
        """
        Performs inference on a batch of prompts.
        :param prompts: List of prompts to infer
        :param batch_size: How much prompts to send each batch
            Possible Values:
            * '0' - Not batched
            * '-1' - Auto sized
        :param estimated_output_cost: Estimated how many tokens are used for each output
        :return: A list of all the responses
        """
        from itertools import batched
        from math import ceil
        import torch
        import gc
        import time

        if self._pipe is None:
            self.init_model()

        self._logger.debug(f"How many prompts to process: {len(prompts)}")
        # region batch sizing
        if batch_size > 1:
            self._logger.info(f"Manual Batch size of {batch_size}")
            pass
        if batch_size == 0:
            self._logger.info("No batching")
            batch_size = len(prompts)
        if batch_size == -1:
            # automatic sizing
            available_vram = self._free_vram - self._model_weight
            total_prompt_cost = self._calculate_prompt_cost(prompts, estimated_output_cost)

            num_batches = ceil(total_prompt_cost / available_vram * 1.3)
            num_prompts = len(prompts)

            batch_size = ceil(num_prompts / num_batches)

            self._logger.info("Automatic Batch Sizing")
            self._logger.debug(f"Estimated Prompt Cost: {total_prompt_cost}")
            self._logger.debug(f"Model Weight: {self._model_weight}")
            self._logger.debug(f"Number of batches: {num_batches}")
            self._logger.debug(f"Batch size: ~{batch_size}")

        batched_prompts = list(batched(prompts, batch_size))
        # endregion

        results = []
        now = time.time()
        for idx, batch in enumerate(batched_prompts, start=1):
            batch_now = time.time()
            results.extend([response.text for response in self._pipe(list(batch))])
            gc.collect()
            torch.cuda.empty_cache()
            self._logger.debug(f"Completed Batch {idx} in {(time.time() - batch_now):.2f} seconds")

        self._logger.info(f"Completed Batch Inference in {(time.time() - now):.2f} seconds")
        return results


class Translator:
    def __init__(self) -> None:
        from backend_new.utils import logger
        self._logger = logger.Logger()

    def translate_lyrics(self, texts: list[str] | str, use_context: bool = False) -> list[str]:
        """
        Translates lyrics
        :param texts: Pure string or list of strings (pure string splits by newlines)
        :param use_context: Whether to use context for the prompts
        :return: Translated lyrics in list form
        """
        import time
        now = time.time()
        # region japanese character check
        import re
        # This checks for:
        # - Hiragana: \u3040-\u309f
        # - Katakana: \u30a0-\u30ff
        # - Kanji (CJK Unified Ideographs): \u4e00-\u9faf
        JAPANESE_CHAR_PATTERN = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]")

        def contains_japanese(string: str) -> bool:
            if type(string) is not str:
                return False

            return bool(JAPANESE_CHAR_PATTERN.search(string))
        # endregion

        # allows pure string and list of string & context creation
        if type(texts) is str:
            data = texts.split("\n")
            context = texts
        elif type(texts) is list:
            data = texts
            context = "\n".join(texts)

        # setup prompts to be sent
        prompts = []
        mapping_index = []
        processed_lyrics = {}
        for idx, text in enumerate(data):
            # skips certain conditions
            if text == '':
                continue
            if text.startswith("[") and text.endswith("]"):
                continue
            if not contains_japanese(text):
                continue
            if text in processed_lyrics:
                mapping_index.append((idx, "dup"))
                continue

            # region prompts
            if use_context:
                prompts.append(f"""
            You are a **professional Japanese translator** who captures emotional depth, poetic nuance, and cultural context. 
            Your goal is to translate naturally and beautifully — as if the text were written in English — while respecting the original emotion and imagery.

            ### TRANSLATION PRINCIPLES ###
            - Prioritize FEELING and resonance over literal wording.
            - Preserve metaphors, imagery, and poetic tone.

            ### RULES ###
            1. Translate **only** the given line in "Lyric:" below.
            2. Output exactly one line: `**Translation:** <your translation>`
            3. Do not add explanations, alternatives, or commentary. Ever.
            4. Stop immediately after the translation line.

            ### EXAMPLES ###
            Text: 君がいない夜は長すぎる  
            **Translation:** The nights without you stretch on forever  

            Text: 心の奥で泣いている  
            **Translation:** I'm crying deep inside my soul  

            ### USE THIS AS CONTEXT TO HOW THE LYRIC INTERACTS WITH THE SONG ###
            Context: {context}

            Now translate the following line with emotional depth and natural phrasing:
            Lyric: {text}

            **Output exactly:**
            **Translation:** <your translation>
            """)
            else:
                prompts.append(f"""
            You are a **professional Japanese translator** who captures emotional depth, poetic nuance, and cultural context. 
            Your goal is to translate naturally and beautifully — as if the text were written in English — while respecting the original emotion and imagery.
            
            ### TRANSLATION PRINCIPLES ###
            - Prioritize FEELING and resonance over literal wording.
            - Preserve metaphors, imagery, and poetic tone.
        
            ### RULES ###
            1. Translate **only** the given line in "Lyric:" below.
            2. Output exactly one line: `**Translation:** <your translation>`
            3. Do not add explanations, alternatives, or commentary. Ever.
            4. Stop immediately after the translation line.
            
            ### EXAMPLES ###
            Text: 君がいない夜は長すぎる  
            **Translation:** The nights without you stretch on forever  
    
            Text: 心の奥で泣いている  
            **Translation:** I'm crying deep inside my soul  

            Now translate the following line with emotional depth and natural phrasing:
            Lyric: {text}
    
            **Output exactly:**
            **Translation:** <your translation>
            """)
            # endregion
            mapping_index.append((idx, "do"))
            processed_lyrics[text] = idx

        with LLMModel() as llm:
            responses = dict(zip([idx for idx, exp in mapping_index if exp == "do"], llm.batch_inference(prompts, estimated_output_cost=50)))

        results = []
        # remap all unprocessed, remove special whitespace and strips
        def clean_unicode(input_string: str) -> str:
            input_string = re.sub(r"[\u2005\u200a\u205f\u2014]", " ", input_string)
            input_string = re.sub(r"\u2019", "'", input_string)
            input_string = input_string.strip()

            return input_string

        def clean_translation_header_and_unicode(input_string: str) -> str:
            """Also cleans Unicode"""
            input_string = input_string.strip()
            input_string = re.sub(
                r"^\*?\*?Translation:\*?\*?\s*", "", input_string, flags=re.IGNORECASE
            )
            input_string = clean_unicode(input_string)

            return input_string

        for idx, d in enumerate(data):
            if (idx, "do") in mapping_index:
                response = responses[idx]

                # remove translation header
                formatted_response = clean_translation_header_and_unicode(response)
                results.append(formatted_response)
            elif (idx, "dup") in mapping_index:
                prev_processed_idx = processed_lyrics[d]
                response = responses[prev_processed_idx]

                # remove translation header
                formatted_response = clean_translation_header_and_unicode(response)
                results.append(formatted_response)
            else:
                formatted_response = clean_unicode(d)
                results.append(formatted_response)

        self._logger.debug(f"Finished translating in {(time.time() - now):.2f} seconds")

        return results

if __name__ == "__main__":
    translator = Translator()
#
#     print(translator.translate_text(["姿形の見えない魔物",
# "どこへでも連れて行くよ",
# "街を見下ろして"]))

    # lyric = "[\u30dd\u30eb\u30ab\u30c9\u30c3\u30c8\u30b9\u30c6\u30a3\u30f3\u30b0\u30ec\u30a4\u306e\u300cJET\u300d\u6b4c\u8a5e]\n\n[Intro]\nTaking off, taking off\n\u59ff\u5f62\u306e\u898b\u3048\u306a\u3044\u9b54\u7269\n\u3069\u3053\u3078\u3067\u3082\u9023\u308c\u3066\u884c\u304f\u3088\n\u8857\u3092\u898b\u4e0b\u308d\u3057\u3066\nWell, you are my star\n\n[Verse 1]\n\u8033\u3092\u585e\u3044\u3067\u3082\u805e\u3053\u3048\u308b\u306e\n\u885d\u52d5\u306e\u5f3e\u3051\u308b\u97f3\u304c\nUh, just a moment, du-ru-du, du-ru-du, du-ru-du\nI am\u2005just\u2005waiting for my,\u2005du-ru-du, du-ru-du, du-ru-du\n\u4e00\u77ac\u306e\u9759\u5bc2\u306e\u5302\u3044\n\u3042\u306a\u305f\u3092\u601d\u3044\u51fa\u3059\n\u5225\u308c\u969b\u306e\u3042\u306a\u305f\u3092\u601d\u3046\n\u91d1\u66dc\u306e\u5348\u5f8c\u306e\u7a7a\u60f3\u3055\nGive me a second,\u2005du-ru-du, du-ru-du, du-ru-du\n\u604b\u3059\u308b\u767d\u663c\u5922, du-ru-du, du-ru-du\n\u4eca\u306f\u4f55\u3092\u3057\u3066\u3044\u308b\u306e\uff1f\n\u3042\u306a\u305f\u304c\u5c45\u308c\u3070\u3069\u3053\u3067\u3082\u884c\u3051\u3066\u3057\u307e\u3046\n\n[Chorus]\n\u6025\u3044\u3067\uff01\nTaking off, taking off\n\u59ff\u5f62\u306e\u898b\u3048\u306a\u3044\u9b54\u7269\n\u8033\u3092\u585e\u3044\u3067\u3082\u805e\u3053\u3048\u308b\u885d\u52d5\u306e\u97f3\nYou're just moving\u205fon,\u205fmoving\u205fon\n\u4eca\u306f\u3069\u3053\u304b\u9060\u304f\u3078\u9003\u3052\u3088\u3046\n\u3069\u3053\u3078\u3067\u3082\u9023\u308c\u3066\u884c\u304f\u3088\n\u8857\u3092\u898b\u4e0b\u308d\u3057\u3066\nYou are my\u205fjet star\n\n[Verse 2]\n\u4e00\u4eba\u304d\u308a\u306e\u90e8\u5c4b\u3067\u9a12\u3050\n\u3072\u3068\u308a\u3067\u306b\u71c3\u3048\u308b\u9f13\u52d5\u3055\nNobody like\u205fyou, du-ru-du, du-ru-du, du-ru-du\n\u604b\u3059\u308b\u30c0\u30f3\u30b9\u30d5\u30ed\u30a2, du-ru-du, du-ru-du, du-ru-du\n\u5c0f\u3055\u3059\u304e\u308b\u90e8\u5c4b\n\u3042\u3042\u3001\u79c1\u306e\u77e5\u3089\u306a\u3044\u305d\u3093\u306a\u9854\u3057\u306a\u3044\u3067\n\n[Chorus]\nLoving you, loving you\n\u5618\u3082\u8aa0\u3082\u8981\u3089\u306a\u3044\u3001up to you\n\u4e00\u4eba\u306e\u90e8\u5c4b\u3001\u7d9a\u304f\u590f\u306e\u5302\u3044\nI'm just moving on, moving on\n\u3042\u306a\u305f\u306b\u51fa\u4f1a\u3046\u307e\u3067\u306f\u79c1\n\u306d\u3048\u3001\u3069\u3093\u306a\u9854\u3092\u3057\u3066\u751f\u304d\u3066\u304d\u305f\u3093\u3060\u3063\u3051\uff1f\nAll I need is you\n\n[Pre-Chorus]\nLadies and gentlemen\nFor your comfort, we will be dimming the main cabin lights\nIf you wish to continue reading, you will find your reading light\nIn the panel above you, thank you\n\n[Chorus]\nTaking off, taking off\n\u59ff\u5f62\u306e\u898b\u3048\u306a\u3044\u9b54\u7269\n\u8033\u3092\u585e\u3044\u3067\u3082\u805e\u3053\u3048\u308b\u885d\u52d5\u306e\u97f3\nYou're just moving on, moving on\n\u53e3\u306f\u707d\u3044\u306e\u3082\u3068\u306a\u3089\u3070\n\u4f55\u3082\u8a00\u308f\u306a\u304f\u3066\u3044\u3044\u3088\n\u3069\u3053\u306b\u884c\u3053\u3046\uff1f\nTaking off, taking off\n\u4eca\u306f\u660e\u65e5\u307e\u3067\u5f85\u3066\u306a\u3044 Taking a trip\n\u3053\u306e\u590f\u304c\u7d42\u308f\u308b\u524d\u306b\n\u79c1\u305f\u3061\u304d\u3063\u3068\u4f1a\u3044\u307e\u3057\u3087\u3046\n\n[Outro]\nAh-ah\nDu-ru-du, du-ru-du, du-ru-du\nNobody like you, ooh-ooh, ooh-ooh\nMoving on, moving on\nNobody like you are my star"
    # lyric = "[\u30b0\u30fc\u30b9 \u30cf\u30a6\u30b9\u300c\u5149\u308b\u306a\u3089\u300d\u6b4c\u8a5e]\n\n[Verse 1]\n\u96e8\u4e0a\u304c\u308a\u306e\u8679\u3082 \u51db\u3068\u54b2\u3044\u305f\u82b1\u3082\n\u8272\u3065\u304d\u6ea2\u308c\u51fa\u3059\n\u831c\u8272\u306e\u7a7a \u4ef0\u3050\u541b\u306b\n\u3042\u306e\u65e5 \u604b\u306b\u843d\u3061\u305f\n\n[Pre-Chorus]\n\u77ac\u9593\u306e\u30c9\u30e9\u30de\u30c1\u30c3\u30af\n\u30d5\u30a3\u30eb\u30e0\u306e\u4e2d\u306e\u4e00\u30b3\u30de\u3082\n\u6d88\u3048\u306a\u3044\u3088 \u5fc3\u306b\u523b\u3080\u304b\u3089\n\n[Chorus]\n\u541b\u3060\u3088 \u541b\u306a\u3093\u3060\u3088 \u6559\u3048\u3066\u304f\u308c\u305f\n\u6697\u95c7\u3082\u5149\u308b\u306a\u3089 \u661f\u7a7a\u306b\u306a\u308b\n\u60b2\u3057\u307f\u3092\u7b11\u9854\u306b \u3082\u3046\u96a0\u3055\u306a\u3044\u3067\n\u714c\u3081\u304f\u3069\u3093\u306a\u661f\u3082 \u541b\u3092\u7167\u3089\u3059\u304b\u3089\n\n[Verse 2]\n\u7720\u308a\u3082\u5fd8\u308c\u3066\u8fce\u3048\u305f\u671d\u65e5\u304c\n\u3084\u305f\u3089\u3068\u7a81\u304d\u523a\u3055\u308b\n\u4f4e\u6c17\u5727\u904b\u3076 \u982d\u75db\u3060\u3063\u3066\n\u5fd8\u308c\u308b \u541b\u306b\u4f1a\u3048\u3070\n\n[Pre-Chorus]\n\u9759\u5bc2\u306f\u30ed\u30de\u30f3\u30c6\u30a3\u30c3\u30af\n\u7d05\u8336\u306b\u6eb6\u3051\u305f\u30b7\u30e5\u30ac\u30fc\u306e\u3088\u3046\u306b\n\u5168\u8eab\u306b\u5de1\u308b\u3088 \u541b\u306e\u58f0\n\n[Chorus]\n\u541b\u3060\u3088 \u541b\u306a\u3093\u3060\u3088 \u7b11\u9854\u3092\u304f\u308c\u305f\n\u6d99\u3082\u5149\u308b\u306a\u3089 \u6d41\u661f\u306b\u306a\u308b\n\u50b7\u4ed8\u3044\u305f\u305d\u306e\u624b\u3092 \u3082\u3046\u96e2\u3055\u306a\u3044\u3067\n\u9858\u3044\u3092\u8fbc\u3081\u305f\u7a7a\u306b \u660e\u65e5\u304c\u6765\u308b\u304b\u3089\n\n[Bridge]\n\u5c0e\u3044\u3066\u304f\u308c\u305f \u5149\u306f\u541b\u3060\u3088\n\u3064\u3089\u308c\u3066\u50d5\u3082 \u8d70\u308a\u51fa\u3057\u305f\n\u77e5\u3089\u306c\u9593\u306b \u30af\u30ed\u30b9\u3057\u59cb\u3081\u305f\n\u307b\u3089 \u4eca\u3060 \u3053\u3053\u3067 \u5149\u308b\u306a\u3089\n\u541b\u3060\u3088 \u541b\u306a\u3093\u3060\u3088 \u6559\u3048\u3066\u304f\u308c\u305f\n\u6697\u95c7\u306f\u7d42\u308f\u308b\u304b\u3089\n\n[Chorus]\n\u541b\u3060\u3088 \u541b\u306a\u3093\u3060\u3088 \u6559\u3048\u3066\u304f\u308c\u305f\n\u6697\u95c7\u3082\u5149\u308b\u306a\u3089 \u661f\u7a7a\u306b\u306a\u308b\n\u60b2\u3057\u307f\u3092\u7b11\u9854\u306b \u3082\u3046\u96a0\u3055\u306a\u3044\u3067\n\u714c\u3081\u304f\u3069\u3093\u306a\u661f\u3082 \u541b\u3092\u7167\u3089\u3059\u304b\u3089\n\n[Post-Chorus]\n\u7b54\u3048\u306f\u3044\u3064\u3067\u3082 \u5076\u7136\uff1f\u5fc5\u7136\uff1f\n\u3044\u3064\u304b\u9078\u3093\u3060\u9053\u3053\u305d \u904b\u547d\u306b\u306a\u308b\n\u63e1\u308a\u3057\u3081\u305f\u305d\u306e\u5e0c\u671b\u3082\u4e0d\u5b89\u3082\n\u304d\u3063\u3068\u4e8c\u4eba\u3092\u52d5\u304b\u3059 \u5149\u306b\u306a\u308b\u304b\u3089"
    lyric = "[7!!(\u30bb\u30d6\u30f3\u30a6\u30c3\u30d7\u30b9)\u300c\u30aa\u30ec\u30f3\u30b8\u300d\u6b4c\u8a5e]\n\n[Verse 1]\n\u5c0f\u3055\u306a\u80a9\u3092\n\u4e26\u3079\u3066\u6b69\u3044\u305f\n\u4f55\u3067\u3082\u306a\u3044\u4e8b\u3067\u7b11\u3044\u5408\u3044\n\u540c\u3058\u5922\u3092\u898b\u3064\u3081\u3066\u3044\u305f\n\u8033\u3092\u6f84\u307e\u305b\u3070\n\u4eca\u3067\u3082\u805e\u3053\u3048\u308b\n\u541b\u306e\u58f0 \u30aa\u30ec\u30f3\u30b8\u8272\u306b\n\u67d3\u307e\u308b\u8857\u306e\u4e2d\n\n[Pre-Chorus]\n\u541b\u304c\u3044\u306a\u3044\u3068\u672c\u5f53\u306b\u9000\u5c48\u3060\u306d\n\u5bc2\u3057\u3044\u3068\u8a00\u3048\u3070\u7b11\u308f\u308c\u3066\u3057\u307e\u3046\u3051\u3069\n\u6b8b\u3055\u308c\u305f\u3082\u306e \u4f55\u5ea6\u3082\u78ba\u304b\u3081\u308b\u3088\n\u6d88\u3048\u308b\u3053\u3068\u306a\u304f\u8f1d\u3044\u3066\u3044\u308b\n\n[Chorus]\n\u96e8\u4e0a\u304c\u308a\u306e\u7a7a\u306e\u3088\u3046\u306a\n\u5fc3\u304c\u6674\u308c\u308b\u3088\u3046\u306a\n\u541b\u306e\u7b11\u9854\u3092\u61b6\u3048\u3066\u3044\u308b\n\u601d\u3044\u51fa\u3057\u3066\u7b11\u9854\u306b\u306a\u308b\n\u304d\u3063\u3068\u4e8c\u4eba\u306f\u3042\u306e\u65e5\u306e\u307e\u307e\n\u7121\u90aa\u6c17\u306a\u5b50\u4f9b\u306e\u307e\u307e\n\u5de1\u308b\u5b63\u7bc0\u3092\u99c6\u3051\u629c\u3051\u3066\u3044\u304f\n\u305d\u308c\u305e\u308c\u306e\u660e\u65e5\u3092\u898b\u3066\n\n[Verse 2]\n\u4e00\u4eba\u306b\u306a\u308c\u3070\n\u4e0d\u5b89\u306b\u306a\u308b\u3068\n\u7720\u308a\u305f\u304f\u306a\u3044\u591c\u306f\n\u8a71\u3057\u7d9a\u3051\u3066\u3044\u305f\n\n[Pre-Chorus]\n\u541b\u306f\u3053\u308c\u304b\u3089\u4f55\u3092\u898b\u3066\u3044\u304f\u3093\u3060\u308d\u3046\n\u79c1\u306f\u3053\u3053\u3067\u4f55\u3092\u898b\u3066\u3044\u304f\u306e\u3060\u308d\u3046\n\u6c88\u3080\u5915\u713c\u3051 \u30aa\u30ec\u30f3\u30b8\u306b\u67d3\u307e\u308b\u8857\u306b\n\u305d\u3063\u3068\u6d99\u3092\u9810\u3051\u3066\u307f\u308b\n\n[Chorus]\n\u4f55\u5104\u3082\u306e\u5149\u306e\u4e2d\n\u751f\u307e\u308c\u305f\u4e00\u3064\u306e\u611b\n\u5909\u308f\u3089\u306a\u304f\u3066\u3082\u5909\u308f\u3063\u3066\u3057\u307e\u3063\u3066\u3082\n\u541b\u306f\u541b\u3060\u3088 \u5fc3\u914d\u7121\u3044\u3088\n\u3044\u3064\u304b\u4e8c\u4eba\u304c\u5927\u4eba\u306b\u306a\u3063\u3066\n\u7d20\u6575\u306a\u4eba\u306b\u51fa\u4f1a\u3063\u3066\n\u304b\u3051\u304c\u3048\u306e\u306a\u3044\u5bb6\u65cf\u3092\u9023\u308c\u3066\n\u3053\u306e\u5834\u6240\u3067\u9022\u3048\u308b\u3068\u3044\u3044\u306a\n\n[Instrumental Break]\n\n[Chorus]\n\u96e8\u4e0a\u304c\u308a\u306e\u7a7a\u306e\u3088\u3046\u306a\n\u5fc3\u304c\u6674\u308c\u308b\u3088\u3046\u306a\n\u541b\u306e\u7b11\u9854\u3092\u61b6\u3048\u3066\u3044\u308b\n\u601d\u3044\u51fa\u3057\u3066\u7b11\u9854\u306b\u306a\u308b\n\u4f55\u5104\u3082\u306e\u5149\u306e\u4e2d\n\u751f\u307e\u308c\u305f\u4e00\u3064\u306e\u611b\n\u5de1\u308b\u5b63\u7bc0\u3092\u99c6\u3051\u629c\u3051\u3066\u3044\u304f\n\u305d\u308c\u305e\u308c\u306e\u660e\u65e5\u3092\u898b\u3066\n\n[Outro]\n\u305d\u308c\u305e\u308c\u306e\u5922\u3092\u9078\u3093\u3067"


    print(translator.translate_lyrics(f"{lyric}",
                                      use_context=True))