from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from backend_new.tui.screens import ConfigMenu

class MiraaInterface(App):
    SCREENS = {
        "config_menu": ConfigMenu
    }

    BINDINGS = [("ctrl+o", "push_screen('config_menu')", "Config")]

    def compose(self) -> ComposeResult:
        yield Footer()
        yield Header(name="miraa-alternative",
                     show_clock=True)

if __name__ == '__main__':
    app = MiraaInterface()
    app.run()