from pathlib import Path
from textual import events, work, on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Label, Button, ContentSwitcher, Select, TabbedContent, Static
from textual.binding import Binding

from backend_new.tui.screens.config.config import ProcessesMenu
from backend_new.utils.functions.filesystem import all_available_temp_json_files


class ProcessSong(Screen):
    DEFAULT_CSS = """
    #fullscreen {

    }

    #main_content_switcher {
        width: 100%;
        height: 100%;

        content-align: center middle;
        align: center middle;

        hatch: right $accent 10%;
    }

    #choose_json {
        height: auto;
        
        border: solid $secondary;
        border-title-align: center;
        border-title-style: bold;
        border-title-color: $primary;
        
        padding: 1 2;
    }

    #initial_screen #choose_json Select {
        padding: 1 0;
    }

    #initial_screen #choose_json Horizontal {
        width: 100%;
        height: auto;
        align: right middle;
    }

    #confirm_json {
        margin: 0 1;
    }
    
    #initial_screen {
        width: 90%;
        height: auto;

        padding: 1 2;
        
        align: center middle;
        content-align: center middle;
    }
    
    #options {
        padding: 0 1;
    
        height: auto;
        
        border: solid $secondary;
        border-title-align: center;
        border-title-style: bold;
        border-title-color: $primary;
        
        hatch: right $accent 10%;
    }
    
    #processes_menu {
        padding: 1 0;
        
        height: auto;
        
        hatch: right $accent 10%;
    }
    """

    BINDINGS = [
        Binding("ctrl+x", "app.pop_screen", "Exit Processing", priority=True)
    ]

    json_options: list[tuple[str, Path]] = list()
    selected_json_file = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Container(id="fullscreen"):
            with ContentSwitcher(id="main_content_switcher", initial="initial_screen"):
                with Vertical(id="initial_screen"):
                    with Vertical(id="choose_json"):
                        yield Label(id="select_json_header", content="Please choose which song to process")
                        yield Select(id="select_json", options=list())
                        with Horizontal():
                            yield Button(id="confirm_json", label="Next", variant="success")

                    with Vertical(id="options"):
                        yield ProcessesMenu(id="processes_menu", main_container_height="auto")

                with Vertical(id="process_menu"):
                    yield Static(id="current_process_display")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#choose_json", Vertical).border_title = "Song Processing"
        self.query_one("#options", Vertical).border_title = "Options"
        self.update_json_select()

    @work(thread=True)
    def update_json_select(self) -> None:
        all_files = all_available_temp_json_files()
        self.json_options = [(file["name"], file["path"]) for file in all_files]

        self.update_select_json_widget()

    @on(Button.Pressed, "#confirm_json")
    def select_json_file(self):
        select_value = self.query_one("#select_json", Select).value

        if select_value == Select.NULL:
            self.notify("Please choose a song", severity="warning")
            return

        self.selected_json_file = select_value

        self.query_one("#main_content_switcher", ContentSwitcher).current = "process_menu"

    def update_select_json_widget(self) -> None:
        self.query_one("#select_json", Select).set_options(self.json_options)



        