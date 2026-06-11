from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path
from backend_new.utils.structures import DictionaryEntry, RawYomitanEntry
from backend_new.utils.constants import DICTS_DIR

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import gc
        gc.collect()
        return False

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
    def parse_dict(self) -> list[DictionaryEntry]:
        """Searches the entire directory and outputs list of DictionaryEntry"""