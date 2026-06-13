from abc import ABC, abstractmethod
from typing import Any
from functools import wraps
from pathlib import Path
from backend_new.utils.structures import DictionaryEntry, RawYomitanEntry, RedirectEntry
from backend_new.utils.constants import DICTS_DIR
from backend_new.utils.exceptions import InvalidDictDefinitionFormatError
from backend_new.utils.helper_funcs import read_json_file
import time
from concurrent.futures import ProcessPoolExecutor
import os

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
        self.dict_name = self._target_dir.name

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
            logger.debug(f"Time taken to parse {instance.dict_name}: {time.time() - now:.2f}s")

            return result

        return wrapper

    def _get_term_bank_files(self):
        return list(self._target_dir.rglob("term_bank_*.json"))

    @abstractmethod
    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry] | DictionaryEntry | RedirectEntry:
        """Parses one raw entry to DictionaryEntry"""
        pass

    # @abstractmethod
    def _parse_file(self, file_path: Path) -> list[list[DictionaryEntry | RedirectEntry]]:
        json_data = read_json_file(file_path)

        results: list[list[DictionaryEntry | RedirectEntry]] = list()
        for entry in json_data:
            response = self._parse(RawYomitanEntry(*entry))
            if isinstance(response, list):
                pass
            else:
                response = [response]

            results.append(response)

        return results

    # @abstractmethod
    def _execute_parsing(self) -> dict[str, list[DictionaryEntry | RedirectEntry]]:
        dict_data: list[list[DictionaryEntry]] = list()

        max_workers = (os.cpu_count() or 8) // 4

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(self._parse_file, self._term_bank_files)

            for file_data in results:
                dict_data.extend(file_data)

        final_dictionary: dict[str, list[DictionaryEntry | RedirectEntry]] = dict()
        for entry in dict_data:
            for sub_entry in entry:
                if isinstance(sub_entry, DictionaryEntry):
                    main_term = sub_entry.word
                elif isinstance(sub_entry, RedirectEntry):
                    main_term = sub_entry.word
                    logger.debug(sub_entry)
                else:
                    # print(dict_data)
                    print(entry)
                    print(type(sub_entry))
                    print(sub_entry)
                    raise InvalidDictDefinitionFormatError()

                if main_term in final_dictionary:
                    final_dictionary[main_term].append(sub_entry)
                else:
                    final_dictionary[main_term] = [sub_entry]

        return final_dictionary

    @_time_taken_to_parse_dict
    def parse_dict(self) -> dict[str, list[DictionaryEntry | RedirectEntry]]:
        """Public API method that handles the timing and triggers the subclass parsing."""
        return self._execute_parsing()
