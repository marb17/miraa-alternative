# STANDARD LIBRARIES
import gc
import json
import multiprocessing
import os
import subprocess
import sys
import time
import uuid, hashlib
from collections.abc import Generator
from pathlib import Path
from typing import Literal
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydub import AudioSegment

from engine.utils.classes.dataclasses import UIPromptRequest, LyricSegment
from engine.utils.default.default_var import AUDIO_MODEL_PRESETS
# HELPER LIBRARIES
from engine.utils.functions.filesystem import read_json_file
from engine.utils.logger import Logger
# CONSTANTS
from engine.utils.paths import TEMP_DIR, MODEL_DIR

# PYPI LIBRARIES
# from sudachipy.morpheme import Morpheme
# from sudachipy import dictionary, tokenizer
import nagisa
logger = Logger(__name__)

if sys.platform == "darwin":
    # from functools import partial
    # import tqdm
    # tqdm.tqdm = partial(tqdm.tqdm, disable=True)
    multiprocessing.set_start_method("fork", force=True)


ALLOWED_MODEL_NAMES = Literal["vocal_full", "vocal_clean", "instrumental_full", "instrumental_low_resource",
                              "htdemucs_ft", "htdemucs_6s",
                              "drum_sep", "dereverb", "crowd_iso",
                              "bs_reformer_sw"]

class AudioSeparation:
    # TODO fix docs here cuz its bad
    def __init__(self, model_name: ALLOWED_MODEL_NAMES = "vocal_full") -> None:
        """
        Initializes the AudioSeparation object.

        :param model_name: Model that will be used for separation.
        :type model_name: ALLOWED_MODEL_NAMES
        """

        from audio_separator.separator import Separator

        current_dir = Path(__file__).resolve().parent
        while current_dir.name != "src" and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        self._base_dir = current_dir

        self._output_dir = f'{self._base_dir / ".temp"}'
        self._model_file_dir = f'{self._base_dir / "models/audioseparator"}'

        # select model and list available models
        self._available_models = [key for key in AUDIO_MODEL_PRESETS]
        self._model_name = model_name

        # check if model available
        model = AUDIO_MODEL_PRESETS.get(model_name, None)
        if model is None:
            raise Exception(f"Model {model_name} not found, choose from: {self._available_models}")
        else:
            self._selected_model = None

            if AUDIO_MODEL_PRESETS[self._model_name].type == "ensemble":
                self._selected_model = Separator(output_dir=str(self._output_dir),
                                                 model_file_dir=str(self._model_file_dir),
                                                 ensemble_preset=AUDIO_MODEL_PRESETS[self._model_name].name,
                                                 use_autocast=True,
                                                 use_soundfile=False,
                                                 normalization_threshold=0.9,
                                                 mdx_params={"batch_size": 32},
                                                 vr_params={"batch_size": 32},
                                                 mdxc_params={"batch_size": 32})
            elif AUDIO_MODEL_PRESETS[self._model_name].type == "single":
                self._selected_model = Separator(output_dir=str(self._output_dir),
                                                 model_file_dir=str(self._model_file_dir),
                                                 use_autocast=True,
                                                 use_soundfile=False,
                                                 normalization_threshold=0.9,
                                                 mdx_params={"batch_size": 32},
                                                 vr_params={"batch_size": 32},
                                                 mdxc_params={"batch_size": 32})

    def __del__(self) -> None:
        self._close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()
        return False

    def _close(self) -> None:
        if hasattr(self._selected_model, 'model_data'):
            self._selected_model.model_data = None

        self._selected_model = None

        gc.collect()

        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    @property
    def separator_objects(self) -> list[str]:
        return self._available_models

    def _init_model(self) -> None:
        if self._selected_model is None:
            raise ValueError(f"Model wrapper for {self._model_name} did not initialize properly")
        if AUDIO_MODEL_PRESETS[self._model_name].type == "ensemble":
            self._selected_model.load_model()
        elif AUDIO_MODEL_PRESETS[self._model_name].type == "single":
            self._selected_model.load_model(model_filename=AUDIO_MODEL_PRESETS[self._model_name].name)

    def separate_audio(self, audio_path: str | Path, audio_to_save: None | list[str] = None) -> bool:
        """
        Separates vocals into respective stems determined by model used
        :param audio_path: Path to the file
        :type audio_path: str | Path
        :return: None
        :rtype: None
        """
        logger.debug(f"Initializing '{self._model_name}'")
        self._init_model()
        logger.debug("Finished loading model")

        run_id = uuid.uuid4().hex[:8]

        if isinstance(audio_path, str):
            win_audio_path = Path(audio_path)
        elif isinstance(audio_path, Path):
            win_audio_path = audio_path
        else:
            raise NotImplementedError

        # ALWAYS CONVERTS A PARENTLESS PATH TO BASE DIR AT .TEMP
        if len(win_audio_path.parts) == 1:
            win_audio_path = TEMP_DIR / win_audio_path

        logger.debug("Starting to separate into stems")
        now = time.time()
        output_files = self._selected_model.separate([win_audio_path])

        logger.debug(f"Took {(time.time() - now):.2f} seconds to separate stems")

        output_files = [Path(f) for f in output_files]

        def new_file_name(name: str, as_path: bool = False):
            if as_path:
                return Path(f"{str(self._output_dir)}/{win_audio_path.stem}_{name}.wav")
            else:
                return f"{str(self._output_dir)}/{win_audio_path.stem}_{name}.wav"

        def rename_file(file_path: Path, name: str) -> None:
            if len(file_path.parts) == 1:
                file_path = TEMP_DIR / file_path

            file_path.rename(new_file_name(name))

        rename_order = AUDIO_MODEL_PRESETS[self._model_name].rename_order

        # different models output differently, if flipped recheck default_var.py
        for file, rename_to in zip(output_files, rename_order):
            rename_file(file, rename_to)

        for file, rename in zip([new_file_name(suffix, as_path=True) for suffix in rename_order], rename_order):
            audio = AudioSegment.from_file(file)
            audio = audio + AUDIO_MODEL_PRESETS[self._model_name].gain
            if audio_to_save is None or rename in audio_to_save:
                audio.export(file, format="wav")
            else:
                file.unlink()

        logger.debug(f"Finished separating")

        return True



class ForcedAlignment:
    def __init__(self):
        ...

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        gc.collect()

        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

        return False

    def force_align_lyrics(self, audio_file: Path, lyrics: str | list[str]) -> list[LyricSegment]:
        os.environ["PYTHONUTF8"] = "1"
        os.environ["HF_HOME"] = str(MODEL_DIR / "faster_whisper")

        if isinstance(lyrics, str):
            lyrics = lyrics.split("\n")
        elif isinstance(lyrics, list):
            pass

        # run_id = uuid.uuid4().hex[:8]

        def run_alignment(audio: Path, added_silence: int = 0, vad: bool = False):
            now = time.time()

            mapping_index = list()

            for lyric in lyrics:
                if lyric.startswith("[") and lyric.endswith("]"):
                    mapping_index.append((lyric, False))
                elif not lyric:
                    mapping_index.append((lyric, False))
                else:
                    mapping_index.append((lyric, True))

            process_lyrics = [lyric[0] for lyric in mapping_index if lyric[1]]
            process_lyrics = "\n".join(process_lyrics)

            temp_lyric_path = Path(audio_file.parent / f"{audio_file.stem}_lyrics.txt")
            temp_audio_run_path = Path(audio_file.parent / f"{audio_file.stem}_run.wav")
            temp_segments_file = Path(audio_file.parent / f"{audio_file.stem}_segments.json")
            temp_lyric_path.write_text(process_lyrics,
                                       encoding="utf-8")

            silence = AudioSegment.silent(duration=added_silence)
            combined = silence + AudioSegment.from_wav(audio)
            combined.export(str(temp_audio_run_path), format="wav")

            first_pass_args = [
                "lyric-align", str(temp_audio_run_path), str(temp_lyric_path), "-o", "placeholder_output_file",
                 "--dump-segments", str(temp_segments_file),
                 "--model", "large-v3",
                 "--device", "cuda",
                 *([] if vad else ["--no-vad"]),
                 "--pairing", "auto",
                 # "--interpolate",
                 "--window", "1",
            ]

            segment_args = []

            for x in range(1, 6):
                for y in range(1, 5):
                    segment_args.append(
                        ["lyric-align", str(temp_audio_run_path), str(temp_lyric_path), "-o", "placeholder_output_file",
                         "--segments", str(temp_segments_file),
                         "--pairing", str(x),
                         # "--interpolate",
                         "--window", str(y),
                        ]
                    )

                if x == 1:
                    segment_args.append(
                        ["lyric-align", str(temp_audio_run_path), str(temp_lyric_path), "-o", "placeholder_output_file",
                         "--segments", str(temp_segments_file),
                         "--pairing", "auto",
                         # "--interpolate",
                         "--window", str(y),
                         ]
                    )


            def run_pass(arg_template: list[str]):
                arg_hash = hashlib.sha256(''.join(arg_template).encode("utf-8")).hexdigest()[:12]
                temp_holding_file = Path(audio_file.parent / f"{audio_file.stem}_holding_{arg_hash}.json")

                arg_template = [str(temp_holding_file) if arg == "placeholder_output_file" else arg for arg in arg_template]

                process = subprocess.Popen(
                    arg_template,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )

                return_code = process.wait()

                data = read_json_file(temp_holding_file)
                temp_holding_file.unlink()

                for section in data:
                    section["start"] = max(0.0, section["start"] - (added_silence / 1000)) if section["start"] else None
                    section["end"] = max(0.0, section["end"] - (added_silence / 1000)) if section["end"] else None

                return data, sum([seg["score"] for seg in data]) / len(data)


            first_data, first_score = run_pass(first_pass_args)
            pass_data = [first_data]
            scores = [first_score]

            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = {
                    executor.submit(run_pass, template) for template in segment_args
                }
                
                for future in as_completed(futures):
                    p_data, score = future.result()
                    pass_data.append(p_data)
                    scores.append(score)
                    logger.debug("Finished a pass")

            best_index = scores.index(max(scores))
            best_data = pass_data[best_index]
            logger.debug(f"Best Raw Pass: {best_index + 1} | Score: {scores[best_index]}")

            try:
                return best_data
            finally:
                temp_lyric_path.unlink()
                temp_audio_run_path.unlink()
                temp_segments_file.unlink()
                logger.debug(f"Finished Alignment in: {round(time.time() - now, 2)}")


        def run_test_pass():
            target_dbfs = -16

            temp_audio_file = Path(audio_file.parent / f"{audio_file.stem}_temp.wav")
            temp_dry_audio_file = Path(audio_file.parent / f"{audio_file.stem}_dry.wav")

            with AudioSeparation(model_name="dereverb") as sep:
                sep.separate_audio(audio_file, audio_to_save=["dry"])

            dry_audio = AudioSegment.from_wav(temp_dry_audio_file)

            temp_dry_audio_file.unlink()
            audio = AudioSegment.from_wav(audio_file)

            dry_audio = dry_audio.set_frame_rate(16000).set_channels(1).high_pass_filter(80)
            audio = audio.set_frame_rate(16000).set_channels(1).high_pass_filter(80)

            audios = [audio, audio, dry_audio, dry_audio]
            vad_setting = [False, True, False, True]

            scores = list()
            pass_data = list()

            for audio_data, use_vad in zip(audios, vad_setting):
                change_in_dbfs = target_dbfs - audio_data.dBFS
                final_audio = audio_data.apply_gain(change_in_dbfs)

                final_audio.export(str(temp_audio_file), format="wav")

                s_data = run_alignment(temp_audio_file, vad=use_vad)
                scores.append(sum([seg["score"] for seg in s_data]) / len(s_data))
                logger.debug(f"Average Score: {scores[-1]}")
                pass_data.append(s_data)

                temp_audio_file.unlink()

            best_index = scores.index(max(scores))
            logger.debug(f"Chose pass number: {best_index + 1}")
            logger.debug(f"Best Score: {scores[best_index]}")
            return best_index, audios, pass_data, vad_setting, scores

        def run_full_pass(audio_segment_data, 
                          extra_pass_data: list[list[dict]] | None = None, 
                          tries_per_pass: int = 3, 
                          use_vad: bool = False,
                          fail_pass_score: tuple[float, float] = (0.4, 0.75)):
            temp_audio_path = Path(audio_file.parent / f"{audio_file.stem}_align_run.wav")
            audio_segment_data.export(str(temp_audio_path), format="wav")

            pass_data = list()
            if extra_pass_data: pass_data.extend(extra_pass_data)

            times = [200, 600, 1350]

            for idx, t in enumerate(times):
                any_chosen = False
                best_data, best_score = None, 0

                for x in range(tries_per_pass):
                    logger.debug(f"Pass: {idx}, Try: {x}")
                    d = run_alignment(temp_audio_path, added_silence=(t + (x*125)), vad=use_vad)
                    avg_score = sum([seg["score"] for seg in d]) / len(d)
                    logger.debug(f"Average Score: {avg_score}")

                    if avg_score > best_score:
                        best_data, best_score = d, avg_score

                    if avg_score > fail_pass_score[0]:
                        logger.debug(f"Finished pass: {idx} | {x}")
                        pass_data.append(d)
                        any_chosen = True
                    else:
                        logger.debug(f"Failed pass: {idx} | {x}")

                    if avg_score > fail_pass_score[1]:
                        break

                if not any_chosen:
                    pass_data.append(best_data)


            temp_audio_path.unlink()

            final_aligned = list()

            def weighted_median(values_and_weights):
                valid = [(v, w) for v, w in values_and_weights if v is not None and w is not None]
                if not valid:
                    return None

                valid.sort(key=lambda x: x[0])

                total_weight = sum(w for v, w in valid)
                if total_weight <= 0:
                    values = [v for v, w in valid]
                    return values[len(values) // 2]

                half_weight = total_weight / 2.0
                cumulative_weight = 0.0

                for v, w in valid:
                    cumulative_weight += w
                    if cumulative_weight >= half_weight:
                        return v

                return valid[-1][0]

            for passes in zip(*pass_data):
                start_pairs = [(p.get("start"), p.get("score", 0)) for p in passes]
                end_pairs = [(p.get("end"), p.get("score", 0)) for p in passes]

                raw_start = weighted_median(start_pairs)
                raw_end = weighted_median(end_pairs)

                start = round(raw_start, 2) if raw_start is not None else None
                end = round(raw_end, 2) if raw_end is not None else None

                score_sum = max(0.0000001, sum(p.get("score", 0) for p in passes))
                score = round(score_sum / len(passes), 2)

                final_aligned.append(
                    LyricSegment(
                        passes[0]["line"],
                        start,
                        end,
                        score,
                        all(p["matched"] for p in passes)
                    )
                )

            for idx, segment in enumerate(final_aligned[:-1]):
                next_seg = final_aligned[idx + 1]

                if segment.end is not None and next_seg.start is not None:
                    if segment.end >= next_seg.start:
                        final_aligned[idx].end = final_aligned[idx + 1].start - 0.02
                    else:
                        pass

            for idx in range(1, len(final_aligned) - 1):
                last_seg = final_aligned[idx - 1]
                cur_seg = final_aligned[idx]
                next_seg = final_aligned[idx + 1]

                if (cur_seg.start is None and
                        cur_seg.end is None and
                        last_seg.end is not None and
                        next_seg.start is not None and
                        next_seg.start - last_seg.end < 15):
                    cur_seg.start = last_seg.end + 0.05
                    cur_seg.end = next_seg.start - 0.05

            rounded_aligned = [
                LyricSegment(
                    seg.line,
                    round(seg.start, 2) if seg.start else None,
                    round(seg.end, 2) if seg.end else None,
                    seg.score,
                    seg.matched
                )
                for seg in final_aligned]

            return rounded_aligned

        best_idx, audios, data, vad_settings, scores = run_test_pass()
        return run_full_pass(audios[best_idx],
                             extra_pass_data=[data[best_idx]],
                             use_vad=vad_settings[best_idx],
                             fail_pass_score=(
                                 max(scores[best_idx] - 0.05, 0.65),
                                 0.8)
                             )



class MorphologicalAnalyzer:
    def __init__(self):
        raise NotImplementedError

if __name__ == "__main__":
    fa = ForcedAlignment()
    # data = fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\aRDURmIYBZ4_vocal.wav"),
    #                       Path(r"D:\python\miraa-alternative\src\.temp\Mela! - Ryokuoushoku Shakai.json"))
    # data = fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\d6i4AtCxrDo_vocal.wav"),
    #                       read_json_file(Path(r"D:\python\miraa-alternative\src\.temp\Haikei Shounenyo - Hump Back.json")).get("lyrics_main"))
    data = fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\gt-v_YCkaMY_vocal.wav"),
                          read_json_file(Path(r"D:\python\miraa-alternative\src\.temp\Backlight - Ado.json")).get("lyrics_main"))
    # data = fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\v-WcMQbXbKY_vocal.wav"),
    #                       Path(r"D:\python\miraa-alternative\src\.temp\花になって - Be a flower - Ryokuoushoku Shakai.json"))
    # data = fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\qs4Q4cQxyU4_vocal.wav"),
    #                       Path(r"D:\python\miraa-alternative\src\.temp\Wherever you are - ONE OK ROCK.json"))
    # data = fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\1zwaZkOXXqw_vocal.wav"),
    #                       Path(r"D:\python\miraa-alternative\src\.temp\DADDY ! DADDY ! DO ! - Masayuki Suzuki.json"))
    # data = fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\phwvj0_XM4k_vocal.wav"),
    #                       Path(r"D:\python\miraa-alternative\src\.temp\JET - POLKADOT STINGRAY.json"))


    # fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\GQ3V50XoLOM_vocal.wav"),
    #                       Path(r"D:\python\miraa-alternative\src\.temp\ライラック - 美波.json"))
    # fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\QLBfxG0cenQ_vocal.wav"),
    #                       Path(r"D:\python\miraa-alternative\src\.temp\想い人 - Ryokuoushoku Shakai.json"))
    # fa.force_align_lyrics(Path(r"D:\python\miraa-alternative\src\.temp\vOLncha7MqM_vocal.wav"),
    #                       Path(r"D:\python\miraa-alternative\src\.temp\君のせい - the peggies.json"))

    parsed = [d.to_dict() for d in data]
    temp = Path(r"D:\python\miraa-alternative\src\.temp\temp.json")
    temp.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")


