from backend_new.parsers.dicts.base import BaseDictionaryParser
from backend_new.utils.structures import DictionaryEntry, RawYomitanEntry
from backend_new.utils.exceptions import InvalidDictDefinitionFormatError

#! TEMP
from pathlib import Path
from backend_new.utils.helper_funcs import read_json_file

class JitendexYomitanParser(BaseDictionaryParser):
    DICTIONARY_PATTERN = "*jitendex-yomitan*"

    # region HELPER
    def _sense_group_parse(self, data: list[dict]) -> Any:
        for entry in data:
            ...
    # endregion

    def _parse(self, raw_data) -> DictionaryEntry:
        definition_data = raw_data.definitions

        for definition in definition_data:
            if definition.get("type", "") != "structured-content":
                raise InvalidDictDefinitionFormatError("Type is not structured-content")

            content = definition.get("content", [])
            for cont in content:
                if cont.get("tag") == "div":
                    ...

    def _parse_file(self, file_path: Path) -> list[DictionaryEntry]:
        json_data = read_json_file(file_path)

        results: list[DictionaryEntry] = list()
        for entry in json_data:
            results.append(self._parse(RawYomitanEntry(*entry)))

    def parse_dict(self) -> list[DictionaryEntry]:
        dict_data: list[DictionaryEntry] = list()

        for file in self._term_bank_files:
            dict_data.extend(self._parse_file(file))
            #! TEMP
            break


if __name__ == "__main__":
    with JitendexYomitanParser() as parser:
        parser.parse_dict()