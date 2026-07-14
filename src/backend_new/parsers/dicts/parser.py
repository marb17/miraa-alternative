from backend_new.parsers.dicts.base import BaseDictionaryParser
from backend_new.utils.classes.dataclasses import ExampleSentence, RawYomitanEntry, DefinitionSense, DictionaryEntry, \
    RedirectEntry
from backend_new.utils.classes.exceptions import InvalidDictDefinitionFormatError

#! TEMP
from pathlib import Path
from dataclasses import asdict
from backend_new.utils.helper_funcs import read_json_file, write_json_file
from backend_new.utils.constants import DICTS_DIR
from typing import Any
from concurrent.futures import ProcessPoolExecutor
import os
import re
from urllib.parse import unquote
import time
import json
import math

from backend_new.utils.logger import Logger
logger = Logger(__name__)

# region single parsers

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
                                raise InvalidDictDefinitionFormatError(logger, "")

                    elif sense_content['tag'] == "div" and sense_content['data']['content'] == "extra-info":
                        extra_info_contents = sense_content['content']
                        if isinstance(extra_info_contents, dict):
                            extra_info_contents = [extra_info_contents]

                        # TODO add example sentences

                    else:
                        raise InvalidDictDefinitionFormatError(logger, "")

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
                        raise InvalidDictDefinitionFormatError(logger, "")

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
                    if isinstance(response, DefinitionSense):
                        if response.glossaries:
                            raise InvalidDictDefinitionFormatError(logger, "")
                        if response.examples:
                            raise InvalidDictDefinitionFormatError(logger, "")
                        if response.sense_number:
                            raise InvalidDictDefinitionFormatError(logger, "")
                        if response.parts_of_speech:
                            raise InvalidDictDefinitionFormatError(logger, "")
                        if response.series:
                            raise InvalidDictDefinitionFormatError(logger, "")
                    else:
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
                raise InvalidDictDefinitionFormatError(logger, "")

        return holding

    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry]:
        definition_data = raw_data.definitions
        raw_word = raw_data.term

        definitions = []

        for definition in definition_data:
            if isinstance(definition, list):
                redirect_to = definition[0]
                word = re.findall(r"redirected from (.*)", definition[1][0])[0]
                definitions.append(RedirectEntry(self.dict_name, word, redirect_to))
                continue

            if definition.get("type", "") != "structured-content":
                raise InvalidDictDefinitionFormatError(logger, "")

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
                        raise InvalidDictDefinitionFormatError(logger, "")

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
                        raise InvalidDictDefinitionFormatError(logger, "")

                else:
                    raise InvalidDictDefinitionFormatError(logger, "")

            else:
                raise InvalidDictDefinitionFormatError(logger, "")

        return definitions


class PixivLightParser(BaseDictionaryParser):
    DICTIONARY_PATTERN = "*PixivLight*"

    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry] | DictionaryEntry | RedirectEntry:
        definition_data = raw_data.definitions

        definitions = []

        for definition in definition_data:
            holding: DefinitionSense = DefinitionSense()

            if definition.get("type", "") != "structured-content":
                raise InvalidDictDefinitionFormatError(logger, "")

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
                                raise InvalidDictDefinitionFormatError(logger, "")

                    elif section["tag"] == "div" and section["data"]["pixiv"] == "series":
                        if isinstance(section["content"], str):
                            holding.series.append(section["content"])

                        else:
                            raise InvalidDictDefinitionFormatError(logger, "")

                    # so it doesnt shit it self
                    elif section["tag"] == "div" and section["data"]["pixiv"] == "footer":
                        ...

                    elif section["tag"] == "div" and section["data"]["pixiv"] == "parent-link":
                        # TODO idk what this is
                        ...

                    else:
                        raise InvalidDictDefinitionFormatError(logger, "")

            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            definitions.append(DictionaryEntry(self.dict_name, raw_data.term, raw_data.reading, [holding]))

        return definitions


class JMnedictParser(BaseDictionaryParser):
    DICTIONARY_PATTERN = "*JMnedict*"

    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry] | DictionaryEntry | RedirectEntry:
        definition_data = raw_data.definitions

        holding: DefinitionSense = DefinitionSense()

        for definition in definition_data:
            if isinstance(definition, str):
                holding.glossaries.append(definition)

            else:
                raise InvalidDictDefinitionFormatError(logger, "")

        return DictionaryEntry(self.dict_name, raw_data.term, raw_data.reading, [holding])


class GiongoGitaigoJitenParser(BaseDictionaryParser):
    DICTIONARY_PATTERN = "*擬音語・擬態語辞典*"

    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry] | DictionaryEntry | RedirectEntry:
        definition_data = raw_data.definitions
        raw_word = raw_data.term

        definitions = []

        skip_by: int = 0

        circled_numbers = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]")
        jp_quotes = re.compile(r"「.*」")
        synonyms_content = re.compile(r"類義語(.*)")
        redirect_format = re.compile(r"「\?query=([^」^「]*)&wildcards=off」")
        arrow_redirect = re.compile(r"➜(.*)")
        full_stop_ending = re.compile(r".*。")
        for_reference = re.compile(r"参考(.*)")

        for definition in definition_data:
            holding: DefinitionSense = DefinitionSense()
            extra_info = []
            synonyms = []
            synonyms_info = []
            similar_words = []

            if definition["type"] == "structured-content":
                structured_contents = definition["content"]
            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            temporary_string = ""

            for idx, section in enumerate(structured_contents):
                content = section["content"]

                if isinstance(content, str):
                    temporary_string += content
                elif isinstance(content, dict):
                    if content["tag"] == "a":
                        temporary_string += content["href"]

                    elif content["tag"] == "ruby":
                        temporary_string += content["content"][0]

                    else:
                        raise InvalidDictDefinitionFormatError(logger, "")

                else:
                    raise InvalidDictDefinitionFormatError(logger, "")

            formatted_contents = temporary_string.split("\n")

            # ---------------------------------------------------

            if len(formatted_contents) == 1:
                if arrow_redirect.match(formatted_contents[0]):
                    definitions.extend([RedirectEntry(self.dict_name, raw_word, redirect_to) for redirect_to in redirect_format.findall(formatted_contents[0])])

            for line in formatted_contents:
                if circled_numbers.match(line):
                    holding.glossaries.append(line)

                elif jp_quotes.match(line):
                    holding.examples.append({"jp": line})

                elif synonyms_content.match(line):
                    contents = synonyms_content.findall(line)[0]
                    response = redirect_format.findall(contents)
                    synonyms.extend(response)

                elif "類義語" in line:
                    synonyms_info.append(line)

                elif arrow_redirect.match(line):
                    contents = arrow_redirect.findall(line)[0]
                    redirect_info = redirect_format.findall(contents)
                    similar_words.extend(redirect_info)

                elif for_reference.match(line) and len(formatted_contents) > 1:
                    content = for_reference.findall(line)[0]
                    extra_info.append(content)

                elif line.strip() == "":
                    pass

                # fall back
                elif full_stop_ending.match(line):
                    holding.glossaries.append(line)

                else:
                    raise InvalidDictDefinitionFormatError(logger, "")

            # extra info stuf
            entry = DictionaryEntry(self.dict_name, raw_data.term, raw_data.reading, [holding])
            entry.extra_info["extra_info"].extend(extra_info)
            entry.extra_info["synonyms"].extend(synonyms)
            entry.extra_info["synonym_info"].extend(synonyms_info)
            entry.extra_info["similar_words"].extend(similar_words)

            definitions.append(entry)

        return definitions


class YonJiJukugoNoHyakkaJitenParser(BaseDictionaryParser):
    DICTIONARY_PATTERN = "*四字熟語の百科事典*"

    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry] | DictionaryEntry | RedirectEntry:
        definition_data = raw_data.definitions
        raw_word = raw_data.term

        main_word = re.compile(r"【(.*)】")

        definitions = []

        for definition in definition_data:
            if definition["type"] == "structured-content":
                structured_contents = definition["content"]
            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            if isinstance(structured_contents, list):
                pass
            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            if len(structured_contents) == 3:
                overview = structured_contents[0]
                meaning = structured_contents[1]
                example_sentences = structured_contents[2]
            elif len(structured_contents) == 4:
                overview = structured_contents[0]
                image_data = structured_contents[1]
                meaning = structured_contents[2]
                example_sentences = structured_contents[3]
            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            if overview['tag'] == "span" and overview["data"]["name"] == "header":
                inner_content = overview["content"]
                if len(inner_content) != 3:
                    raise InvalidDictDefinitionFormatError(logger, "")

                idiom = main_word.findall(inner_content[1]["content"])[0]
                reading = inner_content[0]["content"]
            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            if meaning["tag"] == "div" and meaning["data"]["name"] == "意味":
                if len(meaning["content"]) != 2:
                    raise InvalidDictDefinitionFormatError(logger, "")
                definition = meaning["content"][1]["content"]
            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            if example_sentences["tag"] == "div" and example_sentences["data"]["name"] == "使い方":
                examples = []
                if len(example_sentences["content"]) == 2:
                    list_of_examples = example_sentences["content"][1]["content"]
                    if example_sentences["content"][1]["tag"] != "ul":
                        raise InvalidDictDefinitionFormatError(logger, "")

                    if isinstance(list_of_examples, list):
                        for li in list_of_examples:
                            if len(li["content"]) != 1:
                                raise InvalidDictDefinitionFormatError(logger, "")
                            meaning = li["content"][0]["content"]
                            examples.append(meaning)
                    else:
                        raise InvalidDictDefinitionFormatError(logger, "")
                else:
                    raise InvalidDictDefinitionFormatError(logger, "")

            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            holding = DefinitionSense()

            holding.examples.extend(examples)
            holding.glossaries.append(definition)

            final_def = DictionaryEntry(self.dict_name, raw_data.term, reading, [holding])
            definitions.append(final_def)

        return definitions


class KotowazaKanyoukuNoHyakkaJitenParser(YonJiJukugoNoHyakkaJitenParser):
    DICTIONARY_PATTERN = "*ことわざ・慣用句の百科事典*"


class DaijirinDaiYonHanParser(BaseDictionaryParser):
    DICTIONARY_PATTERN = "*大辞林*第四版*"

    def _parse(self, raw_data: RawYomitanEntry) -> list[DictionaryEntry | RedirectEntry] | DictionaryEntry | RedirectEntry:
        definition_data = raw_data.definitions
        raw_word = raw_data.term

        definitions = []

        for definition in definition_data:
            if definition["type"] == "structured-content":
                structured_contents = definition["content"]
            else:
                raise InvalidDictDefinitionFormatError(logger, "")

            if isinstance(structured_contents, list):
                if len(structured_contents) == 2 or len(structured_contents) == 3:
                    section_1 = structured_contents[0]
                    section_2 = structured_contents[1]
                    section_3 = structured_contents[2] if len(structured_contents) == 3 else None

                    # section 1
                    if section_1["tag"] == "span" and section_1["data"]["name"] == "見出部":
                        section_1_content = section_1["content"] if isinstance(section_1["content"], list) else [section_1["content"]]
                        for section in section_1_content:
                            match section["tag"]:
                                case "span":
                                    match section["data"]["name"]:
                                        # head word kana
                                        case "見出仮名":
                                            #! TODO FINISHED
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            reading = ""
                                            for inner_content in content:
                                                if isinstance(inner_content, str):
                                                    reading += inner_content
                                                elif inner_content.get("tag") == "span":
                                                    pass
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # orthography & spelling variations
                                        case "表記G":
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                if isinstance(inner_content, str):
                                                    if inner_content in ["〖", "【", "〗", "】"]:
                                                        pass
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "原語表記":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "標準表記":
                                                    ...
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # is personal name
                                        case "人名":
                                            #! TODO FINISHED
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                if inner_content == "◉":
                                                    is_personal_name = True
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # historical kana
                                        case "歴史仮名":
                                            #! TODO FINISHED
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                if isinstance(inner_content, str):
                                                    historical_kana = inner_content
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # accent group
                                        case "アクセントG":
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                if inner_content["tag"] == "span" and inner_content["data"]["name"] == "アクセント":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "複合アクセント":
                                                    ...
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # is geographical place name
                                        case "地名":
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                if inner_content == "◆":
                                                    is_geographical_place = True
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # phrase orthography
                                        case "句表記":
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                if isinstance(inner_content, str):
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "活用分節":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "ルビG":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "連語句活用分節":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "省略":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "言換え":
                                                    ...
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # original orthography groups
                                        case "原綴G":
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            original_orthography_group = {"原綴": list(), "原籍": list()}
                                            for inner_content in content:
                                                if inner_content in ["〕", "〔"]:
                                                    ...
                                                elif inner_content == ";":
                                                    ...
                                                elif inner_content in ["〖", "〗"]:
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "原綴":
                                                    original_orthography_group["原綴"].append(inner_content["content"])
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "原籍":
                                                    original_orthography_group["原籍"].append(inner_content["content"])
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # kanji headword group
                                        case "漢字見出G":
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                if inner_content in ["】","【"]:
                                                    ...
                                                elif inner_content == "・":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "漢字見出":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "別字体G":
                                                    ...
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        # abbreviation group
                                        case "略語G":
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                print(inner_content)
                                                if inner_content["tag"] == "span" and inner_content["data"]["name"] == "略語":
                                                    ...
                                                elif inner_content["tag"] == "span" and inner_content["data"]["name"] == "読みG":
                                                    ...
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                                        case _:
                                            raise InvalidDictDefinitionFormatError(logger, "")
                                case "ul":
                                    match section["data"]["name"]:
                                        # kanji sound / reading group
                                        case "漢字音G":
                                            ...
                                        case _:
                                            raise InvalidDictDefinitionFormatError(logger, "")
                                case _:
                                    raise InvalidDictDefinitionFormatError(logger, "")
                    else:
                        raise InvalidDictDefinitionFormatError(logger, "")

                    # section 2
                    if section_2["tag"] == "div" and section_2["data"]["name"] == "解説部":
                        section_2_content = section_2["content"] if isinstance(section_2["content"], list) else [section_2["content"]]
                        for section in section_2_content:
                            if section["tag"] == "div":
                                match section["data"]["name"]:
                                    # major sense / primary definition
                                    case "大語義":
                                        content = section["content"] if isinstance(section["content"], list) else [
                                            section["content"]]
                                        for inner_content in content:
                                            # semi major word sense
                                            if inner_content.get("data", {}).get("name") == "準大語義":
                                                ...
                                            # part of speech group
                                            elif inner_content.get("data", {}).get("name") == "品詞G":
                                                ...
                                            # classical / literary form
                                            elif inner_content.get("data", {}).get("name") == "文語形":
                                                ...
                                            # derivative group
                                            elif inner_content.get("data", {}).get("name") == "派生G":
                                                ...
                                            # supplementary explanation group
                                            elif inner_content.get("data", {}).get("name") == "補説G":
                                                ...
                                            # potential form
                                            elif inner_content.get("data", {}).get("name") == "可能形":
                                                ...
                                            # conjugation / inflection variation
                                            elif inner_content.get("data", {}).get("name") == "活用変化":
                                                ...
                                            # accent group
                                            elif inner_content.get("data", {}).get("name") == "アクセントG":
                                                ...
                                            # original orthography / spelling group
                                            elif inner_content.get("data", {}).get("name") == "原綴G":
                                                ...
                                            # definition / gloss text
                                            elif inner_content.get("data", {}).get("name") == "語釈":
                                                ...
                                            # cross - reference group
                                            elif inner_content.get("data", {}).get("name") == "参照G":
                                                ...
                                            # antonym group
                                            elif inner_content.get("data", {}).get("name") == "対義語G":
                                                ...
                                            elif inner_content.get("tag") == "span" and inner_content.get("content",
                                                                                                          {}).get(
                                                    "tag"):
                                                pass
                                            else:
                                                raise InvalidDictDefinitionFormatError(logger, inner_content)
                                    # supplementary explanation group
                                    case "補説G":
                                        content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                        for inner_content in content:
                                            if isinstance(inner_content, str):
                                                pass
                                            elif inner_content.get("tag") == "span" and inner_content["data"]["name"] == "補説":
                                                ...
                                            else:
                                                raise InvalidDictDefinitionFormatError(logger, inner_content)
                                    # idiomatic / collocation usage group
                                    case "慣用G":
                                        content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                        for inner_content in content:
                                            if isinstance(inner_content, list):
                                                ...
                                            elif isinstance(inner_content, str):
                                                ...
                                            elif inner_content["tag"] == "span" and isinstance(inner_content.get("content", {}), list):
                                                ...
                                            elif inner_content["tag"] == "span" and inner_content.get("content", {}).get("tag") == "img":
                                                ...
                                            elif inner_content.get("tag") == "span" and inner_content["data"]["name"] == "慣用subG":
                                                ...
                                            else:
                                                raise InvalidDictDefinitionFormatError(logger, inner_content)
                                    # differnt kanji, same reading
                                    case "異字同訓":
                                        content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                        for inner_content in content:
                                            if inner_content["tag"] == "span" and isinstance(inner_content.get("content"), list):
                                                ...
                                            elif inner_content["tag"] == "span" and inner_content.get("content", {}).get("tag") == "img":
                                                ...
                                            elif inner_content["tag"] == "div" and inner_content["data"]["name"] == "異字同訓解説":
                                                ...
                                            else:
                                                raise InvalidDictDefinitionFormatError(logger, inner_content)
                                    # derivative / etymology group
                                    case "派生G":
                                        content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                        for inner_content in content:
                                            if isinstance(inner_content, str):
                                                ...
                                            elif inner_content["tag"] == "span" and isinstance(inner_content.get("content", {}), list):
                                                ...
                                            elif inner_content["tag"] == "span" and inner_content.get("content", {}).get("tag") == "img":
                                                ...
                                            elif inner_content.get("tag") == "span" and inner_content["data"]["name"] == "派生語":
                                                ...
                                            else:
                                                raise InvalidDictDefinitionFormatError(logger, inner_content)
                                    # definition / glossary text
                                    case "語釈":
                                        content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                        for inner_content in content:
                                            if isinstance(inner_content, str):
                                                ...
                                            else:
                                                raise InvalidDictDefinitionFormatError(logger, inner_content)
                                    case _:
                                        raise InvalidDictDefinitionFormatError(logger, "")
                            elif section["tag"] == "span":
                                match section["data"]["name"]:
                                    # part of speech group
                                    case "品詞G":
                                        content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                        for inner_content in content:
                                            if inner_content.get("tag") == "span" and inner_content["data"]["name"] == "品詞subG":
                                                ...
                                            else:
                                                raise InvalidDictDefinitionFormatError(logger, inner_content)
                                    # cross - reference group
                                    case "参照G":
                                        if section.get('content') is None:
                                            pass
                                        else:
                                            content = section["content"] if isinstance(section["content"], list) else [section["content"]]
                                            for inner_content in content:
                                                if isinstance(inner_content, str):
                                                    ...
                                                elif inner_content.get("tag") == "span" and inner_content["data"]["name"] == "参照":
                                                    ...
                                                else:
                                                    raise InvalidDictDefinitionFormatError(logger, inner_content)
                            else:
                                raise InvalidDictDefinitionFormatError(logger, "")
                    else:
                        raise InvalidDictDefinitionFormatError(logger, "")
                else:
                    raise InvalidDictDefinitionFormatError(logger, "")
            elif isinstance(structured_contents, dict):
                ...

            else:
                raise InvalidDictDefinitionFormatError(logger, "")


"""
content = section["content"] if isinstance(section["content"], list) else [section["content"]]
for inner_content in content:
    print(inner_content)
    if not False:
        ...
    else:
        raise InvalidDictDefinitionFormatError(logger, inner_content)
"""

# endregion

class JapaneseDictionary():
    VALID_DICTIONARY_CLASSES = [JitendexYomitanParser, PixivLightParser, JMnedictParser, GiongoGitaigoJitenParser, YonJiJukugoNoHyakkaJitenParser, KotowazaKanyoukuNoHyakkaJitenParser]

    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import gc
        gc.collect()
        return False

    def create_dictionary_file(self):
        dictionary_entries: dict[str, list[RedirectEntry | DictionaryEntry]] = dict()

        now = time.time()

        for parser_object in self.VALID_DICTIONARY_CLASSES:
            with parser_object() as parser:
                data = parser.parse_dict()

                for key, value in data.items():
                    if key not in dictionary_entries:
                        dictionary_entries[key] = value
                    else:
                        dictionary_entries[key].extend(value)

        logger.info(f"Finished parsing all dictionaries in {time.time() - now:.2f} seconds.")
        logger.info(f"Dictionary entries: {len(dictionary_entries)}")

        serialized_map = {
            headword: [asdict(entry) for entry in entries_list]
            for headword, entries_list in dictionary_entries.items()
        }

        dicts_file = DICTS_DIR / "dict.json.gz"

        try:
            write_json_file(dicts_file, serialized_map, ["data"], indent=0, use_gzip=True)
        except Exception as e:
            logger.error("Failed to write dict.json file")
            logger.error(e)
            raise e

        logger.info(f"Successfully saved dictionary entries, size of library is: {dicts_file.stat().st_size / 1000000:.2f}MB")




if __name__ == "__main__":
    # with DaijirinDaiYonHanParser() as parser:
    #     grouped_dict_data = parser.parse_dict()

        # serialized_map = {
        #     headword: [asdict(entry) for entry in entries_list]
        #     for headword, entries_list in grouped_dict_data.items()
        # }
        #
        # write_json_file(DICTS_DIR / "temp.json", serialized_map, ["data"], indent=0, use_gzip=True)
    with JapaneseDictionary() as jd:
        jd.create_dictionary_file()