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

    def _init_model(self, model_name: str = "vocal_full") -> None:
        _model = self._separator_objects.get(model_name)

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
