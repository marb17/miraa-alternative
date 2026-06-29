from typing import Self, Iterable

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, HorizontalGroup, Container
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, Input, Button


class InputSubmit(Widget):
    DEFAULT_CSS = """
    #input_box {
        width: 1fr;
    }
    
    #input_container {
        height: auto;
    }
    
    #input_label {
        padding: 0 1;
    }
    
    .extra_button {
        margin: 0 0 0 1;
    }
    
    #button_con {
        width: auto;
        height: auto;
    }
    
    #submit_input {
        width: auto;
    }
    """

    class Submitted(Message):
        def __init__(self, sender: Widget, value: str, triggered_by: str):
            super().__init__()
            self.value = value
            self.triggered_by = triggered_by
            self.sender_widget = sender

        @property
        def control(self) -> Widget:
            """Return the widget that sent this message."""
            return self.sender_widget

    def __init__(self, label: str = "", placeholder: str = "", default_value: str = "", extra_buttons: Iterable[Button] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_text = label
        self.placeholder_text = placeholder
        self.default_value = default_value
        self.extra_buttons = extra_buttons


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
                with HorizontalGroup(id="button_con"):
                    yield Button("Submit", id="submit_input", variant="success")
                    if self.extra_buttons:
                        for button in self.extra_buttons:
                            button.add_class("extra_button")
                            yield button

    @property
    def value(self):
        try:
            return self.query_one("#input_box", Input).value
        except Exception:
            return self.default_value

    @on(Button.Pressed, "#submit_input")
    def action_button_submit_pressed(self) -> None:
        self.action_submit(triggered_by="submit")

    @on(Input.Submitted, "#input_box")
    def action_input_submitted(self) -> None:
        self.action_submit(triggered_by="submit")

    @on(Button.Pressed)
    def handle_extra_buttons(self, event: Button.Pressed):
        if event.button.id is None:
            raise Exception("please put id on extra buttons")

        if event.button.id != "submit_input":
            self.action_submit(triggered_by=event.button.id)

    def action_submit(self, triggered_by: str) -> None:
        input_value = self.query_one("#input_box", Input).value
        self.post_message(self.Submitted(sender=self, value=input_value, triggered_by=triggered_by))

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


class PasteOnlyInput(Input):
    """An Input widget that blocks standard typing and only allows pasting."""

    def _on_key(self, event) -> None:
        is_paste_shortcut = event.key in ("ctrl+v", "ctrl+y")

        is_navigation = event.key in ("tab", "shift+tab", "enter")

        is_backspace = event.key == "backspace"

        if not (is_paste_shortcut or is_navigation):
            # Block standard character insertions, backspaces, and deletes
            event.prevent_default()
        if is_backspace:
            self.value = ""


class PasteOnlyInputSubmit(Widget):
    DEFAULT_CSS = """
    #input_box {
        width: 1fr;
    }
    
    #input_container {
        height: auto;
    }
    
    #input_label {
        padding: 0 1;
    }
    
    .extra_button {
        margin: 0 0 0 1;
    }
    
    #button_con {
        width: auto;
        height: auto;
    }
    
    #submit_input {
        width: auto;
    }
    """

    class Submitted(Message):
        def __init__(self, sender: Widget, value: str, triggered_by: str):
            super().__init__()
            self.value = value
            self.triggered_by = triggered_by
            self.sender_widget = sender

        @property
        def control(self) -> Widget:
            """Return the widget that sent this message."""
            return self.sender_widget

    def __init__(self, label: str = "", placeholder: str = "", default_value: str = "", extra_buttons: Iterable[Button] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_text = label
        self.placeholder_text = placeholder
        self.default_value = default_value
        self.extra_buttons = extra_buttons

    def compose(self) -> ComposeResult:
        with Vertical(id="input_container"):
            if self.label_text != "" or True:
                yield Label(self.label_text, id="input_label")
            with HorizontalGroup(id="input_container"):
                yield PasteOnlyInput(
                    value=self.default_value,
                    placeholder=self.placeholder_text,
                    id="input_box"
                )
                with HorizontalGroup(id="button_con"):
                    yield Button("Submit", id="submit_input", variant="success")
                    if self.extra_buttons:
                        for button in self.extra_buttons:
                            button.add_class("extra_button")
                            yield button

    @property
    def value(self):
        try:
            return self.query_one("#input_box", PasteOnlyInput).value
        except Exception:
            return self.default_value

    @on(Button.Pressed, "#submit_input")
    def action_button_submit_pressed(self) -> None:
        self.action_submit(triggered_by="submit")

    @on(Input.Submitted, "#input_box")
    def action_input_submitted(self) -> None:
        self.action_submit(triggered_by="submit")

    @on(Button.Pressed)
    def handle_extra_buttons(self, event: Button.Pressed):
        if event.button.id is None:
            raise Exception("please put id on extra buttons")

        if event.button.id != "submit_input":
            self.action_submit(triggered_by=event.button.id)

    def action_submit(self, triggered_by: str) -> None:
        input_value = self.query_one("#input_box", Input).value
        self.post_message(self.Submitted(sender=self, value=input_value, triggered_by=triggered_by))

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