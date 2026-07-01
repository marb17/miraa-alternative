import time
import threading
from typing import Any, Generator

from spotipy import SpotifyException
from textual import events, work, on
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, CenterMiddle, Container, HorizontalGroup, HorizontalScroll
from textual.widgets import Header, Footer, Input, DataTable, Label, Button, ContentSwitcher, Static, LoadingIndicator, \
    RichLog
from textual.binding import Binding
from yt_dlp import DownloadError

from backend_new.core.workflow import WorkflowManager
from backend_new.extractors.downloader import Downloader
from backend_new.tui.widgets.interactive import InputSubmit
from backend_new.tui.widgets.static import SpotifyCurrentlyPlayingWidget
from backend_new.utils.classes.dataclasses import UIPromptRequest
from backend_new.utils.functions.filesystem import read_config


class DownloadScreen(Screen):
    BINDINGS = [
        Binding("ctrl+x", "self_dismiss(False)", "Exit Download", priority=True)
    ]

    DEFAULT_CSS = """
    #fullscreen {
        hatch: right $accent 10%;
    }
    
    #main_window {
        height: auto;
        width: auto;
    }
    
    #main_content_switcher {
        height: auto;
        width: auto;
        hatch: right $accent 10%;
    }
    
    InputSubmit {
        height: auto;
        padding: 1 2 1 1;
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
        hatch: right $accent 10%;
        height: auto;
        margin: 0 2;
    }
    
    #input_query_widget {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-align: center;
        border-title-style: bold;
    
        height: auto;
    }
    
    #current_playing_widget {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-align: center;
        border-title-style: bold;
    
        height: auto;
    }
    
    #current_playing_widget SpotifyCurrentlyPlayingWidget {
        height: auto;
        padding: 1 2;
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
    
    #nav_buttons {
        width: 100%;
        
        content-align: right middle;
        align: right middle;
    }
    
    #nav_buttons Button {
        margin: 0 1;
    }
        
    #info_rich_log {
        margin: 1 2;
    }
    
    #finished, #already_exists, #error_message {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-align: center;
        border-title-style: bold;
        padding: 1 2;
        
        height: auto;
        width: auto;
    }
    
    #finished Static {
        width: auto
    }
    
    #already_exists Static {
        width: auto
    }
    
    #error_message Static {
        width: auto
    }
    """

    pipeline = None
    next_ui_response = None
    config_data = None

    ui_ready_event = threading.Event()

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

                    with Container(id="info_screen"):
                        yield Static(id="info_static")
                        yield RichLog(id="info_rich_log")

                    with Vertical(id="input_pane"):
                        with Container(id="current_playing_widget"):
                            yield SpotifyCurrentlyPlayingWidget()
                        with Container(id="input_query_widget"):
                            yield InputSubmit(id="input_widget", extra_buttons=[Button("Current Song", id="current_playing_song_button", variant="primary", disabled=not self.app.use_spotify_token)])

                    with Vertical(id="select_pane"):
                        yield Label(id="input_table_header")
                        with HorizontalScroll(classes="horizontal_scroll"):
                            yield DataTable(
                                cursor_type="row",
                                zebra_stripes=True,
                                id="input_table"
                            )

                        yield Label(id="table_page_number")

                        with HorizontalGroup(id="nav_buttons"):
                            yield Button(id="__select__", variant="success", label="Select")
                            yield Button(id="__new__", variant="warning", label="New")
                            yield Button(id="__prev__", variant="primary", label="Previous")
                            yield Button(id="__next__", variant="primary", label="Next")

                    with Vertical(id="finished"):
                        yield Static(id="finished_text", content="Finished downloading, press any key to continue[blink]_[/]")

                    with Vertical(id="already_exists"):
                        yield Static(id="already_exists_text", content="Data already exists, skipping, press any key to continue[blink]_[/]")

                    with Vertical(id="error_message"):
                        yield Static("An error has occurred, try again[blink]_[/]\n")
                        yield Static(id="error_message_static")



    def _on_mount(self, event: events.Mount) -> None:
        self.config_data = read_config()

        self.query_one("#current_playing_widget", Container).border_title = "Currently Playing"
        self.query_one("#input_query_widget", Container).border_title = "New Download"
        self.query_one("#select_pane", Vertical).border_title = "New Download"

        self.query_one(SpotifyCurrentlyPlayingWidget).action_authenticate()

        self.run_downloader_pipeline()

    @work(thread=True)
    def run_downloader_pipeline(self) -> None:
        with WorkflowManager() as manager:
            self.pipeline = manager.download_new_song()

            try:
                prompt_request = next(self.pipeline)

                while True:
                    self.ui_ready_event.clear()
                    user_answer = self.app.call_from_thread(self.update_ui_for_prompt, prompt_request)
                    self.ui_ready_event.wait()
                    prompt_request = self.pipeline.send(self.next_ui_response)
            except StopIteration as e:
                if e.value is True:
                    self.app.call_from_thread(self.update_ui_for_finished)
                elif isinstance(e.value, str):
                    self.app.call_from_thread(self.update_ui_for_already_exists)
            except (SpotifyException, DownloadError) as e:
                self.app.call_from_thread(self.update_ui_for_error, str(e))


    def on_button_pressed(self, event: Button.Pressed) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)

        if event.button.id == "__new__":
            switcher.current = "loading_screen"

            val = {"value": "__new__"}
            self.next_ui_response = val
            self.ui_ready_event.set()
        elif event.button.id == "__prev__":
            switcher.current = "loading_screen"

            val = {"value": "__prev__"}
            self.next_ui_response = val
            self.ui_ready_event.set()
        elif event.button.id == "__next__":
            switcher.current = "loading_screen"

            val = {"value": "__next__"}
            self.next_ui_response = val
            self.ui_ready_event.set()

    @on(InputSubmit.Submitted, "#input_widget")
    def handle_input_submit(self, event: InputSubmit.Submitted) -> None:
        val = {"value": self.query_one("#input_widget", InputSubmit).value.strip(),
               "first_yt": read_config()["downloader"]["query_always_first_youtube_result"]}

        if event.triggered_by == "submit":
            if val["value"]:
                switcher = self.query_one("#main_content_switcher", ContentSwitcher)
                switcher.current = "loading_screen"

                self.next_ui_response = val
                self.ui_ready_event.set()
            else:
                self.notify("Please enter a query.", severity="warning")
                return
        elif event.triggered_by == "current_playing_song_button":
            if not self.query_one(SpotifyCurrentlyPlayingWidget).song_available:
                self.notify("No song is playing on spotify.", severity="warning")
                return

            switcher = self.query_one("#main_content_switcher", ContentSwitcher)
            switcher.current = "loading_screen"

            self.next_ui_response = {"value": "__current_song__",
                                     "first_yt": read_config()["downloader"]["current_song_always_first_youtube_result"]}
            self.ui_ready_event.set()

    @on(DataTable.RowSelected, "#input_table")
    def handle_table_select(self) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)
        switcher.current = "loading_screen"

        val = {"value": self.query_one("#input_table", DataTable).cursor_row}
        self.next_ui_response = val
        self.ui_ready_event.set()

    @on(Button.Pressed, "#__select__")
    def handle_select_pressed(self) -> None:
        self.handle_table_select()

    def _on_key(self, event: events.Key) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)
        if switcher.current in ["finished", "already_exists", "error_message"]:
            self.action_self_dismiss(True)

    def update_ui_for_finished(self) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)
        switcher.current = "finished"

    def update_ui_for_already_exists(self) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)
        switcher.current = "already_exists"

    def update_ui_for_error(self, message: str) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)
        switcher.current = "error_message"

        self.query_one("#error_message_static", Static).update(message)

    def action_self_dismiss(self, value: Any) -> None:
        self.dismiss(value)

    def update_ui_for_prompt(self, request: UIPromptRequest) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)

        new_button = self.query_one("#__new__", Button)
        next_button = self.query_one("#__next__", Button)
        prev_button = self.query_one("#__prev__", Button)

        for button in [new_button, next_button, prev_button]:
            button.display = False

        match request.type:
            case "input":
                input_widget = self.query_one("#input_widget", InputSubmit)

                input_widget.update_prompt(placeholder=request.placeholder,
                                           label=request.message,
                                           )

                switcher.current = "input_pane"

                input_widget.focus()

            case "select":
                data_table_widget = self.query_one("#input_table", DataTable)
                data_table_widget.clear(columns=True)

                data_table_header = self.query_one("#input_table_header", Label)
                data_table_header.content = request.message

                data_table_page = self.query_one("#table_page_number", Label)

                if request.sub_type == "spotify":
                    data_table_page.display = True
                    data_table_page.content = f"Page: {request.extra_info["page"]}"

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
                            match track["value"]:
                                case "__new__": new_button.display = True
                                case "__next__": next_button.display = True
                                case "__prev__": prev_button.display = True

                    data_table_widget.add_columns(*table_rows[0])
                    data_table_widget.add_rows(table_rows[1:])
                elif request.sub_type == "youtube":
                    data_table_page.display = True
                    data_table_page.content = ''

                    table_rows = [["Title"]]
                    if self.config_data["youtube_downloader"]["output_format"]["uploader"]: table_rows[0].append("Uploader")
                    if self.config_data["youtube_downloader"]["output_format"]["duration"]: table_rows[0].append("Duration")
                    if self.config_data["youtube_downloader"]["output_format"]["view_count"]: table_rows[0].append("View Count")
                    if self.config_data["youtube_downloader"]["output_format"]["id"]: table_rows[0].append("ID")

                    for track in request.choices:
                        if track["type"] == "__option__":
                            holding = [track["title"]]

                            if self.config_data["youtube_downloader"]["output_format"]["uploader"]: holding.append(track["uploader"])
                            if self.config_data["youtube_downloader"]["output_format"]["duration"]: holding.append(track["duration"])
                            if self.config_data["youtube_downloader"]["output_format"]["view_count"]: holding.append(track["view_count"])
                            if self.config_data["youtube_downloader"]["output_format"]["id"]: holding.append(track["id"])

                            table_rows.append(holding)
                        elif track["type"] == "__nav__":
                            # match track["value"]:
                            #     case "__new__": new_button.display = True
                            pass

                    data_table_widget.add_columns(*table_rows[0])
                    data_table_widget.add_rows(table_rows[1:])

                switcher.current = "select_pane"

                data_table_widget.focus()

            case "info":
                info_widget = self.query_one("#info_static", Static)
                info_widget.content = request.message

                switcher.current = "info_screen"

                self.ui_ready_event.set()

            case "log":
                rich_log_widget = self.query_one("#info_rich_log", RichLog)
                rich_log_widget.write(request.message)
                self.ui_ready_event.set()
