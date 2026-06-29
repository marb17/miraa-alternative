from typing import Iterable, Any
import threading
import webbrowser

from textual import work, events, on
from textual.app import App, ComposeResult, SystemCommand
from textual.screen import Screen, ModalScreen
from textual.widgets import Footer, Header, Button, Static, Link
from textual.containers import Container, Horizontal, HorizontalGroup, CenterMiddle

from backend_new.extractors.downloader import Downloader
from backend_new.tui.modalscreens.info import InfoModalScreen

from backend_new.tui.screens.first_init import InitProgress, InitEnvKeys, InitDownloadDicts, FirstTimeInit
from backend_new.tui.screens.new_download import DownloadScreen
from backend_new.tui.screens.config import ConfigMenu
from backend_new.tui.screens.process_song import ProcessSong
from backend_new.tui.widgets.interactive import InputSubmit

from backend_new.tui.widgets.static import SpotifyCurrentlyPlayingWidget
from backend_new.utils.functions.filesystem import read_config


class SpotifyAuthenticateScreen(ModalScreen):
    DEFAULT_CSS = """
    #fullscreen {
        width: 100%;
        height: 100%;
        
        align: center middle;
        content-align: center middle;
    }
    
    #main_box {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-style: bold;
        border-title-align: center;
    
        width: 85%;
        height: auto;
        
        align: center middle;
        content-align: center middle;
        
        padding: 1 2;
    }
    
    #main_box Static {
        
    }
    
    #main_box HorizontalGroup InputSubmit {
        height: auto;
        width: 1fr;
    }
    
    #main_box HorizontalGroup {
        width: 100%;
    }
    
    #btn_open_link {
        offset-y: 1;
    }
    """

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def compose(self) -> ComposeResult:
        with Container(id="fullscreen"):
            with CenterMiddle(id="main_box"):
                yield Static("This is probably your first time logging in to miraa-alternative.\nWe require you to link your spotify account to ensure all features work.\nPlease click the link below to authorize your spotify account.")
                yield Static()
                yield Link(
                    url=self.url,
                    text="Open Me!"
                )
                yield Static()
                yield Static("Don't worry if the website can't be reached, all services are ran locally on your machine, so there is no website to redirect to.\n\nPlease copy the link you have been redirected to after following the instructions below.\n")
                with HorizontalGroup():
                    yield InputSubmit(
                        placeholder="Enter Link Address",
                        id="input_box"
                    )
                    yield Button(label="Open Link", variant="primary", id="btn_open_link")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#main_box", CenterMiddle).border_title = "Spotify Authentication"

    @on(InputSubmit.Submitted, "#input_box")
    def handle_submit(self, event: InputSubmit.Submitted) -> None:
        self.dismiss(event.value)

    @on(Button.Pressed, "#btn_open_link")
    def handle_open_link(self):
        try:
            webbrowser.open(self.url)
        except Exception as e:
            self.notify(f"Failed to open {self.url}, error: {e}")

class MiraaInterface(App):
    SCREENS = {
        "config_menu": ConfigMenu,
        "init_screen": FirstTimeInit,
        "init_prog": InitProgress,
        "init_env": InitEnvKeys,
        "init_dicts": InitDownloadDicts,
    }

    BINDINGS = [("ctrl+o", "push_screen('config_menu')", "Config")]

    DEFAULT_CSS = """
    #fullscreen {
        hatch: right $accent 10%;
    }
    
    #quick_menu {
        align: center middle;
        
        height: auto;
        width: 100%;
        
        border: solid $secondary;
        border-title-color: $primary;
        border-title-style: bold;
        border-title-align: center;
        
        hatch: right $accent 10%;
        
        dock: bottom;
    }
    
    #quick_menu Button {
        margin: 1 1;
    }
    """

    spotify_client = Downloader()
    next_ui_response = None

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)

        yield SystemCommand(
            title="Config menu",
            help="Opens the configuration menu",
            callback=self.action_open_config
        )
        yield SystemCommand(
            title="Download New",
            help="Downloads a new song to be processed",
            callback=self.action_open_new_download
        )
        yield SystemCommand(
            title="Process Song",
            help="Processes a song that has been downloaded",
            callback=self.action_open_process
        )

    def action_open_config(self) -> None:
        self.app.push_screen("config_menu")

    def action_open_new_download(self) -> None:
        # self.app.push_screen("new_download")
        self.app.push_screen(DownloadScreen())

    def action_open_process(self) -> None:
        self.app.push_screen(ProcessSong())

    def compose(self) -> ComposeResult:
        yield Footer()
        yield Header(name="miraa-alternative",
                     show_clock=True)

        with Container(id="fullscreen"):
            yield SpotifyCurrentlyPlayingWidget(id="spotify_currently_playing")

            with HorizontalGroup(id="quick_menu"):
                yield Button("Download New", id="download", variant="success")
                yield Button("Process Song", id="process", variant="primary")

    def on_mount(self) -> None:
        self.theme = "monokai"
        self.query_one("#quick_menu", HorizontalGroup).border_title = "Quick Menu"

        if not self.check_if_init():
            self.push_screen("init_screen", callback=self.after_init_finished)
        else:
            self.start_app()

    def after_init_finished(self, result: Any = None) -> None:
        self.start_app()

    def start_app(self) -> None:
        self.authenticate_spotify()

    @work(thread=True)
    def authenticate_spotify(self) -> None:
        screen_closed_event = threading.Event()

        pipeline = self.spotify_client.authenticate()

        try:
            message = next(pipeline)
        except StopIteration as e:
            if not e.value: raise Exception("Authentication failed")
            return

        while True:
            try:
                if message.type == "input":
                    screen_closed_event.clear()

                    self.app.call_from_thread(
                        self.display_spotify_auth_message,
                        screen_closed_event,
                        message.extra_info["url"]
                    )

                    screen_closed_event.wait()

                    message = pipeline.send(self.next_ui_response)
                else:
                    message = next(pipeline)

            except StopIteration as e:
                if not e.value:
                    raise Exception("Authentication failed")
                break

        self.app.call_from_thread(self.authenticate_spotify_widget)
        self.set_interval(5, self.update_spotify_widget)

    def authenticate_spotify_widget(self):
        self.query_one("#spotify_currently_playing", SpotifyCurrentlyPlayingWidget).action_authenticate()

    def update_spotify_widget(self) -> None:
        self.query_one("#spotify_currently_playing", SpotifyCurrentlyPlayingWidget).update_data()

    def display_spotify_auth_message(self, event: threading.Event, url_to_auth: str) -> None:
        def on_modal_closed(result: str | None = None) -> None:
            self.next_ui_response = result
            event.set()

        self.app.push_screen(SpotifyAuthenticateScreen(url_to_auth), callback=on_modal_closed)


    @staticmethod
    def check_if_init() -> bool:
        try:
            if read_config().get("init"):
                return True
            else:
                return False
        except FileNotFoundError:
            return False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "download":
            self.action_open_new_download()
        elif event.button.id=="process":
            self.action_open_process()


if __name__ == '__main__':
    app = MiraaInterface()
    app.run()