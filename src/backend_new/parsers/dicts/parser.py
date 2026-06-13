from backend_new.parsers.dicts.base import BaseDictionaryParser
from backend_new.utils.structures import DictionaryEntry, RawYomitanEntry, ExampleSentence, DefinitionSense, RedirectEntry
from backend_new.utils.exceptions import InvalidDictDefinitionFormatError

#! TEMP
from pathlib import Path
from backend_new.utils.helper_funcs import read_json_file
from typing import Any
from concurrent.futures import ProcessPoolExecutor
import os
import re
from urllib.parse import unquote
import time

from backend_new.utils.logger import Logger
logger = Logger(__name__)

class JitendexYomitanParser(BaseDictionaryParser):
    DICTIONARY_PATTERN = "*jitendex-yomitan*"

    def _sense_group_parser(self, data: list[dict[str, Any]]) -> DefinitionSense | list[str]:
        holding: DefinitionSense = DefinitionSense()

        if isinstance(data, dict):
            data = [data]

        for section in data:
            if section["tag"] == "span" and section.get('data', {}).get('content') == "part-of-speech-info":
                holding.parts_of_speech.append(section['title'])

            elif section["tag"] == "div" and section['data']['content'] == "sense":
                sense_contents = section['content']
                if isinstance(sense_contents, dict):
                    sense_contents = [sense_contents]

                for sense_content in sense_contents:
                    if sense_content['tag'] == "ul" and sense_content['data']['content'] == "glossary":
                        glossary_contents = sense_content['content']
                        if isinstance(glossary_contents, dict):
                            glossary_contents = [glossary_contents]

                        for glossary_content in glossary_contents:
                            if glossary_content['tag'] == "li":
                                holding.glossaries.append(glossary_content['content'])
                            else:
                                raise InvalidDictDefinitionFormatError()

                    elif sense_content['tag'] == "div" and sense_content['data']['content'] == "extra-info":
                        extra_info_contents = sense_content['content']
                        if isinstance(extra_info_contents, dict):
                            extra_info_contents = [extra_info_contents]

                        # TODO add example sentences

                    else:
                        raise InvalidDictDefinitionFormatError()

            elif section["tag"] == "ul" and section.get('data', {}).get('content') == "glossary":
                glossary_contents = section['content']
                raw_definition_holding = []

                if isinstance(glossary_contents, dict):
                    glossary_contents = [glossary_contents]

                for glossary_content in glossary_contents:
                    if glossary_content['tag'] == "li":
                        # holding.glossaries.append(glossary_content['content'])
                        raw_definition_holding.append(glossary_content['content'])
                    else:
                        raise InvalidDictDefinitionFormatError()

                return raw_definition_holding

            elif section["tag"] == "span" and section.get('data', {}).get('content') == "misc-info":
                ...

            elif section["tag"] == "span" and section.get('data', {}).get('content') == "dialect-info":
                ...

            elif section["tag"] == "span" and section.get('data', {}).get('content') == "field-info":
                ...

            elif section["tag"] == "ol":
                senses_content = section['content']

                if isinstance(senses_content, dict):
                    senses_content = [senses_content]

                # glossary_holding: list[DefinitionSense] = []

                for sense in senses_content:
                    sense_content = sense['content']

                    response = self._sense_group_parser(sense_content)

                    # glossary_holding.append(response)
                    holding.glossaries.append(response)


            # so it doesnt shit itself on useless shit
            elif section["tag"] == "div" and section["data"]["content"] == "extra-info":
                pass

            elif section["tag"] == "span" and section.get('data', {}).get('content') == "forms-label":
                pass

            elif section["tag"] == "table" and section.get("content", [])[0].get('data', {}).get('content') == "forms-header-row":
                pass

            elif section["tag"] == "table" and section.get('data', {}).get('content') == "forms-header-row":
                pass

            elif section["tag"] == "table" and section.get("content", [])[0].get('data', {}).get('content') == "forms-col-senses-row":
                pass

            elif section["tag"] == "span" and section.get('content', [])[0].get("data", {}).get("class") == "form-special":
                pass

            elif section["tag"] == "ul" and isinstance(section["content"], list):
                pass

            elif section["tag"] == "ul" and section.get("content", {}).get("tag") == "li":
                pass

            else:
                print(section, data, sep="\n")
                raise InvalidDictDefinitionFormatError()

        return holding

    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry]:
        definition_data = raw_data.definitions
        raw_word = raw_data.term

        definitions = []

        for definition in definition_data:
            if isinstance(definition, list):
                continue

            if definition.get("type", "") != "structured-content":
                raise InvalidDictDefinitionFormatError("Type is not structured-content")

            main_content = definition.get("content")

            if isinstance(main_content, list):
                for section in main_content:
                    if section['tag'] == "div" and section['data']['content'] == "sense-group":
                        sense_group_content = section['content']
                        response = self._sense_group_parser(sense_group_content)
                        definitions.append(DictionaryEntry(self.dict_name, raw_data.term, raw_data.reading, response))

                    elif section['tag'] == "div" and section['data']['content'] == "attribution":
                        ...

                    elif section['tag'] == "div" and section['data']['content'] == "forms":
                        ...

                    elif section['tag'] == "ul" and section['data']['content'] == "sense-groups":
                        sense_groups_contents = section['content']

                        if isinstance(sense_groups_contents, dict):
                            sense_groups_contents = [sense_groups_contents]

                        for sense_group in sense_groups_contents:
                            response = self._sense_group_parser(sense_group['content'])
                            definitions.append(DictionaryEntry(self.dict_name, raw_data.term, raw_data.reading, response))

                    else:
                        raise InvalidDictDefinitionFormatError()

            elif isinstance(main_content, dict):
                if main_content.get("data", {}).get("content") == "redirect-glossary":
                    redirect_info = main_content["content"][1]["href"]

                    first_pattern = re.compile(r"\?query=([%A-Z0-9\-\.]*)\&wildcards=off\&primary_reading=([%A-Z0-9\-\.]*)")
                    second_pattern = re.compile(r"\?query=([%A-Z0-9\-\.]*)\&wildcards=off")

                    if first_pattern.match(redirect_info):
                        redirect_word, redirect_primary_reading = first_pattern.findall(redirect_info)[0]
                        redirect_word, redirect_primary_reading = unquote(redirect_word), unquote(redirect_primary_reading)
                        definitions.append(RedirectEntry(self.dict_name, raw_word, redirect_word, redirect_primary_reading))
                    elif second_pattern.match(redirect_info):
                        redirect_word = second_pattern.findall(redirect_info)[0]
                        redirect_word = unquote(redirect_word)
                        definitions.append(RedirectEntry(self.dict_name, raw_word, redirect_word))
                    else:
                        print(redirect_info)
                        raise InvalidDictDefinitionFormatError(redirect_info)

                else:
                    raise InvalidDictDefinitionFormatError()

            else:
                raise InvalidDictDefinitionFormatError()

        return definitions


class PixivLightParser(BaseDictionaryParser):
    DICTIONARY_PATTERN = "*PixivLight*"

    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry] | DictionaryEntry | RedirectEntry:
        definition_data = raw_data.definitions

        holding: DefinitionSense = DefinitionSense()

        for definition in definition_data:
            if isinstance(definition, list):
                continue

            if definition.get("type", "") != "structured-content":
                raise InvalidDictDefinitionFormatError("Type is not structured-content")

            main_content = definition.get("content")

            if isinstance(main_content, list):
                for section in main_content:
                    if section["tag"] == "ul" and section["data"]["pixiv"] == "summary":
                        summary_contents = section["content"]

                        if isinstance(summary_contents, dict):
                            summary_contents = [summary_contents]

                        for summary_content in summary_contents:
                            if summary_content["tag"] == "li":
                                holding.glossaries.append(summary_content["content"])
                            else:
                                raise InvalidDictDefinitionFormatError()

                    elif section["tag"] == "div" and section["data"]["pixiv"] == "series":
                        if isinstance(section["content"], str):
                            holding.series.append(section["content"])

                        else:
                            raise InvalidDictDefinitionFormatError()

                    # so it doesnt shit it self
                    elif section["tag"] == "div" and section["data"]["pixiv"] == "footer":
                        ...

                    elif section["tag"] == "div" and section["data"]["pixiv"] == "parent-link":
                        # TODO idk what this is
                        ...

                    else:
                        print(section)
                        raise InvalidDictDefinitionFormatError()

            else:
                raise InvalidDictDefinitionFormatError()

        return DictionaryEntry(self.dict_name, raw_data.term, raw_data.reading, [holding])






if __name__ == "__main__":
    with PixivLightParser() as parser:
        parser.parse_dict()