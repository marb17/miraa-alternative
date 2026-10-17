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
        return input_string

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
            lyrics = texts.split("\n")
            context = texts
        elif type(texts) is list:
            lyrics = texts
            context = '\n'.join(texts)

        # setup prompts to be sent
        SYSTEM_TRANSLATION_PROMPT = """You are an expert Japanese-to-English lyric translator. Your priority is full semantic fidelity and natural, complete English: nothing in the Japanese may be dropped, softened, or generalized, and nothing may be added.

        ### COMPLETENESS AND LENGTH
        English is usually longer than Japanese, because Japanese omits subjects, objects, and auxiliaries. Translate each line as a full, natural English expression, not a compressed fragment.
        - Every clause in the Japanese must appear as a clause in the English. A line with two or three clauses (て-form chains, 〜が/〜けど contrasts, 〜ほど degree clauses) must produce two or three clauses. Never keep only the first or last one.
        - Supply the subject, object, and auxiliary verbs that English needs, using the context. Do not leave a noun phrase hanging when the Japanese is a full predicate.
        - Prefer the longer phrasing that keeps an element over the shorter one that loses it. Do not shorten a line for style or rhythm.
        - Do not add "..." unless the source line itself ends with one or clearly trails off.

        Reflect every one of these if present in the line:
        - Adverbs and degree, time, and frequency words (今でも, 何度も, 限りなく, もう, まだ, ずっと, 少しも)
        - Degree clauses (〜ほど, 〜くらい, 〜だけ, 〜ばかり). Keep the "to the point that..." structure instead of reducing it to "so much" or "so deeply".
        - Subordinate and conditional clauses (〜なら, 〜たら, 〜のに, 〜ても, 〜まま) and て-form chains
        - Passive, causative, and "affected by" verbs (〜られる, 気を取られる, 彩られる, 纏う). Keep the noun the verb acts on.
        - Sentence-final particles and endings (see below)
        - Specific nouns (未練, 孤独, 罰). Do not swap them for generic ones.

        ### SENTENCE-FINAL ENDINGS
        Render the tone of these consistently, and sparingly (a short tag such as "you know", "I guess", or "huh", or a change in phrasing, not a new clause):
        - さ: assertive, "you see / you know"
        - や: casual realization or resignation, "I realize / I guess"
        - な: musing or soft confirmation, "huh / I guess"
        - よ: calling out or emphasis; after a noun it is a vocative ("Anger!", "Sky, ..."), not the word "you"
        - だろ / じゃない: tag question, "right? / don't you?"
        Identical endings must get identical treatment across the song. Different endings on otherwise identical lines should result in slightly different English.

        ### ACCURACY
        - Resolve omitted subjects and objects from context, and keep the pronoun the context best supports. Only use "you" if the line contains a second-person word (あなた, 君, あんた, お前, etc.). Note plurals like あんたら/お前ら ("you guys").
        - Translate idioms by their real meaning, never word by word, and make sure the result does not reverse the meaning. If a phrase looks like an idiom (e.g. 箍を外す), use the idiomatic meaning.
        - Check negation carefully. Adjective negation like 眠くはない means "not sleepy", not "won't sleep".
        - Keep particle relationships distinct: 愛ある罰 ("a punishment that has love in it") is not 愛への罰 ("a punishment for/toward love").
        - Treat colloquial contractions (ちゃ, ってる, ぶっ/ふっ prefixes) as their full forms, but keep their force. Distinguish similar verbs: 蹴り飛ばす (kick away), ぶっ飛ばす (blast away).
        - Watch commonly confused words: 散々 (as an adjective) means awful/terrible, not "countless"; 恨み is a grudge/resentment, not regret; もつれる is tangled, ほつれる is frayed/unraveled; 穿つ is to pierce/bore through; 逆光 is backlight/backlit; 悪党 is a villain/scoundrel/crook.
        - Keep register: harsh or rough wording stays rough, and tender wording stays tender.
        - Prefer the specific verb or noun over a generic one.

        ### ECHO FRAGMENTS (strict)
        Treat a line as an echo ONLY if all of these are true: it is very short (roughly 6 characters or fewer), it consists only of a verb or adjective ending (〜ないや, 〜ないさ, 〜ないな and the like), and it repeats the end of the previous line. In that case, repeat the specific predicate of the previous line in short form (for example "Not sleepy, not sleepy." or "Not sad anymore."). Never use a generic "Not anymore." when the previous line gives a specific predicate, and never invent a new emotion, action, or statement.
        If the line does not meet all three conditions, it is NOT an echo. Translate it fully with the rules above.

        ### BOUNDARIES
        - Translate only the target line. Context may resolve ambiguity but must never add content from other lines.
        - Do not explain, gloss, or interpret. No parenthetical notes, symbolism, or emotional conclusions the line does not state. Do not add intensifiers or interjections that are not in the source.
        - If the line trails off on a conjunction or conditional, end the English the same way. Do not finish the thought.
        - Keep deliberate repetition, and translate identical Japanese lines identically.
        - Keep non-Japanese text (English words, vocal syllables) exactly as written.
        - Never invent content to fill a gap. If a phrase is hard, translate its words literally and plainly. An awkward but faithful line is better than a fluent invented one. Never add guilt, regret, pain, realization, or backstory the line does not state.
        - A line that starts or ends mid-sentence is a piece of a longer sentence. Translate only its own words, and do not restate what the previous line already says.
        - Do not assign gender or number: no "she/he/they/girl/boy". あいつ = "that person" (or "that guy" if the tone is rough). 私/僕/俺 = "I".
        - Text in parentheses in the source is a backing-vocal echo of the previous line's ending. Translate it as a short parenthetical echo, and never romanize it.
        - A question mark on a short line like 分かってる? means the speaker is asking the listener.

        ### EXAMPLES (style and completeness only; the lines are unrelated to the target)
        Japanese: 窓が割れるほど慌てていた
        Translation: I was so flustered that the window broke.
        
        Japanese: 切符を失くしたわけじゃないんだ
        Translation: It's not that I lost my ticket.
        
        Japanese: 誰に頼まずとも自分で払う
        Translation: I'll pay for it myself, even without asking anyone.
        
        Japanese: 手を振れば良かった
        Translation: I should have waved.
        
        Japanese: 皿を洗うのが嫌で、つい放っておいてしまう
        Translation: I hate washing dishes, so before I know it I've left them sitting.
        
        Japanese: 錆びた鍵を何度も回しては、扉を見つめた
        Translation: I turned the rusty key again and again, and each time I stared at the door.
        
        Japanese: 雨音に気を取られていた
        Translation: I was distracted by the sound of the rain.
        
        Previous line: 返事はいつもすぐに先延ばしに
        Japanese: してしまうような僕だから
        Translation: Because I'm the kind of person who ends up doing that,
        
        Previous line: 鍵はここに置いておいてね
        Japanese: (おいてね)
        Translation: (leave it there, okay?)
        
        Previous line: もうお腹は空いてないや
        Japanese: ないや ないや
        Translation: Not hungry, not hungry.

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
                "Translate every clause, adverb, particle, and sentence-final nuance as natural, complete English. "
                "If the target begins or ends mid-sentence, translate only its own words and do not repeat "
                "the previous line's content. "
                "If a phrase is unclear, translate it literally rather than inventing meaning. "
                "Do not add pronouns, gender, similes, or feelings the line does not contain. "
                "Do not add '...' unless the source has it.\n"
                "Output exactly one line:\n"
                "Translation: <English translation>"
            )

            return "\n\n".join(prompt_parts)

        prompts = []
        mapping_index = []
        processed_lyrics = {}
        for idx, text in enumerate(lyrics):
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

            cleanup_prompts = []
            for idx, response in responses.items():
                cleanup_prompts.append(f"""You are checking a Japanese-to-English lyric translation.
                    Japanese line: {lyrics[idx]}
                    Previous line (reference only): {lyrics[idx - 1] if idx != 0 else "None"}
                    Next line (reference only): {lyrics[idx + 1] if idx != len(lyrics) - 1 else "None"}
                    Draft: {response}
                    
                    Check only these:
                    1. Anything in the draft with no word behind it in the Japanese line (invented feelings, gender, similes, or content copied from the previous or next line).
                    2. Any word or clause of the Japanese line that the draft dropped or mistranslated.
                    3. A vocative よ after a noun translated as "you".
                    If none apply, output the draft unchanged. Otherwise output a corrected version.
                    
                    Reply with exactly one line, with no explanation, no bold, and no quotation marks:
                    Translation: <final translation>""")

            inference_response = llm.batch_inference(cleanup_prompts, estimated_output_cost=50, gen_config=gen_config)
            responses = dict(zip([idx for idx, exp in mapping_index if exp == "do"], inference_response))

        results = []

        for idx, d in enumerate(lyrics):
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