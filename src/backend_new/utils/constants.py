import re

#===================================================
#      DIRECTORIES
#===================================================

# BASE DIR
from pathlib import Path
from dataclasses import dataclass, field
from backend_new.utils.logger import Logger
from typing import Literal, Any

#! Adjust based on exact depth
BASE_DIR = Path(__file__).resolve().parent.parent.parent

#! CHANGE WHEN CHANGING BACKEND FOLDER NAME
BACKEND_DIR = BASE_DIR / "backend_new"

# DIRECTORIES
TEMP_DIR = BASE_DIR / ".temp"
DICTS_DIR = BASE_DIR / "dicts"
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

TUI_TCSS = BACKEND_DIR / "tui/tcss"

# FILES
ENV_FILE = CONFIG_DIR / ".env"
CONFIG_FILE = CONFIG_DIR / "config.json"

#===================================================
#       DATACLASSES
#===================================================


# SONG CONTEXT
@dataclass
class SongContext:
    json_song_data: dict
    json_file_path: Path

@dataclass
class UIPromptRequest:
    type: Literal["select", "input", "confirm"]
    message: str
    sub_type: str | None = None
    choices: list[Any] | None = None
    persistent_choices: list[Any] | None = None
    default: Any = None
    password: bool = False
    placeholder: str = ""

#===================================================
#       ERRORS / EXCEPTIONS
#===================================================

class DataMismatchError(Exception):
    def __init__(self, logger: Logger, message: str = 'Files do not match the data in .temp directory') -> None:
        """
        An error occurring when a data file does not match the expected files or other data required
        :param logger: Logger object used for logging instructions
        :type logger: Logger
        :param message: Custom message to display
        :type message: str
        """
        self.logger = logger
        self.message = message

        self.data_mismatch_error()

        super().__init__(self.message)

    def data_mismatch_error(self):
        self.logger.warning(self.message)
        self.logger.warning("Please do not rename, convert or alter files in .temp to prevent further errors")
        self.logger.warning("Please clear all files in .temp directory to ensure proper functionality")

#===================================================
#      DEFAULT VARIABLES
#===================================================

DEFAULT_CONFIG = {
    "version": "1.0.0",
    "init": True,

    "downloader": {
        "view_limit": 10,
        "retry_count": 3,
        "retry_sleep": 5
    },

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
        "translate_lyrics": False
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

DEFAULT_DICTS = ["PixivLight",
              "JMnedict",
              "jitendex-yomitan",
              "擬音語・擬態語辞典",
              "四字熟語の百科事典",
              "ことわざ・慣用句の百科事典",
              "大辞林　第四版"]

DEFAULT_DICTS_FOLDER_LINK = 'https://drive.google.com/drive/folders/1xURpMJN7HTtSLuVs9ZtIbE7MDRCdoU29?usp=drive_link'

TEST_DRIVE = {"1": "https://drive.google.com/file/d/1XwS1zZPz9Q9SVM-s_SZaVifa6MWSxaZD/view?usp=drive_link",
              "2": "https://drive.google.com/file/d/1PFE3ahf-uMzB7EXSmIzGZJFNCX92OgQB/view?usp=drive_link",
              "3": "https://drive.google.com/file/d/1GkiwXxa-P-7GAlxBNGqbmqQQHO38PC89/view?usp=drive_link"}