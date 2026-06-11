#===================================================
#      DIRECTORIES
#===================================================

# BASE DIR
from pathlib import Path

#! Adjust based on exact depth
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# DIRECTORIES
TEMP_DIR = BASE_DIR / ".temp"
DICTS_DIR = BASE_DIR / "dicts"
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

# FILES
ENV_FILE = CONFIG_DIR / ".env"
CONFIG_FILE = CONFIG_DIR / "config.json"


#===================================================
#      DEFAULT VARIABLES
#===================================================

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
        "translate_lyrics": False
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

