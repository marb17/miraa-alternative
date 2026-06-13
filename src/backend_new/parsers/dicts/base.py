from abc import ABC, abstractmethod
from typing import Any
from functools import wraps
from pathlib import Path
from backend_new.utils.structures import DictionaryEntry, RawYomitanEntry
from backend_new.utils.constants import DICTS_DIR
import time

from backend_new.utils.logger import Logger
logger = Logger(__name__)




class BaseDictionaryParser(ABC):
    DICTIONARY_PATTERN: str = ""

    def __init__(self):
        if not self.DICTIONARY_PATTERN:
            raise NotImplementedError(
                f"Class '{self.__class__.__name__}' must define a non-empty 'DICTIONARY_PATTERN'"
            )

        try:
            self._target_dir = list(DICTS_DIR.glob(self.DICTIONARY_PATTERN))[0]
        except IndexError:
            raise FileNotFoundError(
                f"Could not find a directory matching pattern: '{self.DICTIONARY_PATTERN}' inside {DICTS_DIR}"
            )

        self._term_bank_files = self._get_term_bank_files()
        self._dict_name = self._target_dir.name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import gc
        gc.collect()
        return False

    @staticmethod
    def _time_taken_to_parse_dict(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            instance = args[0] if args else None

            now = time.time()
            result = func(*args, **kwargs)
            logger.debug(f"Time taken to parse {instance._dict_name}: {time.time() - now:.2f}s")

            return result

        return wrapper

    def _get_term_bank_files(self):
        return list(self._target_dir.rglob("term_bank_*.json"))

    @abstractmethod
    def _parse(self, raw_data: RawYomitanEntry) -> DictionaryEntry:
        """Parses one raw entry to DictionaryEntry"""
        pass

    # TODO change to a normal method because the format is always the same, only index 5 different
    @abstractmethod
    def _parse_file(self, file_path: Path) -> list[DictionaryEntry]:
        """Parses one term_bank_#.json file"""
        pass

    @abstractmethod
    def _execute_parsing(self) -> list[DictionaryEntry]:
        """Internal parsing logic implemented by specific dictionary types."""
        pass

    @_time_taken_to_parse_dict
    def parse_dict(self) -> list[DictionaryEntry]:
        """Public API method that handles the timing and triggers the subclass parsing."""
        return self._execute_parsing()
