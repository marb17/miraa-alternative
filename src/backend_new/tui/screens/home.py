from typing import Any

from textual import work, on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Button
from textual.containers import Container, HorizontalGroup

from backend_new.extractors.downloader import Downloader
from backend_new.tui.modalscreens.full import SpotifyAuthenticateScreen
from backend_new.tui.modalscreens.info import RestartAppModalScreen

from backend_new.tui.screens.init.first_init import FirstTimeInit
from backend_new.tui.screens.menu.new_download import DownloadScreen
from backend_new.tui.screens.config.config import ConfigMenu, DownloadMenu
from backend_new.tui.screens.menu.process_song import ProcessSong

from backend_new.tui.widgets.static import SpotifyCurrentlyPlayingWidget
from backend_new.utils.functions.filesystem import read_config, all_available_temp_json_files


class HomeScreen(Screen):
    BINDINGS = [("ctrl+o", "open_config", "Config")]

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

            margin: 1 1;

            dock: bottom;
        }

        #quick_menu Button {
            margin: 1 1;
        }

        SpotifyCurrentlyPlayingWidget {
            width: 100%;
            height: auto;

            padding: 1 2;
        }

        #spotify_container {
            margin: 1 1;

            hatch: right $accent 10%;

            border: solid $secondary;
            border-title-color: $primary;
            border-title-style: bold;
            border-title-align: center;
        }
        """

    spotify_client = Downloader()
    next_ui_response = None

    def action_open_config(self) -> None:
        config = ConfigMenu()
        config.id = "config_menu"
        self.app.push_screen(config)

    def action_open_new_download(self) -> None:
        self.app.push_screen(DownloadScreen(), callback=self.handle_resume_widget_poll)

    def action_open_process(self) -> None:
        self.app.push_screen(ProcessSong(), callback=self.handle_resume_widget_poll)

    def handle_resume_widget_poll(self, result: Any) -> None:
        widget = self.query_one("#spotify_currently_playing", SpotifyCurrentlyPlayingWidget)
        widget.handle_start_updating()

    def compose(self) -> ComposeResult:
        yield Footer()
        yield Header(name="miraa-alternative",
                     show_clock=True)

        with Container(id="fullscreen"):
            with HorizontalGroup(id="spotify_container"):
                yield SpotifyCurrentlyPlayingWidget(id="spotify_currently_playing")

            with HorizontalGroup(id="quick_menu"):
                yield Button("Download New", id="download", variant="success")
                yield Button("Process Song", id="process", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#quick_menu", HorizontalGroup).border_title = "Quick Menu"
        self.query_one("#spotify_container", HorizontalGroup).border_title = "Spotify"

        if not self.check_if_init():
            self.app.push_screen(FirstTimeInit(), callback=self.after_init_finished)
        else:
            self.start_app()

        self.check_can_process_song()

    @work(thread=True)
    def check_can_process_song(self) -> None:
        self.handle_display_process_song(not bool(all_available_temp_json_files()))

    def handle_display_process_song(self, value: bool) -> None:
        self.query_one("#process", Button).disabled = value

    def after_init_finished(self, result: Any = None) -> None:
        self.start_app()

    def start_app(self) -> None:
        self.authenticate_spotify()

    def authenticate_spotify(self):
        self.app.push_screen(SpotifyAuthenticateScreen(), callback=self.handle_authenticate_spotify_widget)

    def handle_authenticate_spotify_widget(self, result: Any) -> None:
        self.query_one("#spotify_currently_playing", SpotifyCurrentlyPlayingWidget).action_authenticate()

    @on(DownloadMenu.ReAuthSpotify)
    def handle_reauth_spotify(self, event: DownloadMenu.ReAuthSpotify) -> None:
        event.stop()
        self.app.push_screen(RestartAppModalScreen())

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
            self.query_one("#spotify_currently_playing", SpotifyCurrentlyPlayingWidget).handle_stop_updating()
            self.action_open_new_download()
        elif event.button.id == "process":
            self.query_one("#spotify_currently_playing", SpotifyCurrentlyPlayingWidget).handle_stop_updating()
            self.action_open_process()