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
