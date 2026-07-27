import os
from typing import Any

from dotenv import set_key, load_dotenv
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Container, VerticalGroup, HorizontalGroup, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Label, Button, Switch, Checkbox, Input, Header, Footer, TabbedContent, TabPane

from engine.tui.modalscreens.full import SpotifyAuthenticateScreen
from engine.tui.modalscreens.interactive import UnsavedConfirmationModalScreen
from engine.tui.widgets.interactive import ConfigOption
from engine.utils.paths import ENV_FILE
from engine.utils.default.default_var import DEFAULT_CONFIG
from engine.utils.functions.filesystem import read_config, write_config


class DownloadMenu(Horizontal):
    DEFAULT_CSS = """
        #main_container {
        height: 100%;
        width: 100%;
        
        hatch: right $accent 10%;
        }
        
        #option_container {
            height: 100%;
            
            hatch: right $accent 10%;
        }
    
        .section_container {
            height: auto;
            border: solid $secondary;
            border-title-style: bold;
            border-title-color: $primary;
            
            margin: 0 1;
        }
        
        .option {
            height: auto;
            margin: 1 0;
        }
        
        .hor_option {
            height: auto;
            margin: 1 0;
            layout: horizontal;
        }
        
        .hor_option Label {
            align: left middle;
            content-align: left middle;
            
            width: 100%;
            height: 100%;
        }
        
        .option Label {
            margin: 0 1;
        }
        
        #spotify_query_display_settings, #youtube_query_display_settings {
            margin: 1 2;
        }
        
        #query_display_settings {
            hatch: right $accent 10%;
        }
        
        ConfigOption {
            height: auto;
            padding-top: 1;
        }
        
        .bottom_margin {
            margin-bottom: 1;
        }
        """

    config_file_data = None
    anything_changed = False

    class ReAuthSpotify(Message):
        def __init__(self, *args, **kwargs):
            super().__init__()

    def compose(self) -> ComposeResult:
        with Container(id="main_container"):
            # with Vertical(id="option_container"):
            with VerticalScroll(id="option_container"):
                with VerticalGroup(classes="section_container", id="query_extract_settings"):
                    yield ConfigOption(
                        "input_int",
                        "How many items to view at once when querying",
                        "query_view_limit",
                        json_keys=["downloader", "view_limit"],
                        enable_config_write=True,
                    )

                    yield ConfigOption(
                        "input_int",
                        "How many times to retry",
                        "query_retry_count",
                        json_keys=["downloader", "retry_count"],
                        enable_config_write=True,
                    )

                    yield ConfigOption(
                        "input_float",
                        "How time to wait for each retry (s)",
                        "query_retry_sleep",
                        json_keys=["downloader", "retry_sleep"],
                        enable_config_write=True,
                    )


                    yield ConfigOption(
                        "switch",
                        "Always choose first YouTube result when using current song",
                        "current_song_always_first_youtube_result",
                        json_keys=["downloader", "current_song_always_first_youtube_result"],
                        enable_config_write=True,
                    )

                    yield ConfigOption(
                        "switch",
                        "Always choose first YouTube result when querying",
                        "query_always_first_youtube_result",
                        json_keys=["downloader", "query_always_first_youtube_result"],
                        enable_config_write=True,
                        classes="bottom_margin"
                    )

                with HorizontalGroup(classes="section_container", id="query_display_settings"):
                    with VerticalGroup(classes="section_container", id="spotify_query_display_settings"):
                        yield ConfigOption(
                            "switch",
                            "Duration",
                            "spotify_display_duration",
                            json_keys=["spotify_downloader", "output_format", "duration"],
                            enable_config_write=True,
                        )

                        yield ConfigOption(
                            "switch",
                            "Album",
                            "spotify_display_album",
                            json_keys=["spotify_downloader", "output_format", "album"],
                            enable_config_write=True,
                        )

                        yield ConfigOption(
                            "switch",
                            "Popularity",
                            "spotify_display_popularity",
                            json_keys=["spotify_downloader", "output_format", "popularity"],
                            enable_config_write=True,
                            classes="bottom_margin"
                        )

                    with VerticalGroup(classes="section_container", id="youtube_query_display_settings"):
                        yield ConfigOption(
                            "switch",
                            "Duration",
                            "youtube_display_duration",
                            json_keys=["youtube_downloader", "output_format", "duration"],
                            enable_config_write=True,
                        )

                        yield ConfigOption(
                            "switch",
                            "Uploader",
                            "youtube_display_uploader",
                            json_keys=["youtube_downloader", "output_format", "uploader"],
                            enable_config_write=True,
                        )

                        yield ConfigOption(
                            "switch",
                            "View Count",
                            "youtube_display_view_count",
                            json_keys=["youtube_downloader", "output_format", "view_count"],
                            enable_config_write=True,
                        )

                        yield ConfigOption(
                            "switch",
                            "ID",
                            "youtube_display_id",
                            json_keys=["youtube_downloader", "output_format", "id"],
                            enable_config_write=True,
                            classes="bottom_margin"
                        )

                with HorizontalGroup(classes="section_container", id="spotify_settings"):
                    yield ConfigOption(
                        "switch",
                        "Authenticate Spotify Account",
                        "spotify_token",
                        json_keys=["spotify_downloader", "token"],
                        enable_config_write=True,
                        classes="bottom_margin"
                    )


    def _on_mount(self, event: events.Mount) -> None:
        with self.prevent(Input.Changed, Switch.Changed):
            self.auto_change = True
            self.query_one("#query_extract_settings", VerticalGroup).border_title = "Query & Extractor Settings"

            self.query_one("#query_display_settings", HorizontalGroup).border_title = "Information Shown while Querying"
            self.query_one("#spotify_query_display_settings", VerticalGroup).border_title = "Spotify"
            self.query_one("#youtube_query_display_settings", VerticalGroup).border_title = "Youtube"

            self.query_one("#spotify_settings", HorizontalGroup).border_title = "Spotify"

            self.config_file_data = read_config()



    @on(ConfigOption.Changed, "#spotify_token")
    def handle_spotify_token(self, event: ConfigOption.Changed) -> None:
        write_config(self.query_one("#spotify_token", ConfigOption).value, ["spotify_downloader", "token"])
        self.config_file_data["spotify_downloader"]["token"] = event.value
        self.app.read_config_worker(False)
        if event.value:
            self.app.push_screen(SpotifyAuthenticateScreen(), callback=self.handle_auth_result)

    def handle_auth_result(self, result: Any) -> None:
        if not result:
            self.notify("failed")
            with self.prevent(Switch.Changed):
                self.query_one("#spotify_token", ConfigOption).value = False
            self.config_file_data["spotify_downloader"]["token"] = False
            write_config(False, ["spotify_downloader", "token"])
            self.app.read_config_worker(False)
        else:
            self.config_file_data["spotify_downloader"]["token"] = result
            self.post_message(self.ReAuthSpotify())


class ProcessesMenu(Horizontal):
    DEFAULT_CSS = """
    #main_container {
        height: 100%;
        width: 100%;
        
        hatch: right $accent 10%;
    }
    
    .section_container {
        height: auto;
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
    }
    
    .option_sections {
        padding: 0 1;
        align: center top;
        
        hatch: right $accent 10%;
        
        height: auto;
    }
    
    ConfigOption {
        height: auto
    }
    """

    def __init__(self, *args, main_container_height: str = "100%", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.chosen_height = main_container_height

    def compose(self) -> ComposeResult:
        with Container(id="main_container"):
            with Container(classes="option_sections"):
                with Container(classes="section_container", id="skip_processes"):
                    # yield Checkbox("Download Song", id="download_song_checkbox")

                    yield ConfigOption(
                        "checkbox",
                        "Genius Metadata",
                        "genius_metadata_checkbox",
                        json_keys=["skip_processes", "genius_metadata"],
                        enable_config_write=True
                    )
                    yield ConfigOption(
                        "checkbox",
                        "Separate Stems",
                        "separate_stems_checkbox",
                        json_keys=["skip_processes", "vocal_separation"],
                        enable_config_write=True
                    )
                    yield ConfigOption(
                        "checkbox",
                        "Split and Tag lyrics",
                        "split_and_tag_checkbox",
                        json_keys=["skip_processes", "split_and_tag"],
                        enable_config_write=True
                    )
                    yield ConfigOption(
                        "checkbox",
                        "Translate Lyrics",
                        "translate_lyrics_checkbox",
                        json_keys=["skip_processes", "translate_lyrics"],
                        enable_config_write=True
                    )


    def _on_mount(self, event: events.Mount) -> None:
        skip_processes = self.query_one("#skip_processes", Container)
        skip_processes.border_title = "Skip Processes"

        self.query_one("#main_container", Container).styles.height = self.chosen_height


class EnvironmentVariablesMenu(Horizontal):
    DEFAULT_CSS = """
    #main_container {
        height: 100%;
        width: 100%;
    }
    
    .section_container {
        height: auto;
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
    }
    
    .option_sections {
        padding: 0 1;
        align: center top;
        
        hatch: right $accent 10%;
        
        height: 1fr;
    }
    
    #buttons {
        align: right middle;
        content-align: right middle;
        margin: 1 0;
        padding: 0 1;
        
        hatch: right $accent 10%;
        
        dock: bottom;
        height: 3;
    }
    
    .option {
        height: auto;
        margin: 1 0;
    }
    
    .option Label {
        margin: 0 1;
    }
    """

    hide_keys = True
    anything_changed = False

    spot_cli_id = None
    spot_cli_sec = None
    spot_redir_uri = None
    gen_acc_tok = None

    def compose(self) -> ComposeResult:
        with Container(id="main_container"):
            with VerticalGroup(classes="option_sections"):
                with Container(classes="section_container", id="spotify"):
                    with Container(classes="option"):
                        yield Label("SPOTIFY_CLIENT_ID")
                        yield Input(placeholder="SPOTIFY_CLIENT_ID", id="in1")

                    with Container(classes="option"):
                        yield Label("SPOTIFY_CLIENT_SECRET")
                        yield Input(placeholder="SPOTIFY_CLIENT_SECRET", id="in2")

                    with Container(classes="option"):
                        yield Label("SPOTIFY_REDIRECT_URI")
                        yield Input(placeholder="SPOTIFY_REDIRECT_URI", id="in3")
                with Container(classes="section_container", id="genius"):
                    with Container(classes="option"):
                        yield Label("GENIUS_ACCESS_TOKEN")
                        yield Input(placeholder="GENIUS_ACCESS_TOKEN", id="in4")

                with HorizontalGroup(id="buttons"):
                    yield Button(variant="warning", id="show", label="Show")
                    yield Button(variant="success", id="save", label="Save")


    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#spotify", Container).border_title = "Spotify"
        self.query_one("#genius", Container).border_title = "Genius"

        for widget in self.query(Input):
            widget.password = self.hide_keys

        self.write_default_values()

        self.anything_changed = False

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "in1":
            self.spot_cli_id = event.input.value
            self.anything_changed = True
        elif event.input.id == "in2":
            self.anything_changed = True
            self.spot_cli_sec = event.input.value
        elif event.input.id == "in3":
            self.spot_redir_uri = event.input.value
            self.anything_changed = True
        elif event.input.id == "in4":
            self.gen_acc_tok = event.input.value
            self.anything_changed = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show":
            self.hide_keys = False if self.hide_keys else True

            for widget in self.query(Input):
                widget.password = self.hide_keys
        elif event.button.id == "save":
            self.save_config()
            self.anything_changed = False

    def save_config(self) -> None:
        set_key(ENV_FILE, "SPOTIFY_CLIENT_ID", self.spot_cli_id, quote_mode="never")
        set_key(ENV_FILE, "SPOTIFY_CLIENT_SECRET", self.spot_cli_sec, quote_mode="never")
        set_key(ENV_FILE, "SPOTIFY_REDIRECT_URI", self.spot_redir_uri, quote_mode="never")
        set_key(ENV_FILE, "GENIUS_ACCESS_TOKEN", self.gen_acc_tok, quote_mode="never")

    def write_default_values(self):
        load_dotenv(ENV_FILE)

        self.spot_cli_id = os.getenv("SPOTIFY_CLIENT_ID", "")
        self.spot_cli_sec = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        self.spot_redir_uri = os.getenv("SPOTIFY_REDIRECT_URI", "")
        self.gen_acc_tok = os.getenv("GENIUS_ACCESS_TOKEN", "")

        with self.prevent(Input.Changed):
            self.query_one("#in1", Input).value = self.spot_cli_id
            self.query_one("#in2", Input).value = self.spot_cli_sec
            self.query_one("#in3", Input).value = self.spot_redir_uri
            self.query_one("#in4", Input).value = self.gen_acc_tok

    def pane_switch_handler(self, ready_to_move_callback) -> None:
        if self.anything_changed:
            self.app.push_screen(
                UnsavedConfirmationModalScreen(),
                callback=lambda choice: self.save_screen_handler(choice, ready_to_move_callback)
            )
        else:
            ready_to_move_callback(False)

    def save_screen_handler(self, value: str, ready_to_move_callback) -> None:
        if value == "save":
            self.save_config()
            ready_to_move_callback(True)
        elif value == "discard":
            self.write_default_values()
            self.anything_changed = False
            ready_to_move_callback(True)
        elif value == "cancel":
            ready_to_move_callback(False)


class ConfigMenu(Screen):
    BINDINGS = [
        Binding("ctrl+x", "app.pop_screen", "Exit Menu", priority=True)
    ]

    _switching_internally = False
    current_pane_id = "processes"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with TabbedContent():
            with TabPane("Processes", id="processes"):
                yield ProcessesMenu()
            with TabPane("Downloader", id="download"):
                yield DownloadMenu()
            with TabPane(".env", id="env"):
                yield EnvironmentVariablesMenu()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if self._switching_internally:
            return

        if event.pane.id == "processes":
            ...
        elif event.pane.id == "download":
            ...
        elif event.pane.id == "env":
            ...

        if self.current_pane_id == "processes" and event.pane.id != "download":
            ...
        elif self.current_pane_id == "download" and event.pane.id != "env":
            ...
        elif self.current_pane_id == "env" and event.pane.id != "env":
            current_widget = self.query_one(EnvironmentVariablesMenu)
            if current_widget.anything_changed:
                self._switching_internally = True
                event.tabbed_content.active = "env"
                self._switching_internally = False

                def handle_navigation(allowed_to_move: bool):
                    if allowed_to_move:
                        self._switching_internally = True
                        event.tabbed_content.active = event.pane.id
                        self._switching_internally = False

                        self.current_pane_id = event.pane.id

                current_widget.pane_switch_handler(handle_navigation)
                return

        self.current_pane_id = event.pane.id
