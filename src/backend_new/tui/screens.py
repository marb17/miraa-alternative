from fontTools.varLib import avar
from mmengine.runner import priority
from rich.box import HEAVY_EDGE
from sympy.physics.wigner import racah
from textual import events, containers, work
from textual.app import ComposeResult
from textual.widgets import Footer, Header, Switch, TabbedContent, TabPane, Checkbox, Label, Button, Static, ProgressBar, RichLog, Input, Link
from textual.containers import Horizontal, Vertical, Container, HorizontalGroup, Middle, CenterMiddle, Center, VerticalScroll, VerticalGroup, Grid
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.reactive import reactive

from backend_new.utils.helper_funcs import read_config, write_config, download_all_dicts
from backend_new.utils.constants import ENV_FILE, DEFAULT_DICTS

from backend_new.main import Analyzer

import time
from dotenv import set_key, load_dotenv
from rich.markup import escape
import os

# region config menu

# default stuff prob like template
"""
DEFAULT_CSS = '''
    .section_container {
        height: auto;
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
    }
    
    .option_sections {
        padding: 0 1;
        align: center top;
        border: heavy $primary;
    }
    '''
"""

class SaveConfirmationModal(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog_card"):
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


class DownloadMenu(Horizontal):
    DEFAULT_CSS = """
        .section_container {
            height: auto;
            border: solid $secondary;
            border-title-style: bold;
            border-title-color: $primary;
        }

        .section_container Label {
            padding: 1;
        }

        .option_sections {
            padding: 0 1;
            align: center top;
        }  
        """

    config_file_data = None
    anything_changed = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(classes="option_sections"):
                with containers.HorizontalGroup(classes="section_container", id="downloader"):
                    yield Switch(id="downloader_cookies_switch")
                    yield Label("Use cookies for YouTube Downloader?")

    def _on_mount(self, event: events.Mount) -> None:
        downloader = self.query_one("#downloader", containers.HorizontalGroup)
        downloader.border_title = "Downloader"

        self.config_file_data = read_config()

        youtube_cookies_switch = self.query_one("#downloader_cookies_switch", Switch)

        youtube_cookies_switch.value = self.config_file_data["youtube_downloader"]["use_cookies"]


    def on_switch_changed(self, event: Switch.Changed):
        self.anything_changed = True

        if event.control.id == "downloader_cookies_switch":
            self.config_file_data["youtube_downloader"]["use_cookies"] = event.value

    @work(thread=True)
    def action_update_config(self):
        write_config(self.config_file_data)


class ProcessesMenu(Horizontal):
    DEFAULT_CSS = """
    .section_container {
        height: auto;
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
    }
    
    .option_sections {
        padding: 0 1;
        align: center top;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
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


class EnvironmentVariablesMenu(Horizontal):
    DEFAULT_CSS = """
    .section_container {
        height: auto;
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
    }
    
    .option_sections {
        padding: 0 1;
        align: center top;
    }
    
    #buttons {
        align: right middle;
        content-align: right middle;
        margin: 0 1;
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

    load_dotenv(ENV_FILE)
    spot_cli_id = os.getenv("SPOTIFY_CLIENT_ID")
    spot_cli_sec = os.getenv("SPOTIFY_CLIENT_SECRET")
    spot_redir_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    gen_acc_tok = os.getenv("GENIUS_ACCESS_TOKEN")

    def compose(self) -> ComposeResult:
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

        self.query_one("#in1", Input).value = self.spot_cli_id
        self.query_one("#in2", Input).value = self.spot_cli_sec
        self.query_one("#in3", Input).value = self.spot_redir_uri
        self.query_one("#in4", Input).value = self.gen_acc_tok

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
            set_key(ENV_FILE, "SPOTIFY_CLIENT_ID", self.spot_cli_id, quote_mode="never")
            set_key(ENV_FILE, "SPOTIFY_CLIENT_SECRET", self.spot_cli_sec, quote_mode="never")
            set_key(ENV_FILE, "SPOTIFY_REDIRECT_URI", self.spot_redir_uri, quote_mode="never")
            set_key(ENV_FILE, "GENIUS_ACCESS_TOKEN", self.gen_acc_tok, quote_mode="never")

            self.anything_changed = False


class ConfigMenu(Screen):
    BINDINGS = [
        Binding("ctrl+x", "app.pop_screen", "Exit Menu", priority=True)
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with TabbedContent():
            with TabPane("Processes"):
                yield ProcessesMenu()
            with TabPane("Downloader"):
                yield DownloadMenu()
            with TabPane(".env"):
                yield EnvironmentVariablesMenu()

# endregion

# region first time init screeen

class InitProgress(Screen):
    BINDINGS = []
    DEFAULT_CSS = """
    #progress {
        height: auto;
        width: 60;
        
        padding: 0 2;
        
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
        border-title-align: center;
    }
    
    #progress > * {
        padding: 1;
        width: 100%;
    }
    
    #progress RichLog {
        height: 6; 
        width: 100%;
    }
    
    Container {
        align: center middle;
        content-align: center middle;
    }
    
    ProgressBar {
        width: 40;
        align: center middle;
    }
        
    Label {
        width: auto;
        text-align: center;
    }
    """

    finished_init = False

    def compose(self) -> ComposeResult:
        yield Header()

        with Container():
            with CenterMiddle(id="progress"):
                with Center():
                    yield Label("Completion:")
                    yield ProgressBar(total=3, show_eta=False)

                yield RichLog(id="logs", highlight=True, markup=True)

                yield Static("Finished initial setup, press any key to continue [blink]_[/]", disabled=True, id="continue_static")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one(CenterMiddle).border_title = "Main Setup"
        self.query_one("#continue_static", Static).display = False

        self.init_miraa()

    def go_to_next_screen(self) -> None:
        self.app.switch_screen("init_env")

    @work(thread=True)
    def init_miraa(self):
        prog_bar = self.query_one(ProgressBar)
        logs = self.query_one(RichLog)

        with Analyzer() as a:
            for log in a.init():
                prog_bar.advance(1)
                logs.write(log)

        self.finished_init = True
        self.query_one("#continue_static", Static).display = True

    def _on_key(self, event: events.Key) -> None:
        if self.finished_init:
            event.stop()
            self.go_to_next_screen()


class InitEnvKeys(Screen):
    class InitEnvHelpScreen(ModalScreen):
        HELP_MESSAGE = """To get your Tokens from Spotify and Genius, please open these links:
    - [@click="app.open_url('https://developer.spotify.com/dashboard')"]Spotify Dashboard[/]
    - [@click="app.open_url('https://genius.com/api-clients')"]Genius Dashboard[/]

Genius is easy to create an API key
Just create an app and press | [bold]Generate Access Token[/bold] |

Spotify is also same but just needs the right Redirect URI
You can use these for them:
    - https://127.0.0.1:8080
    - https://localhost:8080
"""

        DEFAULT_CSS = """
        #vert_group {
            width: 65%;
            height: auto;
            max-height: 30;
            
            background: $surface;
            border: solid $primary;
            border-title-align: center;
            
            align: center middle; 
            content-align: center middle;
        }
        
        Container {
            height: auto;
            
            align: center middle;
            content-align: center middle;
        }
        
        Static {
            margin: 1 2;
            padding: 1 2;
            text-align: left;
            text-overflow: fold;
        }
        
        #text_con {
            margin: 0 1;
            width: 100%;
        }
        
        #button_con {
            width: 100%;
            margin: 0 0 1 0;
        }
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.styles.align = ("center", "middle")

        def compose(self) -> ComposeResult:
            with Center(id="vert_group"):
                with Container(id="text_con"):
                    yield Static(self.HELP_MESSAGE)
                with Container(id="button_con"):
                    yield Button("Exit", variant="error", id="exit")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "exit":
                self.dismiss()

        def _on_mount(self, event: events.Mount) -> None:
            self.query_one(Center).border_title = "Environment Variable Help"

    DEFAULT_CSS = """
    CenterMiddle {
        height: auto;
        width: 100%;
        
        padding: 0 4;
    
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
        border-title-align: center;
    }
    
    Label {
        padding: 1;
    }
    
    Container {
        align: center middle;
        content-align: center middle;
    }
    
    Button {
        margin: 1;
    }
    
    #button_con {
        width: 100%;
        height: auto;
    }
    
    #button_hor {
        align: right middle;
        content-align: right middle;
    }
    """

    spot_cli_id = None
    spot_cli_sec = None
    spot_redir_uri = None
    gen_acc_tok = None

    error_message = ""

    def compose(self) -> ComposeResult:
        yield Header()

        with Container():
            with CenterMiddle(id="env_input"):
                yield Label("Please input your Environment Variables:")

                yield Input(placeholder="SPOTIFY_CLIENT_ID", id="in1")
                yield Input(placeholder="SPOTIFY_CLIENT_SECRET", id="in2")
                yield Input(placeholder="SPOTIFY_REDIRECT_URI", id="in3")
                yield Input(placeholder="GENIUS_ACCESS_TOKEN", id="in4")

                err_msg = Static(self.error_message, disabled=True, id="err_msg")
                err_msg.styles.color = "red"
                yield err_msg

                with Container(id="button_con"):
                    with HorizontalGroup(id="button_hor"):
                        yield Button(variant="warning", id="help_button", label="Help")
                        yield Button(variant="success", id="confirm", label="Confirm")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one(CenterMiddle).border_title = "Environment Variables"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.value:
            if event.input.id == "in1":
                self.query_one("#in2", Input).focus()
            elif event.input.id == "in2":
                self.query_one("#in3", Input).focus()
            elif event.input.id == "in3":
                self.query_one("#in4", Input).focus()
            elif event.input.id == "in4":
                self.query_one("#confirm", Button).focus()
        else:
            match event.input.id:
                case "in1": self.error_message = "SPOTIFY_CLIENT_ID cannot be empty"
                case "in2": self.error_message = "SPOTIFY_CLIENT_SECRET cannot be empty"
                case "in3": self.error_message = "SPOTIFY_REDIRECT_URI cannot be empty"
                case "in4": self.error_message = "GENIUS_ACCESS_TOKEN cannot be empty"
            self.query_one("#err_msg", Static).content = self.error_message
            self.query_one("#err_msg", Static).display = True

    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#err_msg", Static).display = False

        if event.input.id == "in1":
            self.spot_cli_id = event.input.value
        elif event.input.id == "in2":
            self.spot_cli_sec = event.input.value
        elif event.input.id == "in3":
            self.spot_redir_uri = event.input.value
        elif event.input.id == "in4":
            self.gen_acc_tok = event.input.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        anything_empty = False
        empty_list: list[str] = list()

        if event.button.id == "confirm":
            if not self.spot_cli_id:
                anything_empty = True
                empty_list.append("SPOTIFY_CLIENT_ID")
            if not self.spot_cli_sec:
                anything_empty = True
                empty_list.append("SPOTIFY_CLIENT_SECRET")
            if not self.spot_redir_uri:
                anything_empty = True
                empty_list.append("SPOTIFY_REDIRECT_URI")
            if not self.gen_acc_tok:
                anything_empty = True
                empty_list.append("GENIUS_ACCESS_TOKEN")

            if anything_empty:
                self.error_message = f"{', '.join(empty_list)} cannot be empty!"
                self.query_one("#err_msg", Static).content = self.error_message
                self.query_one("#err_msg", Static).display = True
            else:
                set_key(ENV_FILE, "SPOTIFY_CLIENT_ID", self.spot_cli_id, quote_mode="never")
                set_key(ENV_FILE, "SPOTIFY_CLIENT_SECRET", self.spot_cli_sec, quote_mode="never")
                set_key(ENV_FILE, "SPOTIFY_REDIRECT_URI", self.spot_redir_uri, quote_mode="never")
                set_key(ENV_FILE, "GENIUS_ACCESS_TOKEN", self.gen_acc_tok, quote_mode="never")

                self.app.switch_screen("init_dicts")
        elif event.button.id == "help_button":
            self.app.push_screen(self.InitEnvHelpScreen())


class InitDownloadDicts(Screen):
    class AutoDownloadDicts(ModalScreen):
        DEFAULT_CSS = """
        CenterMiddle {
            height: auto;
            width: 80%;
            
            padding: 0 4;
    
            border: solid $secondary;
            border-title-style: bold;
            border-title-color: $primary;
            border-title-align: center;
        }
        
        RichLog {
            height: 30;
            width: 100%;
            margin: 0 0 1 0;
        }
        
        ProgressBar {
            margin: 0 0 1 0;
        }
        
        Container {
            align: center middle;
            content-align: center middle;
        }
        
        Label {
            text-align: center;
        }
        """

        finished_downloading = False
        failed_downloading = False

        def compose(self) -> ComposeResult:
            with Container():
                with CenterMiddle():
                    yield Label("")
                    yield Label("Downloading Dictionaries")
                    yield ProgressBar(id="progress_bar", total=len(DEFAULT_DICTS) * 2, show_eta=True)
                    yield RichLog(id="logs")
                    yield Static("Finished Downloading, press any key to continue [blink]_[/]", disabled=True, id="finished")

        def _on_mount(self, event: events.Mount) -> None:
            self.query_one(CenterMiddle).border_title = "Auto Download Dictionaries"
            self.download_dicts()

        @work(thread=True)
        def download_dicts(self):
            try:
                self.query_one("#finished", Static).display = False
                for log in download_all_dicts():
                    self.query_one(ProgressBar).advance(1)
                    self.query_one(RichLog).write(log)
            except Exception as e:
                self.query_one(RichLog).write(e)
                self.query_one("#finished", Static).content = "Failed to download, press any key to dismiss"
                self.failed_downloading = True

            def reveal_completion_banner():
                self.query_one("#finished", Static).display = True
                self.finished_downloading = True

            self.app.call_from_thread(reveal_completion_banner)

        def _on_key(self, event: events.Key) -> None:
            if self.finished_downloading and not self.failed_downloading:
                event.stop()
                self.dismiss(True)
            elif self.finished_downloading and self.failed_downloading:
                event.stop()
                self.dismiss(False)

    #! TODO fix the message it doesnt work
    class ManualDownloadHelp(ModalScreen):
        HELP_MESSAGE = """Please download these .zip files and move them to src/dicts directory"""
        # for k, v in DEFAULT_DICTS_LINK.items():
        #     safe_key = escape(k)
        #     HELP_MESSAGE += f"\n    - [@click=\"app.open_url('{v}')\"]{safe_key}[/]"

        DEFAULT_CSS = """
        #vert_group {
            width: 85%;
            height: auto;
            max-height: 30;

            background: $surface;
            border: solid $primary;
            border-title-align: center;

            align: center middle; 
            content-align: center middle;
        }

        Container {
            height: auto;

            align: center middle;
            content-align: center middle;
        }

        Static {
            margin: 1 2;
            padding: 1 2;
            text-align: left;
            text-overflow: fold;
        }

        #text_con {
            margin: 0 1;
            width: 100%;
        }

        #button_con {
            width: 100%;
            margin: 0 0 1 0;
        }
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.styles.align = ("center", "middle")

        def compose(self) -> ComposeResult:
            with Center(id="vert_group"):
                with Container(id="text_con"):
                    yield Static(self.HELP_MESSAGE)
                with Container(id="button_con"):
                    yield Button("Exit", variant="error", id="exit")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "exit":
                self.dismiss(True)

        def _on_mount(self, event: events.Mount) -> None:
            self.query_one(Center).border_title = "Manual Download Links"

    #! TODO add the extract thing
    class ExtractDicts(ModalScreen):
        ...

    DEFAULT_CSS = """
    #pop_up {
        width: auto;
        height: auto;
    
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
        border-title-align: center;
    }
    
    #main {
        align: center middle;
        content-align: center middle;
        
        border: solid $primary;
    }
    
    Label {
        width: auto;
    
        margin: 1 2;
        
        text-align: center;
    }
    
    Button {
        width: auto;
    }
    
    #hor_group {
        align: center middle;
        content-align: center middle;
        
        width: auto;
    }
    
    #button_con {
        height: auto;
        width: 100%;
        
        align: center middle;
        content-align: center middle;
        
        margin: 1;
    }
    """

    finished_downloading = False

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main"):
            with CenterMiddle(id="pop_up"):
                yield Label("Please download these JP dictionaries for the app to work!")

                with Container(id="button_con"):
                    with HorizontalGroup(id="hor_group"):
                        yield Button(variant="success", id="download", label="Download All")
                        yield Button(variant="warning", id="manual", label="Manually Download All")

                yield Static("Finished downloading, press any key to continue [blink]_[/]", id="continue_static")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one(CenterMiddle).border_title = "Download Dictionaries"
        self.query_one("#continue_static", Static).display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "download":
            self.app.push_screen(self.AutoDownloadDicts(), callback=self.auto_download_callback)
        elif event.button.id == "manual":
            self.app.push_screen(self.ManualDownloadHelp(), callback=self.manual_download_callback)

    def auto_download_callback(self, value: bool) -> None:
        if value:
            self.finished_downloading = True
            self.query_one("#continue_static", Static).display = True
        else:
            self.query_one("#download", Button).disabled = True

    def manual_download_callback(self, value: bool) -> None:
        if value:
            self.finished_downloading = True
            self.query_one("#manual", Button).disabled = True
            self.query_one("#continue_static", Static).display = True

    def _on_key(self, event: events.Key) -> None:
        if self.finished_downloading:
            # TODO go to next screen
            self.app.pop_screen()

            event.stop()


class FirstTimeInit(Screen):
    BINDINGS = []

    DEFAULT_CSS = """
    #confirm_popup {
        height: auto;
        width: auto;
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
        border-title-align: center;
    }
    
    #confirm_popup HorizontalGroup {
        width: 100%;
        align: center middle;
        content-align: center middle;
        padding: 1 0;
    }
    
    #confirm_popup Static {
        width: auto;
        text-align: center;
        padding: 1 2;
    }
    
    #whole_screen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="whole_screen"):
            with Container(id="confirm_popup"):
                yield Static("miraa-alternative isn't initialized yet,\nWould you like to initialize it?")

                with HorizontalGroup():
                    yield Button(variant="error", label="No", id="deny")
                    yield Button(variant="success", label="Yes", id="confirm")

        yield Footer()

    def _on_mount(self, event: events.Mount) -> None:
        popup = self.query_one("#confirm_popup", Container)
        popup.border_title = "miraa-alternative Initialization"

        self.query_one("#confirm", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.app.switch_screen("init_prog")
        elif event.button.id == "deny":
            self.app.exit()

# endregion