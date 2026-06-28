import time
import threading
from typing import Any, Generator
from textual import events, work, on
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, CenterMiddle, Container, HorizontalGroup, HorizontalScroll
from textual.widgets import Header, Footer, Input, DataTable, Label, Button, ContentSwitcher, Static, LoadingIndicator, \
    RichLog
from textual.binding import Binding

from backend_new.extractors.downloader import Downloader
from backend_new.utils.constants import UIPromptRequest
from backend_new.utils.helper_funcs import read_config

class ProcessSong(Screen):
    DEFAULT_CSS = """
    #fullscreen {
        hatch: right $accent 10%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Container(id="fullscreen"):
            ...
