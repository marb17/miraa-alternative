class Analyzer:
    DEFAULT_CONFIG = {
        "version": "1.0.0",
        "youtube_downloader": {
            "use_cookies": False
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

        self._base_dir = Path("../")
        folder = ["data", "config", "models", ".temp"]
        for path in folder:
            Path(self._base_dir / path).mkdir(parents=True, exist_ok=True)
        self._logger.debug("Main Directories created.")

        self._temp_dir = Path(self._base_dir / ".temp")

    def _setup_config_file(self) -> None:
        """Sets up the config file for the analyzer. Writes default values if it doesn't exist."""
        from pathlib import Path
        import json

        self._config_file = Path(self._base_dir / "config/config.json")
        if not self._config_file.exists():
            config_json = json.dumps(self.DEFAULT_CONFIG, indent=4)
            self._config_file.write_text(config_json)
            self._logger.debug("Created config file and set default values.")
        else:
            config_json = self._config_file.read_text()
            self._logger.debug("Config file exists, read config file")

        self._config_json = json.loads(config_json)

        self._logger.info(f"miraa-alternative Version: {self._config_json['version']}")

    def _load_env_file(self) -> None:
        """
        Loads the environment variables from the .env file.
        Creates a new .env file if it doesn't exist.
        DOES NOT check if the file is filled
        """
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        self._env_file = Path(self._base_dir / "config/.env")
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

    def _init_downloader(self) -> None:
        if self._dl is None:
            import downloader
            import questionary as q
            import json
            from dotenv import set_key

            if self._config_json["youtube_downloader"]["use_cookies"]:
                if self._env_data["YOUTUBE_COOKIE_PATH"] == '' or self._env_data["YOUTUBE_COOKIE_PATH"] is None:
                    _use_cookies = q.confirm("Do you want to use cookies?").ask()
                    if _use_cookies:
                        _cookie_path = q.path("Please enter the path to your cookies file (Netscape .txt file): ").ask()
                        self._env_data["YOUTUBE_COOKIE_PATH"] = _cookie_path
                        set_key(self._env_file, "YOUTUBE_COOKIE_PATH", _cookie_path, quote_mode="never")
                    else:
                        config_json = json.loads(self._config_file.read_text())
                        config_json["youtube_downloader"]["use_cookies"] = False
                        self._config_file.write_text(json.dumps(config_json, indent=4))
                        set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")
            else:
                if self._env_data["YOUTUBE_COOKIE_PATH"] != '':
                    set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")

            self._dl = downloader.Downloader(spotify_client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                                             spotify_client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"],
                                             youtube_cookie_path=self._env_data["YOUTUBE_COOKIE_PATH"])

    def query_song_spotify(self) -> None:
        """
        query a song from spotify and save it to a json file with all data needed
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

    def download_song(self) -> None:
        """
        Downloads a song from YouTube using metadata present in .temp
        When no files are present, it will query spotify
        :return:
        """
        from pathlib import Path
        from itertools import batched
        import questionary as q
        import json
        import asyncio

        def get_youtube_id_from_json(file_path: Path) -> str:
            if file_path.suffix == ".json":
                return str(json.loads(file_path.read_text())["pre_processing"]["youtube_id"])
            return None

        async def _download(file_path: Path | str) -> None:
            if type(file_path) is Path:
                await asyncio.to_thread(self._dl.download_youtube_video, url=get_youtube_id_from_json(file_path))
            if type(file_path) is str:
                await asyncio.to_thread(self._dl.download_youtube_video, url=file_path)

        _break_off = False

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
                        _batched_files = list(batched(_available_json_files, 10))

                        _file_list = [{"name": file.stem, "value": file} for file in _batched_files[_offset]]
                        _file_list.append(q.Separator())
                        _file_list.append({"name": "Next ->", "value": "__next__"})
                        _file_list.append({"name": "Previous <-", "value": "__prev__"})
                        _file_list.append({"name": "Download All", "value": "__all__"})
                        _file_list.append({"name": "Exit", "value": "__exit__"})

                        _user_choice = q.select("Please choose the song:", choices=_file_list).ask()

                        if _user_choice == "__next__":
                            if _offset + 1 >= len(_batched_files) :
                                pass
                            else:
                                _offset += 1
                        elif _user_choice == "__prev__":
                            if _offset > 0:
                                _offset -= 1
                        elif _user_choice == "__all__":
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
                                _data_json = json.loads(file.read_text())
                                _data_json["pre_processing"]["downloaded"] = True
                                file.write_text(json.dumps(_data_json, indent=4))

                            _break_off = True
                            break
                        elif _user_choice == "__exit__":
                            _break_off = True
                            break
                        else:
                            _file_data = json.loads(_user_choice.read_text())
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


def main() -> None:
    ana = Analyzer()
    ana._init_downloader()
    # ana._download("https://open.spotify.com/track/0UFmgncRMHavVzYxtpF0IZ?si=1c86deb161b24778")
    # ana._download("https://open.spotify.com/track/0VPkaJMRQIhYWXiE1LqaCK?si=a867127aa85a4769")
    ana.download_song()
    # ana.query_song_spotify()


if __name__ == "__main__":
    main()