from textwrap import wrap
from typing import Iterable

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Container, HorizontalGroup
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Static, Button


class InfoModalScreen(ModalScreen):
    HELP_MESSAGE = """"""
    MIDDLE_BORDER_TITLE = ""
    WINDOW_WIDTH = 65

    DEFAULT_CSS = f"""
        #vert_group {{
            width: {WINDOW_WIDTH}%;
            height: auto;

            background: $surface;
            border: solid $primary;
            border-title-align: center;

            align: center middle; 
            content-align: center middle;
        }}

        Container {{
            height: auto;

            align: center middle;
            content-align: center middle;
        }}

        Static {{
            text-align: left;
            text-wrap: wrap;
            text-overflow: fold;
        }}

        #text_con {{
            padding: 1 2;
            width: 100%;
        }}

        #button_con {{
            width: 100%;
            margin: 0 0 1 0;
        }}
        """

    def __init__(self, *args, **kwargs):
        self.custom_children: Iterable[Widget] | None = kwargs.pop("children", None)
        self.HELP_MESSAGE = kwargs.pop("message", "You have not inserted a help message, please use the keyword 'message' while initiating this modal screen.")
        self.MIDDLE_BORDER_TITLE = kwargs.pop("border_title", "No Border Title set, please use the keyword 'border_title' while initiating this modal screen.")
        self.WINDOW_WIDTH = kwargs.pop("window_width", 65)

        super().__init__(*args, **kwargs)
        self.styles.align = ("center", "middle")

    def compose(self) -> ComposeResult:
        with Center(id="vert_group"):
            with Container(id="text_con"):
                if self.custom_children is not None:
                    yield from self.custom_children
                else:
                    yield Static(Text(self.HELP_MESSAGE))
            with Container(id="button_con"):
                yield Button("Exit", variant="error", id="exit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "exit":
            self.dismiss(True)

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one(Center).border_title = self.BORDER_TITLE


class RestartAppModalScreen(ModalScreen):
    HELP_MESSAGE = "The app requires to restart to apply the changes."
    MIDDLE_BORDER_TITLE = "Changes require Restart"
    WINDOW_WIDTH = 65

    DEFAULT_CSS = f"""
            #vert_group {{
                width: {WINDOW_WIDTH}%;
                height: auto;

                background: $surface;
                border: solid $primary;
                border-title-align: center;

                align: center middle; 
                content-align: center middle;
            }}

            Container, HorizontalGroup{{
                height: auto;

                align: center middle;
                content-align: center middle;
            }}

            Static {{
                text-align: left;
                text-wrap: wrap;
                text-overflow: fold;
            }}

            #text_con {{
                padding: 1 2;
                width: 100%;
            }}

            #button_con {{
                width: 100%;
                margin: 0 0 1 0;
            }}
            
            Button {{
                margin: 0 1;
            }}
            """

    def __init__(self, help_message: str = None, border_title: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.styles.align = ("center", "middle")

        if help_message:
            self.HELP_MESSAGE = help_message
        if border_title:
            self.MIDDLE_BORDER_TITLE = border_title

    def compose(self) -> ComposeResult:
        with Center(id="vert_group"):
            with Container(id="text_con"):
                yield Static(Text(self.HELP_MESSAGE))
            with HorizontalGroup(id="button_con"):
                yield Button("Restart Now", variant="success", id="now")
                yield Button("Later", variant="warning", id="later")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "later":
            self.dismiss(True)
        elif event.button.id == "now":
            self.app.restart_app()

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one(Center).border_title = self.BORDER_TITLE

