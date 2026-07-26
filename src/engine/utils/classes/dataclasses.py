from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Any


@dataclass
class SongContext:
    json_song_data: dict
    json_file_path: Path


@dataclass
class UIPromptRequest:
    type: Literal["select", "input", "confirm", "info", "log", "hidden_request"]
    message: Any
    sub_type: Any = None
    choices: list[Any] | None = None
    persistent_choices: list[Any] | None = None
    default: Any = None
    password: bool = False
    placeholder: str = ""
    extra_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioSeparatorModel:
    name: str
    type: str
    rename_order: list[str]
    gain: float | int = 0.0


@dataclass
class ExampleSentence:
    lang: str # language of the example sentence
    sentence: str # the example sentence itself


@dataclass
class RawYomitanEntry:
    term: str
    reading: str
    definition_tags: str | None
    deinflection_rules: str
    popularity_score: int
    definitions: list[str | dict[str, Any]]
    sequence_number: int
    term_tags: str


@dataclass
class DefinitionSense:
    sense_number: int | None = None
    parts_of_speech: list[str] = field(default_factory=list) # all parts of speech
    glossaries: list[str | list[str]] = field(default_factory=list) # all definitions
    examples: list[dict[str, str]] = field(default_factory=list) # example sentences [{"en": "..."}, {"jp": "..."}]
    series: list[str] = field(default_factory=list) # where the word is derived from, like a new word e.g. from Harry Potter


ALLOWED_EXTRA_INFO_KEYS = Literal["synonyms", "synonym_info", "similar_words", "extra_info", "see_also", "links"]


@dataclass
class DictionaryEntry:
    dictionary: str # what dictionary is this entry from
    word: str # the word itself
    reading: str # how its read
    senses: list[DefinitionSense] = field(default_factory=list) # all information
    alternative_forms: list[str] = field(default_factory=list) # alt forms, different readings
    extra_info: defaultdict[ALLOWED_EXTRA_INFO_KEYS, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )


@dataclass
class RedirectEntry:
    dictionary: str
    word: str
    redirect_to: str
    primary_reading: str | None = None


@dataclass
class WordEntry:
    word: str
    entries: list[DictionaryEntry] = field(default_factory=list)
