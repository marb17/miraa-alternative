from typing import Iterable

from textual.app import App, ComposeResult, SystemCommand
from textual.screen import Screen
from textual.widgets import Footer, Header
from textual import work

from backend_new.tui.screens import ConfigMenu, FirstTimeInit, InitProgress, InitEnvKeys, InitDownloadDicts

from backend_new.utils.helper_funcs import read_config

class MiraaInterface(App):
    SCREENS = {
        "config_menu": ConfigMenu,
        "init_screen": FirstTimeInit,
        "init_prog": InitProgress,
        "init_env": InitEnvKeys,
        "init_dicts": InitDownloadDicts
    }

    BINDINGS = [("ctrl+o", "push_screen('config_menu')", "Config")]

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)

        yield SystemCommand(
            title="Config menu",
            help="Opens the configuration menu",
            callback=self.action_open_config
        )

    def action_open_config(self) -> None:
        self.app.push_screen("config_menu")

    def compose(self) -> ComposeResult:
        yield Footer()
        yield Header(name="miraa-alternative",
                     show_clock=True)

    def on_mount(self) -> None:
        self.theme = "monokai"

        if not self.check_if_init():
            self.push_screen("init_screen")

    @staticmethod
    def check_if_init() -> bool:
        try:
            if read_config().get("init"):
                return True
            else:
                return False
        except FileNotFoundError:
            return False


if __name__ == '__main__':
    app = MiraaInterface()
    app.run()