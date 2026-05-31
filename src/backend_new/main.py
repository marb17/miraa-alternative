# STANDARD LIBRARIES
import json
import os
import asyncio
import gc

from dotenv import load_dotenv, set_key
from pathlib import Path

# HELPER LIBRARIES
from backend_new.utils import logger
from backend_new.utils.logger import Logger
from backend_new.utils.helper_funcs import read_json_file, write_json_file, questionary_select, questionary_checkbox

from backend_new.extractors import downloader
from backend_new.extractors.geniusextractor import GeniusExtractor

from backend_new.core.processing import VocalSeparation, JPAnalyzer
from backend_new.core.translation_analysis import Translator

from backend_new.utils.constants import SongContext, DataMismatchError

# PYPI LIBRARIES
from questionary import Choice, confirm, path


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
        self._logger = logger.Logger()

        self._setup_main_directories()
        self._load_env_file()
        self._setup_config_file()

        self._dl = None
        self._translator = None


    # region Helper Functions
    def _setup_main_directories(self) -> None:
        """Sets up the main directories for the analyzer."""
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
        self._config_json = read_json_file(self._config_file)

    def _load_env_file(self) -> None:
        """
        Loads the environment variables from the .env file.
        Creates a new .env file if it doesn't exist.
        DOES NOT check if the file is filled
        """
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
    def query_song_spotify(self) -> None:
        """
        query a song from spotify and save it to a JSON file with all data needed
        """
        self._init_downloader()

        data = self._dl.cli_search_song()
        view_name = self._dl.get_title_artist(metadata=data)
        youtube_id = self._dl.youtube_query(query=view_name)
        json_data = json.dumps({"pre_processing": {"youtube_id": youtube_id, "view_name": view_name, "raw_metadata": data}}, indent=4)
        file_path = self._temp_dir / f"{view_name}.json"

        file_path.write_text(json_data)
        self._logger.info(f"Saved song data: {view_name} -> {file_path}")

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
        song_context = self.SongContext(song_data, user_song_choice)
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
                               value="split_tag",
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

        self._update_json_config()
        # endregion

        # region main loop for processes
        # download
        if not skip_options["download_song"]:
            self._download(song_context)
        update_song_data()

        # genius metadata
        if not skip_options["genius_metadata"]:
            self._genius_pull(song_context)
        update_song_data()

        # vocal separation
        if not skip_options["vocal_separation"]:
            if not song_context.json_song_data["pre_processing"].get("downloaded", False):
                self._logger.info("Audio cannot be separated as it hasn't been downloaded")
                if confirm("Would you like to download first?").ask():
                    self._download(song_context)
                else:
                    self._logger.warning("Audio is not present, skipping vocal separation")
            if song_context.json_song_data["pre_processing"].get("downloaded", False):
                self._vocal_sep(song_context)

        # split and tag
        if not skip_options["split_and_tag"]:
            if song_context.json_song_data.get("genius_data", None) is None:
                self._logger.info("Genius metadata not present")
                if confirm("Would you like to pull it now?").ask():
                    self._genius_pull(song_context)
                else:
                    self._logger.warning("Genius data not present, skipping split and tag")
            if song_context.json_song_data.get("genius_data", None) is not None:
                self._lyrics_tag(song_context)

        # translate lyrics
        if not skip_options["translate_lyrics"]:
            if song_context.json_song_data.get("genius_data", None) is None:
                self._logger.info("Genius metadata not present")
                if confirm("Would you like to pull it now?").ask():
                    self._genius_pull(song_context)
                else:
                    self._logger.warning("Genius data not present, skipping translation of lyrics")
            if song_context.json_song_data.get("genius_data", None) is not None:
                self._translate_lyrics(song_context)
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