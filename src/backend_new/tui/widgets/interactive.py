from typing import Self, Iterable, Any

from rich.console import ConsoleRenderable, RichCast
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, HorizontalGroup, Container, HorizontalScroll
from textual.message import Message
from textual.visual import SupportsVisual, Visual
from textual.widget import Widget
from textual.widgets import Label, Input, Button, DataTable
from textual.widgets._data_table import CellType


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


class TableSelect(Widget):
    DEFAULT_CSS = """
    #select_pane {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-align: center;
        border-title-style: bold;
        padding: 1 2;
        
        height: auto;
    }
    
    #input_table {
        height: auto;
    }
    
    .horizontal_scroll {
        width: 100%;
        height: auto;
    }
    
    #nav_buttons {
        width: 100%;
        
        content-align: right middle;
        align: right middle;
    }
    
    #nav_buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, extra_buttons: Iterable[Button], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_buttons = extra_buttons

    def compose(self) -> ComposeResult:
        with Vertical(id="select_pane"):
            yield Label(id="input_table_header")
            with HorizontalScroll(classes="horizontal_scroll"):
                yield DataTable(
                    cursor_type="row",
                    zebra_stripes=True,
                    id="input_table"
                )

            yield Label(id="table_page_footer")

            with HorizontalGroup(id="nav_buttons"):
                yield Button(id="__select__", variant="success", label="Select")
                for button in self.extra_buttons: yield button


    class Submitted(Message):
        def __init__(self, sender: Widget, value: Any) -> None:
            self.value = value
            self.widget = sender
            super().__init__()

        @property
        def control(self):
            return self.widget

    class ButtonPressed(Message):
        def __init__(self, sender: Widget, value: Any) -> None:
            self.value = value
            self.widget = sender
            super().__init__()

        @property
        def control(self):
            return self.widget



    @property
    def selected(self) -> int:
        return self.query_one("#input_table", DataTable).cursor_row

    @property
    def table_footer_content(self) -> ConsoleRenderable | RichCast | str | SupportsVisual | Visual:
        data_table_footer = self.query_one("#table_page_footer", Label).content
        return data_table_footer

    @table_footer_content.setter
    def table_footer_content(self, value: ConsoleRenderable | RichCast | str | SupportsVisual | Visual) -> None:
        data_table_footer = self.query_one("#table_page_footer", Label)
        data_table_footer.content = value

    @property
    def table_footer_visible(self) -> bool:
        return self.query_one("#table_page_footer", Label).display

    @table_footer_visible.setter
    def table_footer_visible(self, value: bool) -> None:
        self.query_one("#table_page_footer", Label).display = value

    @property
    def table_header_content(self) -> ConsoleRenderable | RichCast | str | SupportsVisual | Visual:
        data_table_header = self.query_one("#input_table_header", Label).content
        return data_table_header

    @table_header_content.setter
    def table_header_content(self, value: ConsoleRenderable | RichCast | str | SupportsVisual | Visual):
        self.query_one("#input_table_header", Label).content = value



    @on(DataTable.RowSelected, "#input_table")
    def handle_table_select(self) -> None:
        val = self.selected
        self.post_message(self.Submitted(self, val))

    @on(Button.Pressed, "#__select__")
    def handle_select_pressed(self) -> None:
        self.handle_table_select()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "__select__":
            return

        self.post_message(self.ButtonPressed(self, event.button.id))



    def add_columns(self, columns: Iterable[str]) -> None:
        data_table_widget = self.query_one("#input_table", DataTable)
        data_table_widget.add_columns(*columns)

    def add_rows(self, rows: Iterable[Iterable[CellType]]) -> None:
        data_table_widget = self.query_one("#input_table", DataTable)
        data_table_widget.add_rows(rows)

    def clear_rows(self, clear_columns: bool = True) -> None:
        data_table_widget = self.query_one("#input_table", DataTable)
        data_table_widget.clear(columns=clear_columns)


    def button_visible(self, button_id: str, value: bool) -> None:
        if button_id.startswith("#"):
            self.query_one(button_id, Button).display = value
        else:
            self.query_one(f"#{button_id}", Button).display = value
