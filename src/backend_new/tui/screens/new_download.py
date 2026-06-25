import time
from typing import Any, Generator
from textual import events, work, on
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, CenterMiddle, Container, HorizontalGroup, HorizontalScroll
from textual.widgets import Header, Footer, Input, DataTable, Label, Button, ContentSwitcher, Static, LoadingIndicator
from textual.binding import Binding

from backend_new.extractors.downloader import Downloader
from backend_new.utils.constants import UIPromptRequest
from backend_new.utils.helper_funcs import read_config


class DownloadScreen(Screen):
    BINDINGS = [
        Binding("ctrl+x", "app.pop_screen", "Exit Download", priority=True)
    ]

    DEFAULT_CSS = """
    #main_window {
        height: auto;
        width: auto;
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
    
    #input_pane {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-align: center;
        border-title-style: bold;
        padding: 1 2;
        
    
        height: auto;
    }
    
    #input_box {
        width: 1fr;
    }
    
    #submit_input {
        width: auto;
    }
    
    #select_pane {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-align: center;
        border-title-style: bold;
        padding: 1 2;
        
    
        height: auto;
    }
    
    #input_container {
        width: 100%;
        height: auto;
    }
    
    .horizontal_scroll {
        width: 100%;
        height: auto;
    }
    
    #input_table {
        height: auto;
    }
    """

    pipeline = None
    next_ui_response = None
    has_response = False
    config_data = read_config()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Container(id="fullscreen"):
            with CenterMiddle(id="main_window"):
                with ContentSwitcher(id="main_content_switcher", initial="loading"):
                    with Vertical(id="loading"):
                        yield Static("Initializing Systems [blink]_[/]")

                    with Container(id="loading_screen"):
                        yield LoadingIndicator()

                    with Vertical(id="input_pane"):
                        yield Label(id="input_label")
                        with HorizontalGroup(id="input_container"):
                            yield Input(id="input_box")
                            yield Button("Submit", id="submit_input", variant="success")

                    with Vertical(id="select_pane"):
                        with HorizontalScroll(classes="horizontal_scroll"):
                            yield DataTable(
                                cursor_type="row",
                                zebra_stripes=True,
                                id="input_table"
                            )


    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#input_pane", Vertical).border_title = "New Download"
        self.query_one("#select_pane", Vertical).border_title = "New Download"

        self.run_downloader_pipeline()

    @work(thread=True)
    def run_downloader_pipeline(self) -> None:
        dl = Downloader()
        self.pipeline = dl.download_song()

        try:
            prompt_request = next(self.pipeline)

            while True:
                user_answer = self.app.call_from_thread(self.update_ui_for_prompt, prompt_request)
                self._wait_for_ui_response()
                prompt_request = self.pipeline.send(self.next_ui_response)
        except StopIteration:
            ...

    @on(Button.Pressed, "#submit_input")
    def handle_input_submit(self) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)
        switcher.current = "loading_screen"

        val = {"value": self.query_one("#input_box", Input).value}
        self.next_ui_response = val
        self.has_response = True

    @on(Input.Submitted, "#input_box")
    def handle_submit_input(self) -> None:
        self.handle_input_submit()

    def update_ui_for_prompt(self, request: UIPromptRequest) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)

        match request.type:
            case "input":
                input_widget = self.query_one("#input_box", Input)
                input_label = self.query_one("#input_label", Label)

                input_label.content = request.message
                input_widget.placeholder = request.placeholder

                switcher.current = "input_pane"
            case "select":
                data_table_widget = self.query_one("#input_table", DataTable)

                if request.sub_type == "spotify":
                    table_rows = [["Title", "Artist"]]
                    if self.config_data["spotify_downloader"]["output_format"]["duration"]: table_rows[0].append("Duration")
                    if self.config_data["spotify_downloader"]["output_format"]["album"]: table_rows[0].append("Album")
                    if self.config_data["spotify_downloader"]["output_format"]["popularity"]: table_rows[0].append("Popularity")

                    for track in request.choices:
                        if track["type"] == "__option__":
                            holding = [track["title"], track["artist"]]

                            if self.config_data["spotify_downloader"]["output_format"]["duration"]: holding.append(track["duration"])
                            if self.config_data["spotify_downloader"]["output_format"]["album"]: holding.append(track["album"])
                            if self.config_data["spotify_downloader"]["output_format"]["popularity"]: holding.append(track["relevance"])

                            table_rows.append(holding)
                        elif track["type"] == "__nav__":
                            ...

                    data_table_widget.add_columns(*table_rows[0])
                    data_table_widget.add_rows(table_rows[1:])

                switcher.current = "select_pane"


    def _wait_for_ui_response(self):
        self.has_response = False
        while not self.has_response:
            time.sleep(0.05)