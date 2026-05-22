from pathlib import Path

class Analyzer:
    class DataMismatchError(Exception):
        pass

    DEFAULT_CONFIG = {
        "version": "1.0.0",
        "youtube_downloader": {
            "use_cookies": False
        },
        "skip_processes": {
            "download_song": False,
            "genius_metadata": False,
            "vocal_separation": False
        }
    }

    DEFAULT_ENV_VARS = [
        "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "YOUTUBE_COOKIE_PATH", "GENIUS_ACCESS_TOKEN"
    ]

    def __init__(self) -> None:
        """Initialize the analyzer."""
        import logger
        self._logger = logger.Logger()

        self._setup_main_directories()
        self._load_env_file()
        self._setup_config_file()

        self._dl = None

    # region Helper Functions
    def _setup_main_directories(self) -> None:
        """Sets up the main directories for the analyzer."""
        from pathlib import Path

        self._script_dir = Path(__file__).resolve().parent
        self._base_dir = self._script_dir.parents[0]

        folder = ["data", "config", "models", ".temp"]
        for path in folder:
            Path(self._base_dir / path).mkdir(parents=True, exist_ok=True)
        self._logger.debug("Main Directories created.")

        self._temp_dir = Path(self._base_dir / ".temp")
        self._config_file = Path(self._base_dir / "config/config.json")
        self._env_file = Path(self._base_dir / "config/.env")

    def _setup_config_file(self) -> None:
        """Sets up the config file for the analyzer. Writes default values if it doesn't exist."""
        import json

        if not self._config_file.exists():
            config_json = json.dumps(self.DEFAULT_CONFIG, indent=4)
            self._config_file.write_text(config_json)
            self._logger.debug("Created config file and set default values.")
        else:
            config_json = self._config_file.read_text()
            self._logger.debug("Config file exists, read config file")

        self._config_json = json.loads(config_json)

        self._logger.info(f"miraa-alternative Version: {self._config_json['version']}")

    def _update_json_config(self) -> None:
        from helper_funcs import read_json_file
        self._config_json = read_json_file(self._config_file)

    def _load_env_file(self) -> None:
        """
        Loads the environment variables from the .env file.
        Creates a new .env file if it doesn't exist.
        DOES NOT check if the file is filled
        """
        import os
        from dotenv import load_dotenv

        if self._env_file.exists():
            load_dotenv(dotenv_path=self._env_file)
            self._logger.debug("Loaded .env file.")
        else:
            self._logger.critical("No .env file found. Creating empty .env file. Do NOT reorder the variables")
            self._env_file.write_text("\n".join([f"{var}=" for var in self.DEFAULT_ENV_VARS]))
            raise FileNotFoundError(".env file not found, creating one. Please add your credentials to the .env file.")

        load_dotenv()
        self._env_data = dict([(var, os.getenv(var))for var in self.DEFAULT_ENV_VARS])

    @staticmethod
    def _str_to_base58(string: str) -> str:
        import base58
        return base58.b58encode(string.encode('utf-8')).decode('utf-8')

    @staticmethod
    def _base58_to_str(string: str) -> str:
        import base58
        return base58.b58decode(string).decode('utf-8')
    # endregion

    # region preprocessing
    def _init_downloader(self) -> None:
        if self._dl is None:
            import downloader
            import questionary as q
            import json
            from dotenv import set_key
            from helper_funcs import read_json_file, write_json_file

            if self._config_json["youtube_downloader"]["use_cookies"]:
                if self._env_data["YOUTUBE_COOKIE_PATH"] == '' or self._env_data["YOUTUBE_COOKIE_PATH"] is None:
                    _use_cookies = q.confirm("Do you want to use cookies?").ask()
                    if _use_cookies:
                        _cookie_path = q.path("Please enter the path to your cookies file (Netscape .txt file): ").ask()
                        self._env_data["YOUTUBE_COOKIE_PATH"] = _cookie_path
                        set_key(self._env_file, "YOUTUBE_COOKIE_PATH", _cookie_path, quote_mode="never")
                    else:
                        read_json_file(self._config_file)
                        write_json_file(self._config_file, False, ["youtube_downloader", "use_cookies"])
                        set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")
            else:
                if self._env_data["YOUTUBE_COOKIE_PATH"] != '':
                    set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")

            self._dl = downloader.Downloader(spotify_client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                                             spotify_client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"],
                                             youtube_cookie_path=self._env_data["YOUTUBE_COOKIE_PATH"])

    def query_song_spotify(self) -> None:
        """
        query a song from spotify and save it to a JSON file with all data needed
        """
        import json

        self._init_downloader()

        _data = self._dl.cli_search_song()
        _view_name = self._dl.get_title_artist(metadata=_data)
        _youtube_id = self._dl.youtube_query(query=_view_name)

        _json_data = json.dumps({"pre_processing": {"youtube_id": _youtube_id, "view_name": _view_name, "raw_metadata": _data}}, indent=4)
        _file_path = self._temp_dir / f"{_view_name}.json"

        _file_path.write_text(_json_data)
        self._logger.info(f"Saved song data: {_view_name} -> {_file_path}")

    def download_song(self, json_file: Path = None) -> None:
        """
        Downloads a song from YouTube using metadata present in .temp
        When no files are present, it will query spotify
        :param json_file: A path to a JSON file containing metadata, optional
        """
        from pathlib import Path
        from helper_funcs import questionary_select, write_json_file, read_json_file
        import asyncio

        def get_youtube_id_from_json(file_path: Path) -> str | None:
            if file_path.suffix == ".json":
                return str(read_json_file(file_path)["pre_processing"]["youtube_id"])
            return None

        async def _download(file_path: Path | str | None) -> None:
            if file_path is None:
                raise Exception("No file path provided")
            if type(file_path) is str:
                await asyncio.to_thread(self._dl.download_youtube_video, url=file_path)
            if type(file_path) is Path:
                await asyncio.to_thread(self._dl.download_youtube_video, url=get_youtube_id_from_json(file_path))

        _break_off = False

        if json_file is None:
            while True:
                if _break_off:
                    break

                _all_files = list(self._temp_dir.iterdir())
                _all_files_stem = [file.stem for file in _all_files]
                _available_json_files = [file for file in _all_files if file.suffix == ".json" and get_youtube_id_from_json(file) not in _all_files_stem]

                # if songs are available, ask user which one to download or download the only one present
                if _available_json_files:
                    # if only one song is available, download it
                    if len(_available_json_files) == 1:
                        target_id = get_youtube_id_from_json(_available_json_files[0])
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(_download(target_id))
                        except RuntimeError:
                            asyncio.run(_download(target_id))
                    # if multiple songs are available, ask user which one to download
                    elif len(_available_json_files) > 1:
                        _offset = 0

                        while True:
                            _all_files = list(self._temp_dir.iterdir())
                            _all_files_stem = [file.stem for file in _all_files]
                            _available_json_files = [file for file in _all_files
                                                     if file.suffix == ".json" and
                                                     get_youtube_id_from_json(file) not in _all_files_stem]

                            _file_list = [{"name": file.stem, "value": file} for file in _available_json_files]

                            _user_choice = questionary_select("Please choose the song:",
                                                              choose_data=_file_list,
                                                              enable_pages=True,
                                                              enable_all="Download All",
                                                              enable_exit="Exit",
                                                              batch_data=True)

                            if _user_choice == "__all__":
                                _target_ids = [get_youtube_id_from_json(file) for file in _available_json_files]
                                _tasks = [_download(y_id) for y_id in _target_ids]

                                async def run_batch():
                                    await asyncio.gather(*_tasks)

                                try:
                                    loop = asyncio.get_running_loop()
                                    loop.create_task(run_batch())
                                except RuntimeError:
                                    asyncio.run(run_batch())

                                for file in _available_json_files:
                                    write_json_file(file, True, ["pre_processing", "downloaded"])
                                _break_off = True
                                break
                            else:
                                _file_data = read_json_file(_user_choice)
                                _tasks = [_download(_file_data["pre_processing"]["youtube_id"])]

                                async def run_batch():
                                    await asyncio.gather(*_tasks)

                                try:
                                    loop = asyncio.get_running_loop()
                                    loop.create_task(run_batch())
                                except RuntimeError:
                                    asyncio.run(run_batch())
                # if no songs are available, query spotify
                else:
                    self.query_song_spotify()
        else:
            target_id = get_youtube_id_from_json(json_file)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_download(target_id))
            except RuntimeError:
                asyncio.run(_download(target_id))
    # endregion

    def process_song(self) -> None:
        from helper_funcs import questionary_select, questionary_checkbox, write_json_file, read_json_file
        from questionary import Choice, confirm
        import gc

        self._init_downloader()

        while True:
            _all_files = [file for file in self._temp_dir.iterdir() if file.suffix == ".json"]
            _all_files_stem = [file.stem for file in _all_files]

            _song_choice_list = [{"name": file.stem, "value": file} for file in _all_files]

            _user_song_choice = questionary_select("Please choose the song:", choose_data=_song_choice_list, extra_navigation_options=[{"name": "Download New", "value": "__new__"}])
            if _user_song_choice == "__new__":
                self.query_song_spotify()
            else:
                break

        _song_data = read_json_file(_user_song_choice)

        def update_song_data() -> None:
            nonlocal _song_data
            _song_data = read_json_file(_user_song_choice)

        # region all processes, returns True if already done
        def _download() -> bool:
            if _song_data.get("pre_processing", {}).get("downloaded", False):
                # checks if the audio file is present in the .temp dir, if not handle appropriately
                if _song_data["pre_processing"].get("youtube_id", None) not in [file.stem for file in self._temp_dir.iterdir() if file.suffix == ".wav"]:
                    self._logger.warning("Data file says audio has been downloaded, but it isn't present in .temp directory")
                    self._logger.warning("Please do not rename, convert or alter files in .temp to prevent further errors")
                    self._logger.warning("Please clear all files in .temp directory to ensure proper functionality")
                    if confirm("Do you want to retry?").ask():
                        write_json_file(_user_song_choice, False, ["pre_processing", "downloaded"])
                        update_song_data()
                        _download()
                    else:
                        raise self.DataMismatchError
                self._logger.debug(f"Song already downloaded, skipping")
                return True
            else:
                self._logger.debug(f"Song not downloaded, downloading it now.")
                self.download_song(_user_song_choice)
                write_json_file(_user_song_choice, True, ["pre_processing", "downloaded"])
                return False

        def _genius_pull() -> bool:
            from geniusextractor import GeniusExtractor

            if _song_data.get("genius_data", None) is not None:
                self._logger.debug(f"Genius data already present, skipping")
                return True
            else:
                _genius_data = GeniusExtractor(self._env_data["GENIUS_ACCESS_TOKEN"]).return_metadata(
                    title=_song_data["pre_processing"]["raw_metadata"]["name"],
                    artist=_song_data["pre_processing"]["raw_metadata"]["artists"][0]["name"]
                )
                write_json_file(_user_song_choice, _genius_data, ["genius_data"])
                return False

        def _vocal_sep() -> bool:
            # TODO add vocal sep model chooser
            if _song_data.get("vocal_separation", {}).get("separated", False) is True:
                # TODO add vocal sep audio file check

                self._logger.debug(f"Vocal separation already done, skipping")
                return True
            else:
                from processing import VocalSeparation
                _vs = VocalSeparation()
                _vs.separate_vocal(f"../.temp/{_song_data["pre_processing"]["youtube_id"]}.wav")
                write_json_file(_user_song_choice, True, ["vocal_separation", "separated"])

                del _vs
                gc.collect()
                return False
        # endregion

        # skip processes
        _skip_options = self._config_json.get("skip_processes")

        # choice list for skip processes, update when adding new processes
        _choice_list = [Choice("Download song",
                               value="download_song",
                               checked=_skip_options['download_song'],
                               disabled="Song already downloaded" if _song_data.get("pre_processing", {}).get("downloaded") else None),
                        Choice("Get Genius metadata",
                               value="genius_metadata",
                               checked=_skip_options['genius_metadata'],
                               disabled="Data already gathered" if _song_data.get("genius_data") else None),
                        Choice("Separate audio into stems",
                               value="vocal_separation",
                               checked=_skip_options['vocal_separation'],
                               disabled="Stems already separated" if _song_data.get("vocal_separation", {}).get("separated") else None)]

        _skip_processes = questionary_checkbox("Please choose what options to skip", choice_data=_choice_list)
        if _skip_processes != [k for k in _skip_options if _skip_options[k]]:
            _write_skip_to_json = confirm("Do you want to set this to default?").ask()
        else:
            _write_skip_to_json = False

        for key in _skip_options:
            if key in _skip_processes:
                _skip_options[key] = True
            else:
                _skip_options[key] = False

        if _write_skip_to_json:
            write_json_file(self._config_file, _skip_options, ["skip_processes"])

        self._update_json_config()

        # main loop for processes
        while True:
            if not self._config_json["skip_processes"]["download_song"]:
                _download()
            if not self._config_json["skip_processes"]["genius_metadata"]:
                _genius_pull()
            if not self._config_json["skip_processes"]["vocal_separation"]:
                if not _song_data["pre_processing"].get("downloaded", False):
                    self._logger.info("Audio cannot be separated as it hasn't been downloaded")
                    if confirm("Would you like to download first?").ask():
                        _download()
                    else:
                        break
                _vocal_sep()

            break


def main() -> None:
    ana = Analyzer()
    # ana._download("https://open.spotify.com/track/0UFmgncRMHavVzYxtpF0IZ?si=1c86deb161b24778")
    # ana._download("https://open.spotify.com/track/0VPkaJMRQIhYWXiE1LqaCK?si=a867127aa85a4769")
    # ana.download_song()
    # ana.query_song_spotify()
    ana.process_song()


if __name__ == "__main__":
    main()