import os
import sys
from typing import Iterable, Any
import socket

from textual import work, on
from textual.app import App, SystemCommand
from textual.screen import Screen

from backend_new.tui.screens.home import HomeScreen
from backend_new.tui.screens.menu.new_download import DownloadScreen
from backend_new.tui.screens.config.config import ConfigMenu, DownloadMenu
from backend_new.tui.screens.menu.process_song import ProcessSong

from backend_new.utils.functions.filesystem import read_config



class MiraaInterface(App):
    use_spotify_token = False
    connected_to_internet = False
    is_initialized = False

    # PALATTE COMMANDS
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

        self.is_connected_to_internet()
        self.set_interval(3, self.is_connected_to_internet)



    def restart_app(self) -> None:
        self.notify("Restarting Application")
        self.exit()
        python_executable = sys.executable
        script_args = sys.argv
        os.execv(python_executable, [python_executable] + script_args)



    def handle_config_response(self, result: Any, push_screen: bool = False):
        if result:
            self.use_spotify_token = result["spotify_downloader"]["token"]
        else:
            self.use_spotify_token = False

        if push_screen:
            self.handle_push_home_screen()

    def handle_push_home_screen(self) -> None:
        self.push_screen("home")

    @work(thread=True)
    def read_config_worker(self, push_screen: bool = False) -> None:
        try:
            result = read_config()
        except FileNotFoundError:
            result = None

        self.call_from_thread(self.handle_config_response, result, push_screen)

    @on(DownloadMenu.ReAuthSpotify)
    def bubble_reauth_spotify(self, event: DownloadMenu.ReAuthSpotify) -> None:
        try:
            home_screen = self.get_screen("home")
            home_screen.post_message(event)
        except Exception as e:
            raise Exception()



    @work(thread=True)
    def is_connected_to_internet(self) -> None:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.connected_to_internet = True
        except OSError:
            self.connected_to_internet = False

if __name__ == '__main__':
    app = MiraaInterface()

    app.run()