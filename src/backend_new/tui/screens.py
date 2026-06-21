from mmengine.runner import priority
from textual import events, containers, work
from textual.app import ComposeResult
from textual.widgets import Footer, Header, Switch, TabbedContent, TabPane, Checkbox, Label, Button
from textual.containers import Horizontal, Vertical, Container
from textual.screen import Screen, ModalScreen
from textual.binding import Binding

from backend_new.utils.helper_funcs import read_config, write_config

# default stuff prob like template
"""
DEFAULT_CSS = '''
    .section_container {
        height: auto;
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
    }
    
    .option_sections {
        padding: 0 1;
        align: center top;
        border: heavy $primary;
    }
    '''
"""

class SaveConfirmationModal(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog_card"):
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


class DownloadMenu(Horizontal):
    DEFAULT_CSS = """
        .section_container {
            height: auto;
            border: solid $secondary;
            border-title-style: bold;
            border-title-color: $primary;
        }

        .section_container Label {
        padding: 1;
        }

        .option_sections {
            padding: 0 1;
            align: center top;
            border: heavy $primary;
        }  
        """

    config_file_data = None
    anything_changed = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                with containers.HorizontalGroup(classes="section_container", id="downloader"):
                    yield Switch(id="downloader_cookies_switch")
                    yield Label("Use cookies for YouTube Downloader?")

        yield Footer()

    def _on_mount(self, event: events.Mount) -> None:
        downloader = self.query_one("#downloader", containers.HorizontalGroup)
        downloader.border_title = "Downloader"

        self.config_file_data = read_config()

        youtube_cookies_switch = self.query_one("#downloader_cookies_switch", Switch)

        youtube_cookies_switch.value = self.config_file_data["youtube_downloader"]["use_cookies"]


    def on_switch_changed(self, event: Switch.Changed):
        self.anything_changed = True

        if event.control.id == "downloader_cookies_switch":
            self.config_file_data["youtube_downloader"]["use_cookies"] = event.value

    @work(thread=True)
    def action_update_config(self):
        write_config(self.config_file_data)


class ProcessesMenu(Horizontal):
    DEFAULT_CSS = """
    .section_container {
        height: auto;
        border: solid $secondary;
        border-title-style: bold;
        border-title-color: $primary;
    }
    
    .option_sections {
        padding: 0 1;
        align: center top;
        border: heavy $primary;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(classes="option_sections"):
                with Container(classes="section_container", id="skip_processes"):
                    yield Checkbox("Download Song", id="download_song_checkbox")
                    yield Checkbox("Genius Metadata", id="genius_metadata_checkbox")
                    yield Checkbox("Separate Stems", id="separate_stems_checkbox")
                    yield Checkbox("Split and Tag lyrics", id="split_and_tag_checkbox")
                    yield Checkbox("Translate Lyrics", id="translate_lyrics_checkbox")

    def _on_mount(self, event: events.Mount) -> None:
        skip_processes = self.query_one("#skip_processes", Container)
        skip_processes.border_title = "Skip Processes"

        config_file_data = read_config()
        initial_skip_processes = config_file_data["skip_processes"]

        download_song_checkbox = self.query_one("#download_song_checkbox", Checkbox)
        genius_metadata_checkbox = self.query_one("#genius_metadata_checkbox", Checkbox)
        separate_stems_checkbox = self.query_one("#separate_stems_checkbox", Checkbox)
        split_and_tag_checkbox = self.query_one("#split_and_tag_checkbox", Checkbox)
        translate_lyrics_checkbox = self.query_one("#translate_lyrics_checkbox", Checkbox)

        download_song_checkbox.value = initial_skip_processes["download_song"]
        genius_metadata_checkbox.value = initial_skip_processes["genius_metadata"]
        separate_stems_checkbox.value = initial_skip_processes["vocal_separation"]
        split_and_tag_checkbox.value = initial_skip_processes["split_and_tag"]
        translate_lyrics_checkbox.value = initial_skip_processes["translate_lyrics"]


class ConfigMenu(Screen):
    BINDINGS = [
        Binding("ctrl+x", "app.pop_screen", "Exit Menu", priority=True)
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with TabbedContent():
            with TabPane("Processes"):
                yield ProcessesMenu()
            with TabPane("Downloader"):
                yield DownloadMenu()