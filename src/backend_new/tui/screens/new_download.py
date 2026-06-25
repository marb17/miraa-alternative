from typing import Any, Generator
from textual import events, work, on
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, CenterMiddle, Container, HorizontalGroup
from textual.widgets import Header, Footer, Input, OptionList, Label, Button, ContentSwitcher, Static
from textual.binding import Binding

from backend_new.extractors.downloader import Downloader

class DownloadScreen(Screen):
    BINDINGS = [
        Binding("ctrl+x", "app.pop_screen", "Exit Download", priority=True)
    ]

    DEFAULT_CSS = """
    #main_window {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-align: center;
        border-title-style: bold;
        
        height: auto;
        width: auto;
        
        padding: 1 2;
    }
    
    #main_content_switcher {
        height: auto;
        width: auto;
    }
    
    #fullscreen {
        align: center middle;
        content-align: center middle;
        
        height: 100%;
        width: 100%;
    }
    
    #loading {
        height: auto;
        width: auto;
    }
    
    #loading Static {
        height: auto;
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Container(id="fullscreen"):
            with CenterMiddle(id="main_window"):
                with ContentSwitcher(id="main_content_switcher", initial="loading"):
                    with Vertical(id="loading"):
                        yield Static("Initializing Systems [blink]_[/]")

                    with Vertical(id="input_pane"):
                        with HorizontalGroup():
                            yield Input()
                            yield Button("Submit")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#main_window", CenterMiddle).border_title = "New Download"

    @work(thread=True)
    def run_downloader_pipeline(self) -> None:
        dl = Downloader()
        pipeline = dl.download_song()

        try:
            ...
        except StopIteration:
            ...
