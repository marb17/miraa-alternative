# STANDARD LIBRARY
import re
import gc
import time
from typing import Any, Generator
import platform

from engine.core.llm_model import LLMModel
from engine.utils.classes.dataclasses import UIPromptRequest
# HELPER LIBRARIES
from engine.utils.functions.other import contains_japanese

# PYPI LIBRARIES

if platform.system() == "Windows":
    from lmdeploy import GenerationConfig
elif platform.system() == "Darwin":
    pass
    # raise NotImplementedError

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

    def _clean_translation_response(self, input_string: str) -> str:
        input_string = input_string.strip()

        m = re.search(r"^\W*Translation:\W*\s*(.+)$", input_string, re.IGNORECASE | re.MULTILINE)
        if m:
            input_string = m.group(1)
        else:
            input_string = input_string.split("\n")[0]

        input_string = self._clean_unicode(input_string)
        input_string = input_string.strip().strip('*"').strip()

        return input_string

    def translate_lyrics(self, texts: list[str] | str, use_context: bool = False) -> list[Any]:
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
            context = '\n'.join(texts)

        # setup prompts to be sent
        def get_context(data: list[str], idx: int, radius: int = 4) -> str:
            start = max(0, idx - radius)
            end = min(len(data), idx + radius + 1)

            return "\n".join(
                line.strip()
                for i, line in enumerate(data[start:end], start=start)
                if i != idx and line.strip()
            )

        SYSTEM_TRANSLATION_PROMPT = """You are an expert Japanese-to-English lyric translator. Your priority is full semantic fidelity: nothing in the Japanese may be dropped, softened, or generalized, and nothing may be added.

        ### COMPLETENESS
        English may be, and often must be, longer than the Japanese. Never shorten a line to make it sound cleaner or more poetic. If a choice is between a smooth phrase that loses an element and a slightly longer phrase that keeps it, choose the longer one.

        Reflect every one of these if present in the line:
        - Adverbs and degree, time, and frequency words (今でも, 何度も, 限りなく, もう, まだ, ずっと, 少しも)
        - Degree clauses (〜ほど, 〜くらい, 〜だけ, 〜ばかり)
        - Subordinate and conditional clauses (〜なら, 〜たら, 〜のに, 〜ても, 〜まま) and て-form chains
        - Passive, causative, and "affected by" verbs (〜られる, 気を取られる, 彩られる, 纏う)
        - Sentence-final particles and endings (さ, よ, ね, な, だろ, や, のさ), which carry tone and assertion
        - Specific nouns (未練, 孤独, 罰). Do not swap them for generic ones.

        ### ACCURACY
        - Resolve omitted subjects and objects from context, and keep the pronoun the context best supports.
        - Translate idioms by their real meaning, never word by word, and make sure the result does not reverse the meaning.
        - Check negation carefully. Adjective negation like 眠くはない means "not sleepy", not "won't sleep".
        - Keep particle relationships distinct: 愛ある罰 ("a punishment that has love in it") is not 愛への罰 ("a punishment for/toward love").
        - Treat colloquial contractions (ちゃ, ってる, ぶっ/ふっ prefixes) as their full forms, but keep their force.
        - Prefer the specific verb or noun over a generic one.

        ### BOUNDARIES
        - Translate only the target line. Context may resolve ambiguity but must never add content from other lines.
        - Do not explain, gloss, or interpret. No parenthetical notes, symbolism, or emotional conclusions the line does not state.
        - If the line trails off on a conjunction or conditional, end the English the same way. Do not finish the thought.
        - Keep deliberate repetition, and translate identical Japanese lines identically.
        - Keep non-Japanese text (English words, vocal syllables) exactly as written.

        ### EXAMPLES (style and completeness only; the lines are unrelated to the target)
        Japanese: 今でも君の声が耳から離れない
        Translation: Even now, your voice won't leave my ears.

        Japanese: 何度も諦めようとしたのに
        Translation: Even though I tried to give up so many times

        Japanese: もう泣かないさ
        Translation: I'm not going to cry anymore, you know.

        Japanese: 雨に打たれた街を歩いていた
        Translation: I was walking through the city, beaten by the rain.

        ### OUTPUT
        Output exactly one line and nothing else:
        Translation: <English translation>"""

        def build_prompt(text: str, context: str = None, use_context: bool = False) -> str:
            prompt_parts = [SYSTEM_TRANSLATION_PROMPT.strip()]

            if context and context.strip():
                prompt_parts.append(
                    "FULL SONG IN THE ORIGINAL LANGUAGE (reference only):\n"
                    "Use it only to determine the speaker, addressee, omitted subjects/objects, "
                    "and emotional situation. Do not translate it or take content from it.\n"
                    f"<<<\n{context.strip()}\n>>>"
                )

            prompt_parts.append(
                "TARGET LYRIC (translate this line only):\n"
                f"<<<\n{text.strip()}\n>>>\n\n"
                "Keep every adverb, clause, particle, and sentence-final nuance. "
                "Do not add anything from neighboring lines or your own interpretation.\n"
                "Output exactly one line:\n"
                "Translation: <English translation>"
            )

            return "\n\n".join(prompt_parts)

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
            prompts.append(build_prompt(text,
                                        context,
                                        use_context))
            # endregion
            mapping_index.append((idx, "do"))
            processed_lyrics[text] = idx

        #todo json schema kwargs? thanks pycharm go to implementation

        # gen_config = GenerationConfig(
        #     max_new_tokens=96,
        #     do_sample=True,
        #     temperature=0.3,
        #     top_p=0.9,
        #     top_k=40,
        #     min_p=0.0,
        #     repetition_penalty=1.0,
        #     random_seed=42,
        # )
        gen_config = GenerationConfig(
            max_new_tokens=96,
            do_sample=False,
            repetition_penalty=1.0,
        )

        if not prompts:
            raise ValueError("No prompts found to be generated, please re-check lyrics to ensure they are in Japanese Scripts")

        with LLMModel() as llm:
            inference_response = llm.batch_inference(prompts, estimated_output_cost=50, gen_config=gen_config)
            responses = dict(zip([idx for idx, exp in mapping_index if exp == "do"], inference_response))

        results = []

        for idx, d in enumerate(data):
            if (idx, "do") in mapping_index:
                response = responses[idx]

                # remove translation header
                formatted_response = self._clean_translation_response(response)
                results.append(formatted_response)
            elif (idx, "dup") in mapping_index:
                prev_processed_idx = processed_lyrics[d]
                response = responses[prev_processed_idx]

                # remove translation header
                formatted_response = self._clean_translation_response(response)
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

        with LLMModel() as llm:
            data = llm.batch_inference([prompt])
            data = data[0].strip()

        data = self._clean_translation_response(data)

        return data