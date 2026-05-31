# BASE DIR
from pathlib import Path
from dataclasses import dataclass
from backend_new.utils.logger import Logger

#! Adjust based on exact depth
BASE_DIR = Path(__file__).resolve().parent.parent.parent

TEMP_DIR = BASE_DIR / ".temp"
DICTS_DIR = BASE_DIR / "dicts"
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

# SONG CONTEXT
@dataclass
class SongContext:
    json_song_data: dict
    json_file_path: Path

# ERROR / EXCEPTIONS
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
