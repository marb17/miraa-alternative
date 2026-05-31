# STANDARD LIBRARIES
import time
import gc
import shutil
from pathlib import Path
from typing import Any
from functools import partial
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# HELPER LIBRARIES
from backend_new.utils.helper_funcs import read_json_file

# PYPI LIBRARIES
from sudachipy.morpheme import Morpheme
from sudachipy import dictionary, tokenizer

import nagisa

from backend_new.utils.logger import Logger
logger = Logger(__name__)

# region vocal sep
class VocalSeparation:
    # TODO add normal models for more stuff yesyes
    PRESETS = {
        "vocal_full": ("vocal_full", "ensemble"),
        "vocal_clean": ("vocal_clean", "ensemble"),
        "instrumental_full": ("instrumental_full", "ensemble"),
        "instrumental_low_resource": ("instrumental_low_resource", "ensemble"),
    }

    def __init__(self, model_name: str = "vocal_full") -> None:
        """
        Separator object:
        vocal_full: A rawer vocal stem with noise artifacts but the most clear articulation
        vocal_clean: A more processed vocal stem with fewer noise artifacts but more muffled in certain areas
        instrumental_full: A model best for getting a clear instrumental stem, not ideal vocals
        instrumental_low_resource: A good low-resource model, decent quality for both stems but with some slight bleeding
        """
        from audio_separator.separator import Separator

        current_dir = Path(__file__).resolve().parent
        while current_dir.name != "src" and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        self._base_dir = current_dir

        self._output_dir = f'{self._base_dir / ".temp"}'
        self._model_file_dir = f'{self._base_dir / "models/audioseparator"}'

        # select model and list available models
        self._available_models = [key for key in self.PRESETS]
        self._model_name = model_name

        # check if model available
        model = self.PRESETS.get(model_name, None)
        if model is None:
            raise Exception(f"Model {model_name} not found, choose from: {self._available_models}")
        else:
            self._selected_model = None

            if self.PRESETS[self._model_name][1] == "ensemble":
                self._selected_model = Separator(output_dir=str(self._output_dir),
                                                 model_file_dir=str(self._model_file_dir),
                                                 ensemble_preset=self._model_name)

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
        self._selected_model.load_model()

    def separate_vocal(self, audio_path: str) -> None:
        self._init_model()

        win_audio_path = Path(audio_path)

        now = time.time()
        output_files = self._selected_model.separate(audio_path)
        logger.info(f"Took {(time.time() - now):.2f} seconds to separate stems")

        output_files = [Path(f) for f in output_files]

        def rename_file(file_path: Path, name: str) -> None:
            file_path.rename(f"{str(self._output_dir)}/{win_audio_path.stem}_{name}.wav")

        # different models output differently, if flipped recheck this
        match self._model_name:
            case "vocal_full":
                rename_file(output_files[0], "inst")
                rename_file(output_files[1], "vocal")
            case "vocal_clean":
                rename_file(output_files[0], "inst")
                rename_file(output_files[1], "vocal")
            case "instrumental_full":
                rename_file(output_files[0], "vocal")
                rename_file(output_files[1], "inst")
            case "instrumental_low_resource":
                rename_file(output_files[0], "vocal")
                rename_file(output_files[1], "inst")
# endregion

# region dictionaries
class JPDictionary:
    def __init__(self) -> None:
        from backend_new.utils import logger
        logger = logger.Logger()

        current_dir = Path(__file__).resolve().parent
        while current_dir.name != "src" and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        self._base_dir = current_dir
        self._dict_dir = self._base_dir / "dicts"

        self._available_dicts: list[Path] = []
        # TODO change any to something meaningful
        self._lookup_table: Any = None

        # prepare all dicts
        self._extract_zip_files()
        self._read_all_available_dicts()

    def _extract_zip_files(self):
        all_zip_files = [file for file in self._dict_dir.iterdir() if file.suffix == ".zip"]
        all_zip_files_stem = [file.stem for file in all_zip_files]

        if all_zip_files:
            logger.debug("New .zip files detected, extracting now")
            for file_path, stem_name in zip(all_zip_files, all_zip_files_stem):
                dir_path = self._dict_dir / f"{stem_name}"
                dir_path.mkdir(parents=True, exist_ok=True)

                logger.debug(f"Extracting: {file_path}")
                try:
                    shutil.unpack_archive(file_path, dir_path)
                    logger.debug(f"Completed extracting: {file_path}, deleting old .zip files")
                    file_path.unlink()
                except:
                    raise Exception("File unsuccessfully extracted, please re-run and check for any unintended changes in 'dict' directory")
            logger.debug("All .zip files extracted successfully")
        else:
            logger.debug("No new .zip files detected, skipping")

    def _read_all_available_dicts(self) -> None:
        all_dicts = [path for path in self._dict_dir.iterdir() if path.is_dir()]
        self._available_dicts = all_dicts

    def _read_single_dict(self, dict_path: Path) -> dict:
        all_term_bank_files = list(dict_path.rglob("term_bank_*.json"))

        #! temporary test, have to learn the format of the data
        single = all_term_bank_files[0]

        file_data = read_json_file(single)
        print(file_data[100])

    def _initialize_lookup(self):
        # TODO allow user to choose what dicts to use cuz yeah would be cool and accept the always ask so it doesnt keep asking
        self._read_single_dict(self._available_dicts[0])


# endregion

# region japanese morphological analyzer
class TaggedData:
    def __init__(self, words: list[str], pos: list[str], en_pos: list[str], text: str):
        self._words = words
        self._pos = pos
        self._en_pos = en_pos
        self._text = text

        self._data_dict = {"words": words,
                           "pos": pos,
                           "en_pos": en_pos,
                           "text": text}

    def __str__(self) -> str:
        return " | ".join(self.words)

    @property
    def data(self) -> dict[str, Any]: return self._data_dict
    @property
    def words(self) -> list[str]: return self._words
    @property
    def pos(self) -> list[str]: return self._pos
    @property
    def en_pos(self) -> list[str]: return self._en_pos
    @property
    def text(self) -> str: return self._text


class MorphemeData:
    def __init__(self, morpheme: Morpheme) -> None:
        self._surface = morpheme.surface()
        self._dictionary_form = morpheme.dictionary_form()
        self._normalized_form = morpheme.normalized_form()
        self._reading = morpheme.reading_form()
        self._pos = morpheme.part_of_speech()

        self._data_dict = {
            "surface": self._surface,
            "dictionary_form": self._dictionary_form,
            "normalized_form": self._normalized_form,
            "reading": self._reading,
            "pos": self._pos
        }

    def __str__(self) -> str:
        return self.dictionary_form

    def __repr__(self) -> str:
        return "'" + self.dictionary_form + "'"

    @property
    def data(self) -> dict[str, Any]: return self._data_dict
    @property
    def surface(self) -> str: return self._surface
    @property
    def dictionary_form(self) -> str: return self._dictionary_form
    @property
    def normalized_form(self) -> str: return self._normalized_form
    @property
    def reading(self) -> str: return self._reading
    @property
    def pos(self) -> tuple[str, ...]: return self._pos


def tag_data(text_data: str, translation_dict: dict[str, Any]) -> TaggedData | None:
    if text_data is None or text_data == "":
        return None
    if translation_dict is None:
        raise Exception("Please fill out japanese_pos_translation")

    data = nagisa.tagging(text_data)
    en_pos = [translation_dict[pos] for pos in data.postags]
    return TaggedData(data.words, data.postags, en_pos, data.text)


class JPAnalyzer:
    japanese_pos_translation = {
        "oov": "out of vocabulary",
        "補助記号": "auxiliary sign / punctuation",
        "名詞": "noun",
        "空白": "whitespace",
        "助詞": "particle",
        "接尾辞": "suffix",
        "動詞": "verb",
        "連体詞": "adnominal / pre-noun adjectival",
        "助動詞": "auxiliary verb",
        "形容詞": "i-adjective / adjective",
        "感動詞": "interjection",
        "接頭辞": "prefix",
        "記号": "symbol",
        "接続詞": "conjunction",
        "副詞": "adverb",
        "代名詞": "pronoun",
        "形状詞": "na-adjective / adjectival noun",
        "web誤脱": "web typo / omission / error",
        "URL": "URL",
        "英単語": "English word",
        "漢文": "Kanbun / classical Chinese text",
        "未知語": "unknown word",
        "言いよどみ": "filler / hesitation word",
        "ローマ字文": "Romanized text / Romaji sentence"
    }

    def __init__(self) -> None:
        self._fixed_tagger = partial(tag_data, translation_dict=self.japanese_pos_translation)
        self._tokenizer_obj = dictionary.Dictionary(dict="full").create()

    # TODO use SudachiPy for dict look up
    # TODO add fallback when lyrics are romanized

    def _tag(self, data: list[str]) -> list[TaggedData | None]:
        """
        Tags a string into their parts (including pos)
        :param data: data to process
        :return: A dict containing the words, their parts, and the text itself
        """
        with ProcessPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(self._fixed_tagger, data))

        return results

    def _morpheme(self, data: list[TaggedData | None]) -> list[list[MorphemeData] | None]:
        """
        Gets dictionary data from tagged data
        :param data:
        :return:
        """
        def morpheme_pull(str_data: list[str] | None, tokenizer_object, split_mode) -> list[Morpheme] | None:
            if str_data is None:
                return None

            return [tokenizer_object.tokenize(word, split_mode)[0] for word in str_data]

        mode = tokenizer.Tokenizer.SplitMode.C
        fixed_morpheme_pull = partial(morpheme_pull, tokenizer_object=self._tokenizer_obj, split_mode=mode)

        formatted_data = []
        for d in data:
            if d is None:
                formatted_data.append(None)
            else:
                formatted_data.append(d.words)

        with ThreadPoolExecutor(max_workers=15) as executor:
            results = list(executor.map(fixed_morpheme_pull, formatted_data))

        final_results = []
        for res in results:
            if res is None:
                final_results.append(None)
                continue

            final_results.append([MorphemeData(word) for word in res])

        return final_results

    def process(self, text: str, split_newline: bool = True) -> dict[str, Any] | list[dict[str, Any] | None] | None:
        if split_newline:
            data_list = text.split("\n")
        else:
            data_list = [text]

        tag_data = self._tag(data_list)
        morpheme_data = self._morpheme(tag_data)

        # TODO add -/jamdict/- use yomitan dict

# endregion

if __name__ == "__main__":
    # analyzer = JPAnalyzer()
    # lyric = "[7!!(\u30bb\u30d6\u30f3\u30a6\u30c3\u30d7\u30b9)\u300c\u30aa\u30ec\u30f3\u30b8\u300d\u6b4c\u8a5e]\n\n[Verse 1]\n\u5c0f\u3055\u306a\u80a9\u3092\n\u4e26\u3079\u3066\u6b69\u3044\u305f\n\u4f55\u3067\u3082\u306a\u3044\u4e8b\u3067\u7b11\u3044\u5408\u3044\n\u540c\u3058\u5922\u3092\u898b\u3064\u3081\u3066\u3044\u305f\n\u8033\u3092\u6f84\u307e\u305b\u3070\n\u4eca\u3067\u3082\u805e\u3053\u3048\u308b\n\u541b\u306e\u58f0 \u30aa\u30ec\u30f3\u30b8\u8272\u306b\n\u67d3\u307e\u308b\u8857\u306e\u4e2d\n\n[Pre-Chorus]\n\u541b\u304c\u3044\u306a\u3044\u3068\u672c\u5f53\u306b\u9000\u5c48\u3060\u306d\n\u5bc2\u3057\u3044\u3068\u8a00\u3048\u3070\u7b11\u308f\u308c\u3066\u3057\u307e\u3046\u3051\u3069\n\u6b8b\u3055\u308c\u305f\u3082\u306e \u4f55\u5ea6\u3082\u78ba\u304b\u3081\u308b\u3088\n\u6d88\u3048\u308b\u3053\u3068\u306a\u304f\u8f1d\u3044\u3066\u3044\u308b\n\n[Chorus]\n\u96e8\u4e0a\u304c\u308a\u306e\u7a7a\u306e\u3088\u3046\u306a\n\u5fc3\u304c\u6674\u308c\u308b\u3088\u3046\u306a\n\u541b\u306e\u7b11\u9854\u3092\u61b6\u3048\u3066\u3044\u308b\n\u601d\u3044\u51fa\u3057\u3066\u7b11\u9854\u306b\u306a\u308b\n\u304d\u3063\u3068\u4e8c\u4eba\u306f\u3042\u306e\u65e5\u306e\u307e\u307e\n\u7121\u90aa\u6c17\u306a\u5b50\u4f9b\u306e\u307e\u307e\n\u5de1\u308b\u5b63\u7bc0\u3092\u99c6\u3051\u629c\u3051\u3066\u3044\u304f\n\u305d\u308c\u305e\u308c\u306e\u660e\u65e5\u3092\u898b\u3066\n\n[Verse 2]\n\u4e00\u4eba\u306b\u306a\u308c\u3070\n\u4e0d\u5b89\u306b\u306a\u308b\u3068\n\u7720\u308a\u305f\u304f\u306a\u3044\u591c\u306f\n\u8a71\u3057\u7d9a\u3051\u3066\u3044\u305f\n\n[Pre-Chorus]\n\u541b\u306f\u3053\u308c\u304b\u3089\u4f55\u3092\u898b\u3066\u3044\u304f\u3093\u3060\u308d\u3046\n\u79c1\u306f\u3053\u3053\u3067\u4f55\u3092\u898b\u3066\u3044\u304f\u306e\u3060\u308d\u3046\n\u6c88\u3080\u5915\u713c\u3051 \u30aa\u30ec\u30f3\u30b8\u306b\u67d3\u307e\u308b\u8857\u306b\n\u305d\u3063\u3068\u6d99\u3092\u9810\u3051\u3066\u307f\u308b\n\n[Chorus]\n\u4f55\u5104\u3082\u306e\u5149\u306e\u4e2d\n\u751f\u307e\u308c\u305f\u4e00\u3064\u306e\u611b\n\u5909\u308f\u3089\u306a\u304f\u3066\u3082\u5909\u308f\u3063\u3066\u3057\u307e\u3063\u3066\u3082\n\u541b\u306f\u541b\u3060\u3088 \u5fc3\u914d\u7121\u3044\u3088\n\u3044\u3064\u304b\u4e8c\u4eba\u304c\u5927\u4eba\u306b\u306a\u3063\u3066\n\u7d20\u6575\u306a\u4eba\u306b\u51fa\u4f1a\u3063\u3066\n\u304b\u3051\u304c\u3048\u306e\u306a\u3044\u5bb6\u65cf\u3092\u9023\u308c\u3066\n\u3053\u306e\u5834\u6240\u3067\u9022\u3048\u308b\u3068\u3044\u3044\u306a\n\n[Instrumental Break]\n\n[Chorus]\n\u96e8\u4e0a\u304c\u308a\u306e\u7a7a\u306e\u3088\u3046\u306a\n\u5fc3\u304c\u6674\u308c\u308b\u3088\u3046\u306a\n\u541b\u306e\u7b11\u9854\u3092\u61b6\u3048\u3066\u3044\u308b\n\u601d\u3044\u51fa\u3057\u3066\u7b11\u9854\u306b\u306a\u308b\n\u4f55\u5104\u3082\u306e\u5149\u306e\u4e2d\n\u751f\u307e\u308c\u305f\u4e00\u3064\u306e\u611b\n\u5de1\u308b\u5b63\u7bc0\u3092\u99c6\u3051\u629c\u3051\u3066\u3044\u304f\n\u305d\u308c\u305e\u308c\u306e\u660e\u65e5\u3092\u898b\u3066\n\n[Outro]\n\u305d\u308c\u305e\u308c\u306e\u5922\u3092\u9078\u3093\u3067"
    #
    # analyzer.process(lyric)

    jpdict = JPDictionary()
    jpdict._initialize_lookup()