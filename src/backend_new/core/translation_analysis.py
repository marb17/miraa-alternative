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

        self._llm = None
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

        self._free_vram = None
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
        from lmdeploy import pipeline

        self._pipe = pipeline(self._model_id)

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

        if self._pipe is None:
            self.init_model()

        # region batch sizing
        if batch_size > 1:
            pass
        if batch_size == 0:
            batch_size = len(prompts)
        if batch_size == -1:
            # automatic sizing
            available_vram = self._free_vram - self._model_weight
            total_prompt_cost = self._calculate_prompt_cost(prompts, estimated_output_cost)

            num_batches = ceil(total_prompt_cost / available_vram) + 1
            num_prompts = len(prompts)

            batch_size = ceil(num_prompts / num_batches)

        batched_prompts = list(batched(prompts, batch_size))
        # endregion

        results = []
        for batch in batched_prompts:
            results.extend([response.text for response in self._pipe(list(batch))])
            gc.collect()
            torch.cuda.empty_cache()

        return results


class Translator:
    def __init__(self) -> None:
        self._model = LLMModel()

    def translate_lyrics(self, texts: list[str] | str, use_context: bool = False) -> list[str]:
        """
        Translates lyrics
        :param texts: Pure string or list of strings (pure string splits by newlines)
        :param use_context: Whether to use context for the prompts
        :return: Translated lyrics in list form
        """
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
        for idx, text in enumerate(data):
            # skips certain conditions
            if text == '':
                continue
            if text.startswith("[") and text.endswith("]"):
                continue
            if not contains_japanese(text):
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
            mapping_index.append(idx)

        responses = dict(zip(mapping_index, self._model.batch_inference(prompts, estimated_output_cost=50)))

        results = []
        # remap all unprocessed, remove special whitespace and strips
        for idx, data in enumerate(data):
            if idx in mapping_index:
                response = responses[idx]
                # remove translation header
                formatted_response = response.strip()
                formatted_response = re.sub(
                    r"^\*?\*?Translation:\*?\*?\s*", "", formatted_response, flags=re.IGNORECASE
                )
                formatted_response = re.sub(r"[\u2005\u200a\u205f]", " ", formatted_response)
                results.append(formatted_response)
            else:
                formatted_response = re.sub(r"[\u2005\u200a\u205f]", " ", data)
                formatted_response = formatted_response.strip()
                results.append(formatted_response)

        return results

if __name__ == "__main__":
    llm_model = LLMModel()
    translator = Translator()
#
#     print(translator.translate_text(["姿形の見えない魔物",
# "どこへでも連れて行くよ",
# "街を見下ろして"]))

    lyric = "[\u30dd\u30eb\u30ab\u30c9\u30c3\u30c8\u30b9\u30c6\u30a3\u30f3\u30b0\u30ec\u30a4\u306e\u300cJET\u300d\u6b4c\u8a5e]\n\n[Intro]\nTaking off, taking off\n\u59ff\u5f62\u306e\u898b\u3048\u306a\u3044\u9b54\u7269\n\u3069\u3053\u3078\u3067\u3082\u9023\u308c\u3066\u884c\u304f\u3088\n\u8857\u3092\u898b\u4e0b\u308d\u3057\u3066\nWell, you are my star\n\n[Verse 1]\n\u8033\u3092\u585e\u3044\u3067\u3082\u805e\u3053\u3048\u308b\u306e\n\u885d\u52d5\u306e\u5f3e\u3051\u308b\u97f3\u304c\nUh, just a moment, du-ru-du, du-ru-du, du-ru-du\nI am\u2005just\u2005waiting for my,\u2005du-ru-du, du-ru-du, du-ru-du\n\u4e00\u77ac\u306e\u9759\u5bc2\u306e\u5302\u3044\n\u3042\u306a\u305f\u3092\u601d\u3044\u51fa\u3059\n\u5225\u308c\u969b\u306e\u3042\u306a\u305f\u3092\u601d\u3046\n\u91d1\u66dc\u306e\u5348\u5f8c\u306e\u7a7a\u60f3\u3055\nGive me a second,\u2005du-ru-du, du-ru-du, du-ru-du\n\u604b\u3059\u308b\u767d\u663c\u5922, du-ru-du, du-ru-du\n\u4eca\u306f\u4f55\u3092\u3057\u3066\u3044\u308b\u306e\uff1f\n\u3042\u306a\u305f\u304c\u5c45\u308c\u3070\u3069\u3053\u3067\u3082\u884c\u3051\u3066\u3057\u307e\u3046\n\n[Chorus]\n\u6025\u3044\u3067\uff01\nTaking off, taking off\n\u59ff\u5f62\u306e\u898b\u3048\u306a\u3044\u9b54\u7269\n\u8033\u3092\u585e\u3044\u3067\u3082\u805e\u3053\u3048\u308b\u885d\u52d5\u306e\u97f3\nYou're just moving\u205fon,\u205fmoving\u205fon\n\u4eca\u306f\u3069\u3053\u304b\u9060\u304f\u3078\u9003\u3052\u3088\u3046\n\u3069\u3053\u3078\u3067\u3082\u9023\u308c\u3066\u884c\u304f\u3088\n\u8857\u3092\u898b\u4e0b\u308d\u3057\u3066\nYou are my\u205fjet star\n\n[Verse 2]\n\u4e00\u4eba\u304d\u308a\u306e\u90e8\u5c4b\u3067\u9a12\u3050\n\u3072\u3068\u308a\u3067\u306b\u71c3\u3048\u308b\u9f13\u52d5\u3055\nNobody like\u205fyou, du-ru-du, du-ru-du, du-ru-du\n\u604b\u3059\u308b\u30c0\u30f3\u30b9\u30d5\u30ed\u30a2, du-ru-du, du-ru-du, du-ru-du\n\u5c0f\u3055\u3059\u304e\u308b\u90e8\u5c4b\n\u3042\u3042\u3001\u79c1\u306e\u77e5\u3089\u306a\u3044\u305d\u3093\u306a\u9854\u3057\u306a\u3044\u3067\n\n[Chorus]\nLoving you, loving you\n\u5618\u3082\u8aa0\u3082\u8981\u3089\u306a\u3044\u3001up to you\n\u4e00\u4eba\u306e\u90e8\u5c4b\u3001\u7d9a\u304f\u590f\u306e\u5302\u3044\nI'm just moving on, moving on\n\u3042\u306a\u305f\u306b\u51fa\u4f1a\u3046\u307e\u3067\u306f\u79c1\n\u306d\u3048\u3001\u3069\u3093\u306a\u9854\u3092\u3057\u3066\u751f\u304d\u3066\u304d\u305f\u3093\u3060\u3063\u3051\uff1f\nAll I need is you\n\n[Pre-Chorus]\nLadies and gentlemen\nFor your comfort, we will be dimming the main cabin lights\nIf you wish to continue reading, you will find your reading light\nIn the panel above you, thank you\n\n[Chorus]\nTaking off, taking off\n\u59ff\u5f62\u306e\u898b\u3048\u306a\u3044\u9b54\u7269\n\u8033\u3092\u585e\u3044\u3067\u3082\u805e\u3053\u3048\u308b\u885d\u52d5\u306e\u97f3\nYou're just moving on, moving on\n\u53e3\u306f\u707d\u3044\u306e\u3082\u3068\u306a\u3089\u3070\n\u4f55\u3082\u8a00\u308f\u306a\u304f\u3066\u3044\u3044\u3088\n\u3069\u3053\u306b\u884c\u3053\u3046\uff1f\nTaking off, taking off\n\u4eca\u306f\u660e\u65e5\u307e\u3067\u5f85\u3066\u306a\u3044 Taking a trip\n\u3053\u306e\u590f\u304c\u7d42\u308f\u308b\u524d\u306b\n\u79c1\u305f\u3061\u304d\u3063\u3068\u4f1a\u3044\u307e\u3057\u3087\u3046\n\n[Outro]\nAh-ah\nDu-ru-du, du-ru-du, du-ru-du\nNobody like you, ooh-ooh, ooh-ooh\nMoving on, moving on\nNobody like you are my star"

    print(translator.translate_lyrics(f"{lyric}",
                                      use_context=True))