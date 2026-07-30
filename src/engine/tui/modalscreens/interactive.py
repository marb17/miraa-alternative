from textual import events
from textual.app import ComposeResult
from textual.containers import CenterMiddle, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label, Button


class UnsavedConfirmationModalScreen(ModalScreen):
    DEFAULT_CSS = """
    #dialog_card {
        width: auto; 
        height: auto;
        
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
        border-title-align: center;
    }
    
    #dialog_msg {
        width: 100%;
        margin: 1 0;
        text-align: center;
    }
    
    #dialog_buttons {
        height: auto;
        width: auto;
        
        margin: 0 2 1 2;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.styles.align = ("center", "middle")

    def compose(self) -> ComposeResult:
        with CenterMiddle(id="dialog_card"):
            yield Label("⚠️ You have unsaved changes!\nWould you like to save before switching?", id="dialog_msg")
            with Horizontal(id="dialog_buttons"):
                yield Button("Save", variant="success", id="modal_save")
                yield Button("Discard", variant="error", id="modal_discard")
                yield Button("Cancel", variant="default", id="modal_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_save":
            self.dismiss("save")
        elif event.button.id == "modal_discard":
            self.dismiss("discard")
        elif event.button.id == "modal_cancel":
            self.dismiss("cancel")

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#dialog_card", CenterMiddle).border_title = "Unsaved Changes"