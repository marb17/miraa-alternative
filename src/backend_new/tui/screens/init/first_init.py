from dotenv import set_key
from textual import events, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, CenterMiddle, Center, HorizontalGroup
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Label, ProgressBar, RichLog, Static, Button, Input, Footer

from backend_new.main import Analyzer
from backend_new.tui.modalscreens.info import InfoModalScreen
from backend_new.utils.paths import ENV_FILE
from backend_new.utils.default.default_var import DEFAULT_DICTS
from backend_new.utils.functions.download import download_all_dicts
from backend_new.utils.functions.filesystem import write_config


class InitProgress(Screen):
    BINDINGS = [
        Binding("ctrl+o", "no_action", "No Action", show=False)
    ]

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
        
        hatch: right $accent 10%
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
        self.app.switch_screen(InitEnvKeys())

    @work(thread=True)
    def init_miraa(self):
        prog_bar = self.query_one(ProgressBar)
        logs = self.query_one(RichLog)

        with Analyzer() as a:
            for log in a.init():
                self.app.call_from_thread(prog_bar.advance, 1)
                self.app.call_from_thread(logs.write, log)

        self.finished_init = True
        self.query_one("#continue_static", Static).display = True

    def _on_key(self, event: events.Key) -> None:
        if self.finished_init:
            event.stop()
            self.go_to_next_screen()

    def action_no_action(self) -> None:
        pass


class InitEnvKeys(Screen):
    BINDINGS = [
        Binding("ctrl+o", "no_action", "No Action", show=False)
    ]

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
        
        hatch: right $accent 10%
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

                self.app.switch_screen(InitDownloadDicts())
        elif event.button.id == "help_button":
            self.app.push_screen(InfoModalScreen(message="""To get your Tokens from Spotify and Genius, please open these links:
    - [@click="app.open_url('https://developer.spotify.com/dashboard')"]Spotify Dashboard[/]
    - [@click="app.open_url('https://genius.com/api-clients')"]Genius Dashboard[/]

Genius is easy to create an API key
Just create an app and press | [bold]Generate Access Token[/bold] |

Spotify is also same but just needs the right Redirect URI
You can use these for them:
    - https://127.0.0.1:8080
    - https://localhost:8080""", border_title="Environment Variables Help"))

    def action_no_action(self) -> None:
        pass


class InitDownloadDicts(Screen):
    BINDINGS = [
        Binding("ctrl+o", "no_action", "No Action", show=False)
    ]

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
            
            hatch: right $accent 10%
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
                    self.app.call_from_thread(self.query_one(ProgressBar).advance, 1)
                    self.app.call_from_thread(self.query_one(RichLog).write, log)
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
        
        hatch: right $accent 10%
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
            self.app.push_screen(InfoModalScreen(message="Please download these dicts and move them to src/dicts.",
                                                 border_title="Manual Download Links",
                                                 window_width=85), callback=self.manual_download_callback)

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
            write_config(True, ["init"])

            event.stop()

    def action_no_action(self) -> None:
        pass


class FirstTimeInit(Screen):
    BINDINGS = [
        Binding("ctrl+o", "no_action", "No Action", show=False)
    ]

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
        hatch: right $accent 10%
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
            self.app.switch_screen(InitProgress())
        elif event.button.id == "deny":
            self.app.exit()

    def action_no_action(self) -> None:
        pass
