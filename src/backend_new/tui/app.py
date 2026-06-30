from typing import Iterable, Any
import threading
import webbrowser

from textual import work, events, on
from textual.app import App, ComposeResult, SystemCommand
from textual.events import ScreenResume, ScreenSuspend
from textual.screen import Screen, ModalScreen
from textual.widgets import Footer, Header, Button, Static, Link
from textual.containers import Container, Horizontal, HorizontalGroup, CenterMiddle

from backend_new.extractors.downloader import Downloader
from backend_new.tui.modalscreens.info import InfoModalScreen

from backend_new.tui.screens.first_init import InitProgress, InitEnvKeys, InitDownloadDicts, FirstTimeInit
from backend_new.tui.screens.home import HomeScreen
from backend_new.tui.screens.new_download import DownloadScreen
from backend_new.tui.screens.config import ConfigMenu, DownloadMenu
from backend_new.tui.screens.process_song import ProcessSong
from backend_new.tui.widgets.interactive import InputSubmit, PasteOnlyInputSubmit

from backend_new.tui.widgets.static import SpotifyCurrentlyPlayingWidget
from backend_new.utils.functions.filesystem import read_config



class MiraaInterface(App):
    use_spotify_token = False

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
        self.push_screen(ConfigMenu())

    def action_open_new_download(self) -> None:
        self.push_screen(DownloadScreen())

    def action_open_process(self) -> None:
        self.push_screen(ProcessSong())

    def on_mount(self) -> None:
        self.theme = "monokai"
        self.read_config_worker(True)

        self.install_screen(HomeScreen(), name="home")

    def handle_config_response(self, result: Any, push_screen: bool = False):
        self.use_spotify_token = result["spotify_downloader"]["token"]
        if push_screen:
            self.handle_push_home_screen()
        self.notify(str(self.use_spotify_token))

    def handle_push_home_screen(self) -> None:
        self.push_screen("home")

    @work(thread=True)
    def read_config_worker(self, push_screen: bool = False) -> None:
        result = read_config()
        self.call_from_thread(self.handle_config_response, result, push_screen)

    @on(DownloadMenu.ReAuthSpotify)
    def bubble_reauth_spotify(self, event: DownloadMenu.ReAuthSpotify) -> None:
        try:
            home_screen = self.get_screen("home")
            self.notify(f"bubble app {str(home_screen)}")
            home_screen.post_message(event)
        except Exception as e:
            raise Exception("screen not registered")

if __name__ == '__main__':
    app = MiraaInterface()
    app.run()