from typing import Any

# region vocal sep
class VocalSeparation:
    def __init__(self) -> None:
        """
        Separator object:
        vocal_full: A rawer vocal stem with noise artifacts but the most clear articulation
        vocal_clean: A more processed vocal stem with fewer noise artifacts but more muffled in certain areas
        instrumental_full: A model best for getting a clear instrumental stem, not ideal vocals
        instrumental_low_resource: A good low-resource model, decent quality for both stems but with some slight bleeding
        """

        from audio_separator.separator import Separator
        from pathlib import Path

        self._script_dir = Path(__file__).resolve().parent
        self._base_dir = self._script_dir.parents[0]

        self._output_dir = f'{self._base_dir / ".temp"}'
        self._model_file_dir = f'{self._base_dir / "models/audioseparator"}'

        # TODO add normal models for more stuff yesyes
        self._separator_objects = {"vocal_full": Separator(output_dir=str(self._output_dir),
                                                           model_file_dir=str(self._model_file_dir),
                                                           ensemble_preset='vocal_full'),
                                   "vocal_clean": Separator(output_dir=str(self._output_dir),
                                                           model_file_dir=str(self._model_file_dir),
                                                           ensemble_preset='vocal_clean'),
                                   "instrumental_full": Separator(output_dir=str(self._output_dir),
                                                           model_file_dir=str(self._model_file_dir),
                                                           ensemble_preset='instrumental_full'),
                                   "instrumental_low_resource": Separator(output_dir=str(self._output_dir),
                                                           model_file_dir=str(self._model_file_dir),
                                                           ensemble_preset='instrumental_low_resource')
                                   }
    @property
    def separator_objects(self) -> list[str]:
        return list(self._separator_objects)

    def _init_model(self, model_name: str = "vocal_full") -> None:
        _model = self._separator_objects.get(model_name, None)

        if _model is None:
            raise Exception(f"Model {model_name} not found")
        else:
            self._separator_objects[model_name].load_model()

    def separate_vocal(self, audio_path: str, model: str = "vocal_full") -> None:
        from pathlib import Path

        self._init_model(model)
        _win_audio_path = Path(audio_path)

        _output_files = self._separator_objects[model].separate(audio_path)
        print(_output_files)

        _output_files = [Path(f) for f in _output_files]

        def rename_file(file_path: Path, name: str) -> None:
            file_path.rename(f"{str(self._output_dir)}/{_win_audio_path.stem}_{name}.wav")

        # different models output differently, if flipped recheck this
        match model:
            case "vocal_full":
                rename_file(_output_files[0], "inst")
                rename_file(_output_files[1], "vocal")
            case "vocal_clean":
                rename_file(_output_files[0], "inst")
                rename_file(_output_files[1], "vocal")
            case "instrumental_full":
                rename_file(_output_files[0], "vocal")
                rename_file(_output_files[1], "inst")
            case "instrumental_low_resource":
                rename_file(_output_files[0], "vocal")
                rename_file(_output_files[1], "inst")
# endregion

# region japanese morphological analyzer
def _tag_data(text_data: str, translation_dict: dict[str, str] = None) -> dict[str, Any] | None:
    import nagisa
    if text_data is None or text_data == "":
        return None
    if translation_dict is None:
        raise ValueError("Please put a translation dict in kwargs")
    _data = nagisa.tagging(text_data)
    _en_pos = [translation_dict[pos] for pos in _data.postags]
    return {"words": _data.words,
            "pos": _data.postags,
            "en_pos": _en_pos,
            "text": _data.text}

class JPSplitTagger:
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
        pass

    # TODO maybe use SudachiPy or fugashi for backup?
    # TODO add fallback when lyrics are romanized

    def tag(self, text: str, split_newline: bool = True) -> dict[str, Any] | list[dict[str, Any] | None] | None:
        """
        Tags a string into their parts (including pos)
        :param text: String to process
        :param split_newline: Whether to split the text into lines
        :return: A dict containing the words, their parts, and the text itself
        """
        from functools import partial

        if split_newline:
            from concurrent.futures import ProcessPoolExecutor
            _split_text = text.split("\n")

            _fixed_tagger = partial(_tag_data, translation_dict=self.japanese_pos_translation)

            with ProcessPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(_fixed_tagger, _split_text))

            return results
        else:
            return _tag_data(text, self.japanese_pos_translation)