import os

from dotenv import set_key, load_dotenv
from textual import events, containers
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import CenterMiddle, Horizontal, Vertical, Container, VerticalGroup, HorizontalGroup
from textual.screen import ModalScreen, Screen
from textual.widgets import Label, Button, Switch, Checkbox, Input, Header, Footer, TabbedContent, TabPane

from backend_new.utils.constants import ENV_FILE, DEFAULT_CONFIG
from backend_new.utils.helper_funcs import read_config, write_config


class SaveConfirmationModal(ModalScreen):
    DEFAULT_CSS = """
    #dialog_card {
        width: auto; 
        height: auto;
        
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
        border-title-align: center;
    }
    
    #dialog_msg {
        width: 100%;
        margin: 1 0;
        text-align: center;
    }
    
    #dialog_buttons {
        height: auto;
        width: auto;
        
        margin: 0 2 1 2;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.styles.align = ("center", "middle")

    def compose(self) -> ComposeResult:
        with CenterMiddle(id="dialog_card"):
            yield Label("⚠️ You have unsaved changes!\nWould you like to save before switching?", id="dialog_msg")
            with Horizontal(id="dialog_buttons"):
                yield Button("Save", variant="success", id="modal_save")
                yield Button("Discard", variant="error", id="modal_discard")
                yield Button("Cancel", variant="default", id="modal_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_save":
            self.dismiss("save")
        elif event.button.id == "modal_discard":
            self.dismiss("discard")
        elif event.button.id == "modal_cancel":
            self.dismiss("cancel")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#dialog_card", CenterMiddle).border_title = "Unsaved Changes"


class DownloadMenu(Horizontal):
    DEFAULT_CSS = """
        #main_container {
        height: 100%;
        width: 100%;
        
        hatch: right $accent 10%;
        }
        
        #option_container {
            height: auto;
            
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
        """

    config_file_data = None
    anything_changed = False

    def compose(self) -> ComposeResult:
        with Container(id="main_container"):
            with Vertical(id="option_container"):
                with VerticalGroup(classes="section_container", id="query_extract_settings"):
                    with Container(classes="option"):
                        yield Label("How many items to view at once when querying")
                        yield Input(id="query_view_limit", placeholder="10", type="integer")

                    with Container(classes="option"):
                        yield Label("How many times to retry")
                        yield Input(id="query_retry_count", placeholder="3", type="integer")

                    with Container(classes="option"):
                        yield Label("How long to wait for each retry (s)")
                        yield Input(id="query_retry_sleep", placeholder="5.0", type="number")

                with HorizontalGroup(classes="section_container", id="query_display_settings"):
                    with VerticalGroup(classes="section_container", id="spotify_query_display_settings"):
                        with Container(classes="hor_option"):
                            yield Switch(id="spotify_display_duration")
                            yield Label("Duration")

                        with Container(classes="hor_option"):
                            yield Switch(id="spotify_display_album")
                            yield Label("Album")

                        with Container(classes="hor_option"):
                            yield Switch(id="spotify_display_popularity")
                            yield Label("Popularity")

                    with VerticalGroup(classes="section_container", id="youtube_query_display_settings"):
                        with Container(classes="hor_option"):
                            yield Switch(id="youtube_display_duration")
                            yield Label("Duration")

                        with Container(classes="hor_option"):
                            yield Switch(id="youtube_display_uploader")
                            yield Label("Uploader")

                        with Container(classes="hor_option"):
                            yield Switch(id="youtube_display_view_count")
                            yield Label("View Count")

                        with Container(classes="hor_option"):
                            yield Switch(id="youtube_display_id")
                            yield Label("ID")


    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#query_extract_settings", VerticalGroup).border_title = "Query & Extractor Settings"

        self.query_one("#query_display_settings", HorizontalGroup).border_title = "Information Shown while Querying"
        self.query_one("#spotify_query_display_settings", VerticalGroup).border_title = "Spotify"
        self.query_one("#youtube_query_display_settings", VerticalGroup).border_title = "Youtube"

        self.config_file_data = read_config()

        self.query_one("#query_view_limit", Input).value = str(self.config_file_data["downloader"]["view_limit"])
        self.query_one("#query_retry_count", Input).value = str(self.config_file_data["downloader"]["retry_count"])
        self.query_one("#query_retry_sleep", Input).value = str(self.config_file_data["downloader"]["retry_sleep"])

        self.query_one("#spotify_display_duration", Switch).value = self.config_file_data["spotify_downloader"]["output_format"]["duration"]
        self.query_one("#spotify_display_album", Switch).value = self.config_file_data["spotify_downloader"]["output_format"]["album"]
        self.query_one("#spotify_display_popularity", Switch).value = self.config_file_data["spotify_downloader"]["output_format"]["popularity"]

        self.query_one("#youtube_display_duration", Switch).value = self.config_file_data["youtube_downloader"]["output_format"]["duration"]
        self.query_one("#youtube_display_uploader", Switch).value = self.config_file_data["youtube_downloader"]["output_format"]["uploader"]
        self.query_one("#youtube_display_view_count", Switch).value = self.config_file_data["youtube_downloader"]["output_format"]["view_count"]
        self.query_one("#youtube_display_id", Switch).value = self.config_file_data["youtube_downloader"]["output_format"]["id"]

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "query_view_limit":
            if self.query_one("#query_view_limit", Input).value == '':
                value = DEFAULT_CONFIG["downloader"]["view_limit"]
            else:
                value = int(self.query_one("#query_view_limit", Input).value)
            write_config(value, ["downloader", "view_limit"])
        elif event.input.id == "query_retry_count":
            if self.query_one("#query_retry_count", Input).value == '':
                value = DEFAULT_CONFIG["downloader"]["retry_count"]
            else:
                value = int(self.query_one("#query_retry_count", Input).value)
            write_config(value, ["downloader", "retry_count"])
        elif event.input.id == "query_retry_sleep":
            if self.query_one("#query_retry_sleep", Input).value == '':
                value = DEFAULT_CONFIG["downloader"]["retry_sleep"]
            else:
                value = float(self.query_one("#query_retry_sleep", Input).value)
            write_config(value, ["downloader", "retry_sleep"])

    def on_switch_changed(self, event: Switch.Changed):
        if event.switch.id == "spotify_display_duration":
            write_config(self.query_one("#spotify_display_duration", Switch).value, ["spotify_downloader", "output_format", "duration"])
        elif event.switch.id == "spotify_display_album":
            write_config(self.query_one("#spotify_display_album", Switch).value, ["spotify_downloader", "output_format", "album"])
        elif event.switch.id == "spotify_display_popularity":
            write_config(self.query_one("#spotify_display_popularity", Switch).value, ["spotify_downloader", "output_format", "popularity"])

        elif event.switch.id == "youtube_display_duration":
            write_config(self.query_one("#youtube_display_duration", Switch).value, ["youtube_downloader", "output_format", "duration"])
        elif event.switch.id == "youtube_display_uploader":
            write_config(self.query_one("#youtube_display_uploader", Switch).value, ["youtube_downloader", "output_format", "uploader"])
        elif event.switch.id == "youtube_display_view_count":
            write_config(self.query_one("#youtube_display_view_count", Switch).value, ["youtube_downloader", "output_format", "view_count"])
        elif event.switch.id == "youtube_display_id":
            write_config(self.query_one("#youtube_display_id", Switch).value, ["youtube_downloader", "output_format", "id"])

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
    """

    def compose(self) -> ComposeResult:
        with Container(id="main_container"):
            with Vertical(classes="option_sections"):
                with Container(classes="section_container", id="skip_processes"):
                    yield Checkbox("Download Song", id="download_song_checkbox")
                    yield Checkbox("Genius Metadata", id="genius_metadata_checkbox")
                    yield Checkbox("Separate Stems", id="separate_stems_checkbox")
                    yield Checkbox("Split and Tag lyrics", id="split_and_tag_checkbox")
                    yield Checkbox("Translate Lyrics", id="translate_lyrics_checkbox")

    def _on_mount(self, event: events.Mount) -> None:
        skip_processes = self.query_one("#skip_processes", Container)
        skip_processes.border_title = "Skip Processes"

        config_file_data = read_config()
        initial_skip_processes = config_file_data["skip_processes"]

        download_song_checkbox = self.query_one("#download_song_checkbox", Checkbox)
        genius_metadata_checkbox = self.query_one("#genius_metadata_checkbox", Checkbox)
        separate_stems_checkbox = self.query_one("#separate_stems_checkbox", Checkbox)
        split_and_tag_checkbox = self.query_one("#split_and_tag_checkbox", Checkbox)
        translate_lyrics_checkbox = self.query_one("#translate_lyrics_checkbox", Checkbox)

        download_song_checkbox.value = initial_skip_processes["download_song"]
        genius_metadata_checkbox.value = initial_skip_processes["genius_metadata"]
        separate_stems_checkbox.value = initial_skip_processes["vocal_separation"]
        split_and_tag_checkbox.value = initial_skip_processes["split_and_tag"]
        translate_lyrics_checkbox.value = initial_skip_processes["translate_lyrics"]

    @staticmethod
    def on_checkbox_changed(event: Checkbox.Changed):
        if event.checkbox.id == "download_song_checkbox":
            write_config(event.value, ["skip_processes", "download_song"])
        elif event.checkbox.id == "genius_metadata_checkbox":
            write_config(event.value, ["skip_processes", "genius_metadata"])
        elif event.checkbox.id == "separate_stems_checkbox":
            write_config(event.value, ["skip_processes", "vocal_separation"])
        elif event.checkbox.id == "split_and_tag_checkbox":
            write_config(event.value, ["skip_processes", "split_and_tag"])
        elif event.checkbox.id == "translate_lyrics_checkbox":
            write_config(event.value, ["skip_processes", "translate_lyrics"])


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
                SaveConfirmationModal(),
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
