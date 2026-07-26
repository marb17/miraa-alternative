# STANDARD LIBRARY
import re
import gc
import time
from typing import Any, Generator

from engine.core.llm_model import WindowsLLMModel
from engine.utils.classes.dataclasses import UIPromptRequest
# HELPER LIBRARIES
from engine.utils.functions.other import contains_japanese

# PYPI LIBRARIES
from lmdeploy import GenerationConfig

from engine.utils.logger import Logger
logger = Logger(__name__)


class Translator:
    def __init__(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()
        return False

    def _close(self) -> None:
        logger.debug("Closing Translator")

        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    # remap all unprocessed, remove special whitespace and strips
    @staticmethod
    def _clean_unicode(input_string: str) -> str:
        input_string = re.sub(r"[\u2005\u200a\u205f\u2014]", " ", input_string)
        input_string = re.sub(r"\u2019", "'", input_string)
        input_string = input_string.strip()

        return input_string

    def _clean_translation_header_and_unicode(self, input_string: str) -> str:
        """Also cleans Unicode"""
        input_string = input_string.strip()
        input_string = re.sub(
            r"^\*?\*?Translation:\*?\*?\s*", "", input_string, flags=re.IGNORECASE
        )
        input_string = self._clean_unicode(input_string)

        return input_string

    def translate_lyrics(self, texts: list[str] | str, use_context: bool = False) -> Generator[UIPromptRequest, None, list[Any]]:
        """
        Translates lyrics
        :param texts: Pure string or list of strings (pure string splits by newlines)
        :type texts: str | list[str]
        :param use_context: Whether to use context for the prompts
        :type use_context: bool
        :return: Translated lyrics in list form
        :rtype: list[str]
        """
        now = time.time()

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

        gen_config = GenerationConfig(max_new_tokens=50)

        if not prompts:
            raise ValueError("No prompts found to be generated, please re-check lyrics to ensure they are in Japanese Scripts")

        with WindowsLLMModel() as llm:
            inference_response = yield from llm.batch_inference(prompts, estimated_output_cost=50, gen_config=gen_config)
            responses = dict(zip([idx for idx, exp in mapping_index if exp == "do"], inference_response))

        results = []

        for idx, d in enumerate(data):
            if (idx, "do") in mapping_index:
                response = responses[idx]

                # remove translation header
                formatted_response = self._clean_translation_header_and_unicode(response)
                results.append(formatted_response)
            elif (idx, "dup") in mapping_index:
                prev_processed_idx = processed_lyrics[d]
                response = responses[prev_processed_idx]

                # remove translation header
                formatted_response = self._clean_translation_header_and_unicode(response)
                results.append(formatted_response)
            else:
                formatted_response = self._clean_unicode(d)
                results.append(formatted_response)

        logger.debug(f"Finished translating in {(time.time() - now):.2f} seconds")

        return results

    def romaji_to_script(self, lyrics: str) -> str:
        prompt = f"""
        You are an expert Japanese Language Processor specializing in Orthographic Reconstruction. 

        Your sole task is to reconstruct raw Romaji text back into authentic Japanese orthography (a natural, native balance of Kanji, Hiragana, and Katakana).

        ** STRICT REGULATORY RULES **:
        1. DO NOT translate the meaning into English or any other language. 
        2. DO NOT alter, expand, or poetically reinterpret the lines. This is a script conversion task, not a creative rewriting task.
        3. Preserve the exact line breaks, stanzas, and structural layout of the input text.
        4. If a line contains actual English words or punctuation, preserve them exactly as they are written.
        5. Use the surrounding thematic context of the verse to choose the correct Kanji for homonyms (e.g., distinguishing "kimi" as 君 vs. 黄身 based on the song's tone).

        ** INPUT ROMAJI LYRICS **:
        {lyrics}
    
        ** OUTPUT FORMAT **:
        Return ONLY the reconstructed Japanese script. Do not include conversational filler, notes, or introductions. Use the exact block wrapper below:

        **Translation:**
        <your reconstructed Japanese text here>
        """

        with WindowsLLMModel() as llm:
            data = llm.batch_inference([prompt])[0].strip()

        data = self._clean_translation_header_and_unicode(data)

        return data