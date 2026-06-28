from typing import Iterable

from textual.app import App, ComposeResult, SystemCommand
from textual.screen import Screen
from textual.widgets import Footer, Header, Button
from textual.containers import Container, Horizontal, HorizontalGroup

from backend_new.tui.screens.first_init import InitProgress, InitEnvKeys, InitDownloadDicts, FirstTimeInit
from backend_new.tui.screens.new_download import DownloadScreen
from backend_new.tui.screens.config import ConfigMenu
from backend_new.tui.screens.process_song import ProcessSong

from backend_new.utils.helper_funcs import read_config

class MiraaInterface(App):
    SCREENS = {
        "config_menu": ConfigMenu,
        "init_screen": FirstTimeInit,
        "init_prog": InitProgress,
        "init_env": InitEnvKeys,
        "init_dicts": InitDownloadDicts,

        # "new_download": DownloadScreen
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
            with HorizontalGroup(id="quick_menu"):
                yield Button("Download New", id="download", variant="success")
                yield Button("Process Song", id="process", variant="primary")

    def on_mount(self) -> None:
        self.theme = "monokai"

        if not self.check_if_init():
            self.push_screen("init_screen")

        self.query_one("#quick_menu", HorizontalGroup).border_title = "Quick Menu"

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