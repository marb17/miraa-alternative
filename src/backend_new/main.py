from pathlib import Path
from backend_new.utils.logger import Logger


class Analyzer:
    # region default config
    DEFAULT_CONFIG = {
        "version": "1.0.0",
        "spotify_downloader": {
            "output_format": {
                "duration": True,
                "album": True,
                "popularity": True
            }
        },
        "youtube_downloader": {
            "use_cookies": False
        },
        "skip_processes": {
            "download_song": False,
            "genius_metadata": False,
            "vocal_separation": False,
            "split_and_tag": False,
            "translate_lyrics" : False
        },
        "jp_dicts": {
            "always_ask": False,
            "dicts_to_use": {}
        }
    }

    DEFAULT_ENV_VARS = [
        "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "YOUTUBE_COOKIE_PATH", "GENIUS_ACCESS_TOKEN"
    ]

    DEFAULT_DICTS_MESSAGE = """# Please download these recommended dictionaries:

- [JA-EN] **jitendex-yomitan**
  - This is the main structural dictionary, providing most of the comprehensive English definitions
- [JA-JA Names] **JMnedict**
  - Contains real-world words
    - Names
    - Places
    - Pop-Culture Titles
    - etc.
- [JA-JA Encyclopedia] **PixivLight**
  - Contains more modern / slang vocabularies
  - Catches internet memes
  - Vocaloid tracking terms
  - Modern abbreviations
  - Comtemporary subculture jargon
- [JA-JA Onomatopoeia] **擬音語・擬態語辞典**
  - Contains mimetic and sound-effect words (onomatopoeia)
    - e.g. gira-gira
- [JA-JA Yoji] **四字熟語の百科事典**
  - Dedicated to four-character idiomatic compounds
  - Often appears in dramatic or poetic song hooks
- [JA-JA] **ことわざ・慣用句の百科事典**
  - Handles traditional proverbs and idiomatic expressions
  - Can possibly provide symbolic meaning behind a phrase instead of a literal translation
- [JA-JA] **大辞林 第四版**
  - One of the best modern dictionaries for breaking down:
    - Compound verbs
    - Subtle semantic shifts
    - Artistic nuances
    - etc.
            
# Sources:
- https://github.com/MarvNC/yomitan-dictionaries

# How to install
- To install these dictionaries, please download the dictionaries and place them in the "dicts" directory
- The app will automatically extract the .zip files if not yet done and automatically detect each dictionary each run
    """
    # endregion

    def __init__(self) -> None:
        """Initialize the analyzer."""
        from backend_new.utils import logger
        self._logger = logger.Logger()

        self._setup_main_directories()
        self._load_env_file()
        self._setup_config_file()

        self._dl = None
        self._translator = None

    # region error messages
    class DataMismatchError(Exception):
        def __init__(self, logger: Logger, message: str = 'Files do not match the data in .temp directory') -> None:
            self.logger = logger
            self.message = message

            self.data_mismatch_error()

            super().__init__(self.message)

        def data_mismatch_error(self):
            self.logger.warning(self.message)
            self.logger.warning("Please do not rename, convert or alter files in .temp to prevent further errors")
            self.logger.warning("Please clear all files in .temp directory to ensure proper functionality")
    # endregion

    # region Helper Functions
    def _setup_main_directories(self) -> None:
        """Sets up the main directories for the analyzer."""
        from pathlib import Path

        current_dir = Path(__file__).resolve().parent
        while current_dir.name != "src" and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        self._base_dir = current_dir

        folder = ["data", "config", "models", ".temp", "dicts"]
        for path in folder:
            Path(self._base_dir / path).mkdir(parents=True, exist_ok=True)
        self._logger.debug("Main Directories created.")

        self._temp_dir = Path(self._base_dir / ".temp")
        self._config_file = Path(self._base_dir / "config/config.json")
        self._env_file = Path(self._base_dir / "config/.env")

        self._create_misc_files()

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
        """
        Updates the config file with the new values.
        """
        from backend_new.utils.helper_funcs import read_json_file
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

    def _create_misc_files(self) -> None:
        # dicts directory
        dicts_dir = Path(self._base_dir / "dicts")
        dicts_file = dicts_dir / "readme.md"
        if not dicts_file.exists():
            dicts_file.write_text(self.DEFAULT_DICTS_MESSAGE, encoding="utf-8")
        else:
            pass
    # endregion

    # region preprocessing
    def _init_downloader(self) -> None:
        """
        Initializes the downloader for spotify and YouTube
        """
        if self._dl is None:
            from backend_new.extractors import downloader
            import questionary as q
            import json
            from dotenv import set_key
            from backend_new.utils.helper_funcs import read_json_file, write_json_file

            if self._config_json["youtube_downloader"]["use_cookies"]:
                if self._env_data["YOUTUBE_COOKIE_PATH"] == '' or self._env_data["YOUTUBE_COOKIE_PATH"] is None:
                    use_cookies = q.confirm("Do you want to use cookies?").ask()
                    if use_cookies:
                        cookie_path = q.path("Please enter the path to your cookies file (Netscape .txt file): ").ask()
                        self._env_data["YOUTUBE_COOKIE_PATH"] = cookie_path
                        set_key(self._env_file, "YOUTUBE_COOKIE_PATH", cookie_path, quote_mode="never")
                    else:
                        read_json_file(self._config_file)
                        write_json_file(self._config_file, False, ["youtube_downloader", "use_cookies"])
                        set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")
            else:
                if self._env_data["YOUTUBE_COOKIE_PATH"] != '':
                    set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")

            self._dl = downloader.Downloader(spotify_client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                                             spotify_client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"],
                                             youtube_cookie_path=self._env_data["YOUTUBE_COOKIE_PATH"],
                                             cli_output_format=self._config_json["spotify_downloader"]["output_format"])

    def query_song_spotify(self) -> None:
        """
        query a song from spotify and save it to a JSON file with all data needed
        """
        import json

        self._init_downloader()

        data = self._dl.cli_search_song()
        view_name = self._dl.get_title_artist(metadata=data)
        youtube_id = self._dl.youtube_query(query=view_name)
        json_data = json.dumps({"pre_processing": {"youtube_id": youtube_id, "view_name": view_name, "raw_metadata": data}}, indent=4)
        file_path = self._temp_dir / f"{view_name}.json"

        file_path.write_text(json_data)
        self._logger.info(f"Saved song data: {view_name} -> {file_path}")

    def download_song(self, json_file: Path) -> None:
        """
        Downloads a song from YouTube using metadata present in .temp
        When no files are present, it will query spotify
        :param json_file: A path to a JSON file containing metadata, optional
        """
        from pathlib import Path
        from backend_new.utils.helper_funcs import questionary_select, write_json_file, read_json_file
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

        break_off = False

        if json_file is None:
            while True:
                if break_off:
                    break

                all_files = list(self._temp_dir.iterdir())
                all_files_stem = [file.stem for file in all_files]
                available_json_files = [file for file in all_files if file.suffix == ".json" and get_youtube_id_from_json(file) not in all_files_stem]

                # if songs are available, ask user which one to download or download the only one present
                if available_json_files:
                    # if only one song is available, download it
                    if len(available_json_files) == 1:
                        target_id = get_youtube_id_from_json(available_json_files[0])
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(_download(target_id))
                        except RuntimeError:
                            asyncio.run(_download(target_id))
                    # if multiple songs are available, ask user which one to download
                    elif len(available_json_files) > 1:
                        offset = 0

                        while True:
                            all_files = list(self._temp_dir.iterdir())
                            all_files_stem = [file.stem for file in all_files]
                            available_json_files = [file for file in all_files
                                                     if file.suffix == ".json" and
                                                     get_youtube_id_from_json(file) not in all_files_stem]

                            file_list = [{"name": file.stem, "value": file} for file in available_json_files]

                            user_choice = questionary_select("Please choose the song:",
                                                              choose_data=file_list,
                                                              enable_pages=True,
                                                              enable_all="Download All",
                                                              enable_exit="Exit",
                                                              batch_data=True)

                            if user_choice == "__all__":
                                target_ids = [get_youtube_id_from_json(file) for file in available_json_files]
                                tasks = [_download(y_id) for y_id in target_ids]

                                async def run_batch():
                                    await asyncio.gather(*tasks)

                                try:
                                    loop = asyncio.get_running_loop()
                                    loop.create_task(run_batch())
                                except RuntimeError:
                                    asyncio.run(run_batch())

                                for file in available_json_files:
                                    write_json_file(file, True, ["pre_processing", "downloaded"])
                                break_off = True
                                break
                            else:
                                file_data = read_json_file(user_choice)
                                tasks = [_download(file_data["pre_processing"]["youtube_id"])]

                                async def run_batch():
                                    await asyncio.gather(*tasks)

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
        """
        Processes a song, allows the user to choose which song to process
        """
        # region import statements
        from backend_new.utils.helper_funcs import questionary_select, questionary_checkbox, write_json_file, read_json_file
        from questionary import Choice, confirm
        import gc
        # endregion

        # region helper functions
        def update_song_data() -> None:
            """Updates the chosen song's data in the song_data variable."""
            nonlocal song_data
            song_data = read_json_file(user_song_choice)
        # endregion

        self._init_downloader()

        # region asks user which song to process
        while True:
            all_files = [file for file in self._temp_dir.iterdir() if file.suffix == ".json"]
            all_files_stem = [file.stem for file in all_files]

            song_choice_list = [{"name": file.stem, "value": file} for file in all_files]

            if not song_choice_list:
                song_choice_list.append(Choice(title="No songs available, please download a song first", disabled=True))

            user_song_choice = questionary_select("Please choose the song:",
                                                   choose_data=song_choice_list,
                                                   enable_pages=True,
                                                   batch_data=True,
                                                   batch_size=10,
                                                   extra_navigation_options=[Choice("Download New", value="__new__", shortcut_key="n")])
            if user_song_choice == "__new__":
                self.query_song_spotify()
            else:
                break

        song_data = read_json_file(user_song_choice)
        # endregion

        # region all processes, returns True if already done
        def _download() -> bool:
            """
            Downloads the song, checks if the audio file is present in the .temp dir, if not handle appropriately
            :return: True if already downloaded, False if not
            """
            if song_data.get("pre_processing", {}).get("downloaded", False):
                # checks if the audio file is present in the .temp dir, if not handle appropriately
                if song_data["pre_processing"].get("youtube_id", None) not in [file.stem for file in self._temp_dir.iterdir() if file.suffix == ".wav"]:
                    self._logger.warning("Data file says audio has been downloaded, but it isn't present in .temp directory")
                    self._logger.warning("Please do not rename, convert or alter files in .temp to prevent further errors")
                    self._logger.warning("Please clear all files in .temp directory to ensure proper functionality")
                    if confirm("Do you want to retry?").ask():
                        write_json_file(user_song_choice, False, ["pre_processing", "downloaded"])
                        update_song_data()
                        _download()
                    else:
                        raise self.DataMismatchError(self._logger, "Data file says audio has been downloaded, but it isn't present in .temp directory")
                self._logger.debug(f"Song already downloaded, skipping")
                return True
            else:
                self._logger.debug(f"Song not downloaded, downloading it now.")
                self.download_song(user_song_choice)
                write_json_file(user_song_choice, True, ["pre_processing", "downloaded"])
                self._logger.debug(f"Song downloaded.")
                return False

        def _genius_pull() -> bool:
            """
            Pulls Genius metadata for the song
            :return: True if already done, False if not
            """
            from backend_new.extractors.geniusextractor import GeniusExtractor

            if song_data.get("genius_data", None) is not None:
                self._logger.debug(f"Genius data already present, skipping")
                return True
            else:
                self._logger.debug(f"Genius data not present, pulling it now.")
                genius_data = GeniusExtractor(self._env_data["GENIUS_ACCESS_TOKEN"]).return_metadata(
                    title=song_data["pre_processing"]["raw_metadata"]["name"],
                    artist=song_data["pre_processing"]["raw_metadata"]["artists"][0]["name"]
                )
                write_json_file(user_song_choice, genius_data, ["genius_data"])
                self._logger.debug(f"Genius data pulled.")
                return False

        def _vocal_sep() -> bool:
            """
            Separates the audio into its stems
            :return: True if already done, False if not
            """
            # TODO add vocal sep model chooser
            if song_data.get("vocal_separation", {}).get("separated", False) is True:
                if song_data.get("vocal_separation", {}).get("vocal_file", None) not in [file.stem for file in self._temp_dir.iterdir() if file.suffix == ".wav"]:
                    raise self.DataMismatchError(self._logger, "Data file says audio has been separated, but it isn't present in .temp directory")
                if song_data.get("vocal_separation", {}).get("inst_file", None) not in [file.stem for file in self._temp_dir.iterdir() if file.suffix == ".wav"]:
                    raise self.DataMismatchError(self._logger, "Data file says audio has been separated, but it isn't present in .temp directory")

                self._logger.debug(f"Vocal separation already done, skipping")
                return True
            else:
                from backend_new.core.processing import VocalSeparation

                with VocalSeparation() as vs:
                    vs.separate_vocal(f"../.temp/{song_data["pre_processing"]["youtube_id"]}.wav")
                    write_json_file(user_song_choice, {"separated": True,
                                                        "vocal_file": f"{song_data["pre_processing"]["youtube_id"]}_vocal",
                                                        "inst_file": f"{song_data["pre_processing"]["youtube_id"]}_inst"}, ["vocal_separation"])

                return False

        def _lyrics_tag() -> bool:
            if song_data.get("split_and_tag", {}):
                self._logger.debug(f"Lyrics already tagged, skipping")
                return True
            else:
                from backend_new.core.processing import JPAnalyzer
                from backend_new.utils.helper_funcs import write_json_file

                self._logger.debug(f"Lyrics not tagged, tagging it now.")

                jp_analyzer = JPAnalyzer()

                lyrics = song_data["genius_data"]["lyrics"]
                data = jp_analyzer.tag(lyrics)
                write_json_file(user_song_choice, data, ["split_and_tag"])
                return False

        def _translate_lyrics() -> bool:
            if song_data.get("translated_lyrics", {}):
                self._logger.debug(f"Lyrics already translated, skipping")
                return True
            else:
                from backend_new.core.translation_analysis import Translator
                from backend_new.utils.helper_funcs import write_json_file

                self._logger.debug(f"Lyrics not translated, translating it now.")

                if self._translator is None:
                    self._translator = Translator()

                lyrics = song_data["genius_data"]["lyrics"]
                data = self._translator.translate_lyrics(lyrics)

                write_json_file(user_song_choice, data, ["translated_lyrics"])

                return False


        # endregion

        # region choice list for skip processes, update when adding new processes
        skip_options = self._config_json.get("skip_processes")

        choice_list = [Choice("Download song",
                               value="download_song",
                               checked=skip_options['download_song'],
                               disabled="Song already downloaded" if song_data.get("pre_processing", {}).get("downloaded") else None),
                        Choice("Get Genius metadata",
                               value="genius_metadata",
                               checked=skip_options['genius_metadata'],
                               disabled="Data already gathered" if song_data.get("genius_data") else None),
                        Choice("Separate audio into stems",
                               value="vocal_separation",
                               checked=skip_options['vocal_separation'],
                               disabled="Stems already separated" if song_data.get("vocal_separation", {}).get("separated") else None),
                        Choice("Split and tag lyrics",
                               value="split_tag",
                               description="(morphological analysis)",
                               checked=skip_options['split_and_tag'],
                               disabled="Lyrics already split and tagged" if song_data.get("split_and_tag", None) else None),
                        Choice("Translate lyrics to english",
                               value="translate_lyrics",
                               description="(LLM inference)",
                               checked=skip_options['translate_lyrics'],
                               disabled="Lyrics already translated" if song_data.get("translated_lyrics",None) else None)
                        ]

        skip_processes = questionary_checkbox("Please choose what options to skip", choice_data=choice_list)
        if skip_processes != [k for k in skip_options if skip_options[k]]:
            write_skip_to_json = confirm("Do you want to set this to default?").ask()
        else:
            write_skip_to_json = False

        for key in skip_options:
            if key in skip_processes:
                skip_options[key] = True
            else:
                skip_options[key] = False

        if write_skip_to_json:
            write_json_file(self._config_file, skip_options, ["skip_processes"])

        self._update_json_config()
        # endregion

        # region main loop for processes
        while True:
            # download
            if not skip_options["download_song"]:
                _download()
            update_song_data()

            # genius metadata
            if not skip_options["genius_metadata"]:
                _genius_pull()
            update_song_data()

            # vocal separation
            if not skip_options["vocal_separation"]:
                if not song_data["pre_processing"].get("downloaded", False):
                    self._logger.info("Audio cannot be separated as it hasn't been downloaded")
                    if confirm("Would you like to download first?").ask():
                        _download()
                        continue
                    else:
                        break
                _vocal_sep()

            # split and tag
            if not skip_options["split_and_tag"]:
                if song_data.get("genius_data", None) is None:
                    self._logger.info("Genius metadata not present")
                    if confirm("Would you like to pull it now?").ask():
                        _genius_pull()
                        continue
                    else:
                        break
                _lyrics_tag()

            # translate lyrics
            if not skip_options["translate_lyrics"]:
                if song_data.get("genius_data", None) is None:
                    self._logger.info("Genius metadata not present")
                    if confirm("Would you like to pull it now?").ask():
                        _genius_pull()
                        continue
                    else:
                        break
                _translate_lyrics()

            break
        # endregion


def main() -> None:
    ana = Analyzer()
    # ana._download("https://open.spotify.com/track/0UFmgncRMHavVzYxtpF0IZ?si=1c86deb161b24778")
    # ana._download("https://open.spotify.com/track/0VPkaJMRQIhYWXiE1LqaCK?si=a867127aa85a4769")
    # ana.download_song()
    # ana.query_song_spotify()
    ana.process_song()


if __name__ == "__main__":
    main()