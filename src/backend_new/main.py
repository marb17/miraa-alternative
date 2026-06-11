# STANDARD LIBRARIES
import json

from dotenv import set_key
from pathlib import Path

# HELPER LIBRARIES
from backend_new.utils.helper_funcs import (read_json_file, write_json_file,
                                            questionary_select, questionary_checkbox,
                                            load_env_file,
                                            clear_temp_dir)

from backend_new.core.workflow import WorkflowManager

# PYPI LIBRARIES
from questionary import Choice, confirm, path

# CONSTANTS
from backend_new.utils.constants import DEFAULT_CONFIG, DEFAULT_DICTS_MESSAGE
from backend_new.utils.structures import SongContext

from backend_new.utils.logger import Logger
logger = Logger(__name__)


class Analyzer:
    def __init__(self) -> None:
        """Initialize the analyzer."""
        self._setup_main_directories()
        self._env_data = load_env_file()
        self._setup_config_file()


    # region Helper Functions
    def _setup_main_directories(self) -> None:
        """Sets up the main directories for the analyzer."""
        current_dir = Path(__file__).resolve().parent
        while current_dir.name != "src" and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        self._base_dir = current_dir

        folder = ["data", "config", "models", ".temp", "dicts"]
        for p in folder:
            Path(self._base_dir / p).mkdir(parents=True, exist_ok=True)
        logger.debug("Main Directories created.")

        self._temp_dir = Path(self._base_dir / ".temp")
        self._config_file = Path(self._base_dir / "config/config.json")
        self._env_file = Path(self._base_dir / "config/.env")

        self._create_misc_files()

    def _setup_config_file(self) -> None:
        """Sets up the config file for the analyzer. Writes default values if it doesn't exist."""
        if not self._config_file.exists():
            config_json = json.dumps(DEFAULT_CONFIG, indent=4)
            self._config_file.write_text(config_json)
            logger.debug("Created config file and set default values.")
        else:
            config_json = self._config_file.read_text()
            logger.debug("Config file exists, read config file")

        self._config_json = json.loads(config_json)

        logger.info(f"miraa-alternative Version: {self._config_json['version']}")

    def _create_misc_files(self) -> None:
        # dicts directory
        dicts_dir = Path(self._base_dir / "dicts")
        dicts_file = dicts_dir / "readme.md"
        if not dicts_file.exists():
            dicts_file.write_text(DEFAULT_DICTS_MESSAGE, encoding="utf-8")
        else:
            pass

    @staticmethod
    def _clear_temp_directory() -> None:
        clear_temp_dir()
    # endregion

    # region pre-process checking
    def _check_downloader(self) -> None:
        if self._config_json["youtube_downloader"]["use_cookies"]:
            if self._env_data["YOUTUBE_COOKIE_PATH"] == '' or self._env_data["YOUTUBE_COOKIE_PATH"] is None:
                use_cookies = confirm("Do you want to use cookies?").ask()
                if use_cookies:
                    cookie_path = path("Please enter the path to your cookies file (Netscape .txt file): ").ask()
                    self._env_data["YOUTUBE_COOKIE_PATH"] = cookie_path
                    set_key(self._env_file, "YOUTUBE_COOKIE_PATH", cookie_path, quote_mode="never")
                else:
                    read_json_file(self._config_file)
                    write_json_file(self._config_file, False, ["youtube_downloader", "use_cookies"])
                    set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")
        else:
            if self._env_data["YOUTUBE_COOKIE_PATH"] != '':
                set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")

    def _pre_check_settings(self) -> None:
        ...

    # endregion
    def process_song(self) -> None:
        """
        Processes a song, allows the user to choose which song to process
        """
        # region helper functions
        def update_song_data() -> None:
            """Updates the chosen song's data in the song_data variable."""
            nonlocal song_context
            song_context.json_song_data = read_json_file(song_context.json_file_path)
        # endregion

        # region asks user which song to process
        while True:
            all_files = [file for file in self._temp_dir.iterdir() if file.suffix == ".json"]

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
                from backend_new.extractors.downloader import Downloader

                with Downloader() as downloader:
                    downloader.query_song_spotify()
            else:
                break

        song_data = read_json_file(user_song_choice)
        song_context = SongContext(song_data, user_song_choice)
        # endregion

        # region choice list for skip processes, update when adding new processes
        skip_options = self._config_json.get("skip_processes")

        choice_list = [Choice("Download song",
                               value="download_song",
                               checked=skip_options['download_song'],
                               disabled="Song already downloaded" if song_context.json_song_data.get("pre_processing", {}).get("downloaded") else None),
                        Choice("Get Genius metadata",
                               value="genius_metadata",
                               checked=skip_options['genius_metadata'],
                               disabled="Data already gathered" if song_context.json_song_data.get("genius_data") else None),
                        Choice("Separate audio into stems",
                               value="vocal_separation",
                               checked=skip_options['vocal_separation'],
                               disabled="Stems already separated" if song_context.json_song_data.get("vocal_separation", {}).get("separated") else None),
                        Choice("Split and tag lyrics",
                               value="split_and_tag",
                               description="(morphological analysis)",
                               checked=skip_options['split_and_tag'],
                               disabled="Lyrics already split and tagged" if song_context.json_song_data.get("split_and_tag", None) else None),
                        Choice("Translate lyrics to english",
                               value="translate_lyrics",
                               description="(LLM inference)",
                               checked=skip_options['translate_lyrics'],
                               disabled="Lyrics already translated" if song_context.json_song_data.get("translated_lyrics",None) else None)
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


        # endregion

        # region main loop for processes
        with WorkflowManager(song_context) as manager:
            # download
            if not skip_options["download_song"]:
                manager.download(song_context)
            update_song_data()

            # genius metadata
            if not skip_options["genius_metadata"]:
                manager.genius_pull(song_context)
            update_song_data()

            # vocal separation
            if not skip_options["vocal_separation"]:
                if not song_context.json_song_data["pre_processing"].get("downloaded", False):
                    logger.info("Audio cannot be separated as it hasn't been downloaded")
                    if confirm("Would you like to download first?").ask():
                        manager.download(song_context)
                    else:
                        logger.warning("Audio is not present, skipping vocal separation")
                if song_context.json_song_data["pre_processing"].get("downloaded", False):
                    manager.vocal_sep(song_context)

            # split and tag
            if not skip_options["split_and_tag"]:
                if song_context.json_song_data.get("genius_data", None) is None:
                    logger.info("Genius metadata not present")
                    if confirm("Would you like to pull it now?").ask():
                        manager.genius_pull(song_context)
                    else:
                        logger.warning("Genius data not present, skipping split and tag")
                if song_context.json_song_data.get("genius_data", None) is not None:
                    manager.lyrics_tag(song_context)

            # translate lyrics
            if not skip_options["translate_lyrics"]:
                if song_context.json_song_data.get("genius_data", None) is None:
                    logger.info("Genius metadata not present")
                    if confirm("Would you like to pull it now?").ask():
                        manager.genius_pull(song_context)
                    else:
                        logger.warning("Genius data not present, skipping translation of lyrics")
                if song_context.json_song_data.get("genius_data", None) is not None:
                    manager.translate_lyrics(song_context)
        # endregion


def main() -> None:
    ana = Analyzer()
    # ana._download("https://open.spotify.com/track/0UFmgncRMHavVzYxtpF0IZ?si=1c86deb161b24778")
    # ana._download("https://open.spotify.com/track/0VPkaJMRQIhYWXiE1LqaCK?si=a867127aa85a4769")
    # ana.download_song()
    # ana.query_song_spotify()
    ana.process_song()
    # ana._clear_temp_directory()

if __name__ == "__main__":
    main()