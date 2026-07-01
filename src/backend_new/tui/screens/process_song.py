import time
import threading
from pathlib import Path
from typing import Any, Generator
from textual import events, work, on
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, CenterMiddle, Container, HorizontalGroup, HorizontalScroll
from textual.widgets import Header, Footer, Input, DataTable, Label, Button, ContentSwitcher, Static, LoadingIndicator, \
    RichLog, Select
from textual.binding import Binding

from backend_new.extractors.downloader import Downloader
from backend_new.utils.constants import UIPromptRequest
from backend_new.utils.functions.filesystem import read_config, all_available_temp_json_files


class ProcessSong(Screen):
    DEFAULT_CSS = """
    #fullscreen {

    }

    #main_content_switcher {
        width: 100%;
        height: 100%;

        content-align: center middle;
        align: center middle;

        hatch: right $accent 10%;
    }

    #choose_json {
        width: 90%;
        height: auto;

        border: solid $secondary;
        border-title-align: center;
        border-title-style: bold;
        border-title-color: $primary;

        padding: 1 2;
    }

    #choose_json Select {
        padding: 1 0;
    }

    #choose_json Horizontal {
        width: 100%;
        height: auto;
        align: right middle;
    }
    
    #confirm_json {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+x", "app.pop_screen", "Exit Processing", priority=True)
    ]

    json_options: list[tuple[str, Path]] = list()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Container(id="fullscreen"):
            with ContentSwitcher(id="main_content_switcher", initial="choose_json"):
                with Vertical(id="choose_json"):
                    yield Label(id="select_json_header", content="Please choose which song to process")
                    yield Select(id="select_json", options=list())
                    with Horizontal():
                        yield Button(id="confirm_json", label="Next", variant="success")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#choose_json", Vertical).border_title = "Song Processing"
        self.update_json_select()

    @work(thread=True)
    def update_json_select(self) -> None:
        all_files = all_available_temp_json_files()
        self.json_options = [(file["name"], file["path"]) for file in all_files]

        self.update_select_json_widget()

    def update_select_json_widget(self) -> None:
        self.query_one("#select_json", Select).set_options(self.json_options)



        