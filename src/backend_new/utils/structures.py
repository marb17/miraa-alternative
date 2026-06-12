from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#===================================================
#       DATACLASSES
#===================================================

# SONG CONTEXT
@dataclass
class SongContext:
    json_song_data: dict
    json_file_path: Path

# YOMITAN PARSER
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
    glossaries: list[str] = field(default_factory=list) # all definitions
    examples: list[dict[str, str]] = field(default_factory=list) # example sentences [{"en": "..."}, {"jp": "..."}]

@dataclass
class DictionaryEntry:
    dictionary: str # what dictionary is this entry from
    word: str # the word itself
    reading: str # how its read
    senses: list[DefinitionSense] = field(default_factory=list) # all information
    alternative_forms: list[str] = field(default_factory=list) # alt forms