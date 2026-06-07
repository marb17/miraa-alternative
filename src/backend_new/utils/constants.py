# ===================================================
#      DIRECTORIES
# ===================================================

# BASE DIR
from pathlib import Path
from dataclasses import dataclass

from accelerate.utils import other

from backend_new.utils.logger import Logger

# ! Adjust based on exact depth
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


# ===================================================
#       DATACLASSES
# ===================================================


# SONG CONTEXT
@dataclass
class SongContext:
    json_song_data: dict
    json_file_path: Path


# ===================================================
#       ERRORS / EXCEPTIONS
# ===================================================

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


# ===================================================
#      DEFAULT VARIABLES
# ===================================================

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

# ===================================================
#      AUDIO SEPARATION
# ===================================================
MODEL_INFO = """\b
2-STEM SEPARATION (Vocals & Instrumental):
  vocal_full                Rawer vocals, best articulation, minor noise artifacts.
  vocal_clean               Polished vocals, minimal noise, slightly muffled in mid-tones.
  instrumental_full         Pristine backing tracks; vocal stems are low-priority.
  instrumental_low_resource Fast, lightweight processing; minor stem bleed.

\b
MULTI-STEM SEPARATION (Full Band):
  htdemucs_ft               Elite 4-stem model (Vocals/Drums/Bass/Other). Minimal artifacts.
  htdemucs_6s               6-stem model adds Guitar/Piano. Higher artifact risk.

\b
SPECIALIZED CORE UTILITIES:
  drum_sep                  Isolates acoustic/electronic drum elements natively.
  dereverb                  Strips room reflections, decay, and echo tails from stems.
  crowd_iso                 Separates central performances from background crowd noise.
"""

AUDIO_MODEL_PRESETS: dict[str, dict[str, str | list[str]]] = {
    # ENSEMBLES
    "vocal_full": {"model_name": "vocal_full",
                   "type": "ensemble",
                   "rename_order": ["inst", "vocal"]},
    "vocal_clean": {"model_name": "vocal_clean",
                    "type": "ensemble",
                    "rename_order": ["inst", "vocal"]},
    "instrumental_full": {"model_name": "instrumental_full",
                          "type": "ensemble",
                          "rename_order": ["vocal", "inst"]},
    "instrumental_low_resource": {"model_name": "instrumental_low_resource",
                                  "type": "ensemble",
                                  "rename_order": ["vocal", "inst"]},

    # SINGLE MODELS
    "htdemucs_ft": {"model_name": "htdemucs_ft.yaml",
                    "type": "single",
                    "rename_order": ["bass", "drums", "other", "vocal"]},
    "htdemucs_6s": {"model_name": "htdemucs_6s.yaml",
                    "type": "single",
                    "rename_order": ["bass", "drums", "other", "vocal", "guitar", "piano"]},
    "drum_sep": {"model_name": "MDX23C-DrumSep-aufr33-jarredou.ckpt",
                 "type": "single",
                 "rename_order": ["kick", "snare", "toms", "hh", "ride", "crash"]},
    "dereverb": {"model_name": "dereverb_mel_band_roformer_anvuew_sdr_19.1729.ckpt",
                 "type": "single",
                 "rename_order": ["dry", "wet"]},
    "crowd_iso": {"model_name": "mel_band_roformer_crowd_aufr33_viperx_sdr_8.7144.ckpt",
                  "type": "single",
                  "rename_order": ["wet", "dry"]}
}
