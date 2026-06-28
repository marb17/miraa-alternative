from typing import Self

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, HorizontalGroup
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, Input, Button


class InputSubmit(Widget):
    DEFAULT_CSS = """
    #input_box {
        width: 1fr;
    }

    #submit_input {
        width: auto;
    }
    
    #input_container {
        height: auto;
    }
    
    #input_container {
        height: auto;
    }
    
    #input_label {
        padding: 0 1;
    }
    """

    class Submitted(Message):
        def __init__(self, sender: Widget, value: str):
            super().__init__()
            self.value = value
            self.sender_widget = sender

        @property
        def control(self) -> Widget:
            """Return the widget that sent this message."""
            return self.sender_widget

    def __init__(self, label: str = "", placeholder: str = "", default_value: str = "", border_enable: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_text = label
        self.placeholder_text = placeholder
        self.default_value = default_value


    def compose(self) -> ComposeResult:
        with Vertical(id="input_container"):
            if self.label_text != "" or True:
                yield Label(self.label_text, id="input_label")
            with HorizontalGroup(id="input_container"):
                yield Input(
                    value=self.default_value,
                    placeholder=self.placeholder_text,
                    id="input_box"
                )
                yield Button("Submit", id="submit_input", variant="success")

    @property
    def value(self):
        try:
            return self.query_one("#input_box", Input).value
        except Exception:
            return self.default_value

    @on(Button.Pressed, "#submit_input")
    def action_button_submit_pressed(self) -> None:
        self.action_submit()

    @on(Input.Submitted, "#input_box")
    def action_input_submitted(self) -> None:
        self.action_submit()

    def action_submit(self) -> None:
        input_value = self.query_one("#input_box", Input).value
        self.post_message(self.Submitted(sender=self, value=input_value))

    def update_prompt(self, label: str = "", placeholder: str = "", value: str = "", border_title: str = "") -> None:
        if label:
            self.query_one("#input_label", Label).update(label)
        if placeholder:
            self.query_one("#input_box", Input).placeholder = placeholder
        if value:
            self.query_one("#input_box", Input).value = value
        if border_title:
            self.query_one("#input_pane", Vertical).border_title = border_title

    def focus(self, scroll_visible: bool = True) -> Self:
        super().focus()
        self.query_one("#input_box", Input).focus()