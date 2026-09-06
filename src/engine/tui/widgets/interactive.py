from typing import Self, Iterable, Any, Literal

from rich.console import ConsoleRenderable, RichCast
from textual import on, events, work
from textual.app import ComposeResult
from textual.containers import Vertical, HorizontalGroup, Container, HorizontalScroll
from textual.dom import DOMNode
from textual.message import Message
from textual.visual import SupportsVisual, Visual
from textual.widget import Widget
from textual.widgets import Label, Input, Button, DataTable, Static, Switch, Checkbox

from engine.utils.functions.filesystem import write_config, read_config


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
                            if not button.id:
                                raise Exception("Please put id on extra buttons")
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
        for button in self.query(Button): button.disabled = True


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


class PasteOnlyInputSubmit(InputSubmit):
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

    def __init__(self, extra_buttons: Iterable[Button] = None, *args, **kwargs):
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
                if self.extra_buttons:
                    for button in self.extra_buttons: yield button
                yield Button(id="__select__", variant="success", label="Select")



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

    def add_rows(self, rows: Iterable[Iterable[str]]) -> None:
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


class FinishedAnyKeyContinue(Widget):
    can_focus = True

    DEFAULT_CSS = """
    #finished {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-align: center;
        border-title-style: bold;
        padding: 1 2;
        
        height: auto;
        width: auto;
    }
    
    #finished_text {
        width: auto
    }
    """



    class Closed(Message):
        def __init__(self, sender: Widget, message: Any) -> None:
            super().__init__()
            self.sender = sender
            self.message = message

        @property
        def control(self) -> DOMNode | None:
            return self.sender



    def __init__(self, message: str, press_key_add: bool = True, extra_static: Iterable[Static] = None, value: Any = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.message = message
        self.press_key_add = press_key_add
        self.extra_static = extra_static if extra_static else []
        self.value = value



    @property
    def dismiss_value(self) -> Any:
        return self.value

    @dismiss_value.setter
    def dismiss_value(self, value: Any) -> None:
        self.value = value



    def compose(self) -> ComposeResult:
        text = self.message
        if self.press_key_add:
            text += ", press any key to continue[blink]_[/]"

        with Vertical(id="finished"):
            yield Static(id="finished_text", content=text)
            for static in self.extra_static:
                static.classes = "extra_static"
                yield static



    def _on_mount(self, event: events.Mount) -> None:
        self.focus()

    def _on_key(self, event: events.Key) -> None:
        self.post_message(self.Closed(self, self.value))



    def update_static(self, static_id: str, value: str) -> None:
        if static_id.startswith("#"):
            pass
        else:
            static_id = "#" + static_id

        self.query_one(f"#{static_id}", Static).update(value)


class ConfigOption(Widget):
    DEFAULT_CSS = """
        #hor_option {
            height: auto;
            margin: 0 0 0 0;
            layout: horizontal;
        }
        
        #hor_option Label {
            align: left middle;
            content-align: left middle;
            
            width: 100%;
            height: 100%;
        }
        
        #option {
            height: auto;
            margin: 0 0 0 0;
        }
        
        #option Label {
            margin: 0 1;
        }
        
        #flat_option {
            height: auto;
        }
    """



    class Changed(Message):
        def __init__(self, sender: Widget, message: Any) -> None:
            super().__init__()
            self.sender = sender
            self.value = message

        @property
        def control(self) -> DOMNode | None:
            return self.sender



    @property
    def value(self) -> Any:
        if self.config_type == "switch":
            return self.query_one("#switch_widget", Switch).value
        elif self.config_type == "input_int":
            return int(self.query_one("#input_widget", Input).value)
        elif self.config_type == "input_float":
            return float(self.query_one("#input_widget", Input).value)
        elif self.config_type == "input_str":
            return str(self.query_one("#input_widget", Input).value)
        elif self.config_type == "checkbox":
            return self.query_one("#checkbox_widget", Checkbox).value
        return None

    @value.setter
    def value(self, value: Any) -> None:
        with self.prevent(Switch.Changed, Input.Changed, Checkbox.Changed):
            if self.config_type == "switch":
                self.query_one("#switch_widget", Switch).value = value
            elif self.config_type in ["input_int", "input_float", "input_str"]:
                self.query_one("#input_widget", Input).value = str(value)
            elif self.config_type == "checkbox":
                self.query_one("#checkbox_widget", Checkbox).value = value

    @property
    def password(self) -> Any:
        if self.config_type in ["input_int", "input_float", "input_str"]:
            return self.query_one("#input_widget", Input).password
        return None

    @password.setter
    def password(self, value: Any) -> None:
        if self.config_type in ["input_int", "input_float", "input_str"]:
            self.query_one("#input_widget", Input).password = value



    def __init__(self, config_type: Literal["switch", "input_int", "input_float", "input_str", "checkbox"],
                 label: str,
                 widget_id: str,
                 placeholder: str = "",
                 json_keys: list[str] = None,
                 enable_config_write: bool = True,
                 default_value: Any = None,
                 input_password: bool = False,
                 *args, **kwargs) -> None:

        """
        :param config_type: The option type
        :type config_type: Literal["switch", "input_int", "input_float", "input_str", "checkbox"]
        :param label: The label, depends on what config type is used
        :type label: str
        :param widget_id: The textual widget ID
        :type widget_id: str
        :param placeholder: The placeholder for input types
        :type placeholder: str
        :param json_keys: The keys leading to an option, (JSON file)
        :type json_keys: list[str]
        :param enable_config_write: Enable writing to a JSON file
        :type enable_config_write: bool
        :param default_value: The default value to use if enable_config_write if False
        :type default_value: bool
        :param input_password: Hides text in inputs
        :type input_password: bool
        """

        super().__init__(id=widget_id, *args, **kwargs)
        self.config_type = config_type
        self.label = label
        self.placeholder = placeholder
        if json_keys:
            self.json_keys = json_keys
        else:
            self.json_keys = None
        self.enable_config_write = enable_config_write if json_keys else False
        self.default_value = default_value if not self.enable_config_write else None
        self._password = input_password



    def compose(self) -> ComposeResult:
        if self.config_type == "switch":
            with Container(id="hor_option"):
                yield Switch(id="switch_widget")
                yield Label(self.label)
        elif self.config_type == "input_int":
            with Container(id="option"):
                yield Label(self.label)
                yield Input(id="input_widget",
                            placeholder=self.placeholder,
                            type="integer",
                            password=self._password)
        elif self.config_type == "input_float":
            with Container(id="option"):
                yield Label(self.label)
                yield Input(id="input_widget",
                            placeholder=self.placeholder,
                            type="number",
                            password=self._password)
        elif self.config_type == "input_str":
            with Container(id="option"):
                yield Label(self.label)
                yield Input(id="input_widget",
                            placeholder=self.placeholder,
                            type="text",
                            password=self._password)
        elif self.config_type == "checkbox":
            with Container(id="flat_option"):
                yield Checkbox(self.label, id="checkbox_widget")



    def _on_mount(self, event: events.Mount) -> None:
        self.refresh_value()



    @work(thread=True)
    def refresh_value(self) -> None:
        if self.enable_config_write:
            config_data = read_config()
            if self.json_keys:
                for key in self.json_keys:
                    config_data = config_data[key]

            if isinstance(config_data, dict) or isinstance(config_data, list):
                raise Exception("Wrong key traversal")

            self.value = config_data
        else:
            self.value = self.default_value



    @on(Switch.Changed)
    def handle_switch_message(self, event: Switch.Changed) -> None:
        self.post_message(self.Changed(self, self.value))

    @on(Input.Changed)
    def handle_input_message(self, event: Input.Changed) -> None:
        self.post_message(self.Changed(self, self.value))

    @on(Checkbox.Changed)
    def handle_checkbox_message(self, event: Checkbox.Changed) -> None:
        self.post_message(self.Changed(self, self.value))



    @on(Switch.Changed)
    def switch_write_config(self, event: Switch.Changed) -> None:
        if self.enable_config_write:
            write_config(self.value, self.json_keys)

    @on(Input.Changed)
    def input_write_config(self, event: Input.Changed) -> None:
        if self.enable_config_write:
            write_config(self.value, self.json_keys)

    @on(Checkbox.Changed)
    def input_write_checkbox(self, event: Checkbox.Changed) -> None:
        if self.enable_config_write:
            write_config(self.value, self.json_keys)