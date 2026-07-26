from pathlib import Path
from typing import Any

from textual import events, work, on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Label, Button, ContentSwitcher, Select, Static, RichLog, TabbedContent, \
    Tabs, Tab
from textual.binding import Binding

from engine.core.workflow import WorkflowManager
from engine.tui.screens.config.config import ProcessesMenu
from engine.tui.widgets.interactive import FinishedAnyKeyContinue
from engine.utils.classes.dataclasses import UIPromptRequest
from engine.utils.functions.filesystem import all_available_temp_json_files, read_config, read_json_file


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
    
    #finished {
        align: center middle;
        content-align: center middle;
    }
    
    FinishedAnyKeyContinue {
        align: center middle;
        content-align: center middle;
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
                    yield Tabs(
                        Tab("Genius", id="genius_metadata"),
                        Tab("Audio Stems", id="audio_separation"),
                        Tab("Analysis", id="split_and_tag"),
                        Tab("Translate", id="translate_lyrics")
                    )

                    yield Static(id="current_process_display")
                    yield RichLog(id="process_log")

                with Vertical(id="finished"):
                    yield FinishedAnyKeyContinue(message="Finished processing")



    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#choose_json", Vertical).border_title = "Song Processing"
        self.query_one("#options", Vertical).border_title = "Options"
        self.update_json_select()



    @work(thread=True)
    def update_json_select(self) -> None:
        all_files = all_available_temp_json_files()
        self.json_options = [(file["name"], file["path"]) for file in all_files]

        self.update_select_json_widget()

    def update_select_json_widget(self) -> None:
        self.query_one("#select_json", Select).set_options(self.json_options)



    @work(thread=True)
    def run_work(self) -> None:
        config = read_config()["skip_processes"]
        song_data = read_json_file(self.selected_json_file)

        if song_data.get("genius_data"):
            self.app.call_from_thread(self.update_ui_for_prompt, UIPromptRequest(
                type="log",
                message="Genius data already exists, skipping"
            ))
        else:
            if not config["genius_metadata"]:
                with WorkflowManager() as manager:
                    pipeline = manager.extract_genius_metadata(self.selected_json_file)

                    try:
                        prompt_request = next(pipeline)

                        while True:
                            user_answer = self.app.call_from_thread(self.update_ui_for_prompt, prompt_request)
                            prompt_request = pipeline.send(user_answer)
                    except StopIteration as e:
                        if e.value is True:
                            ...
                        else:
                            ...

        if song_data.get("vocal_separation", {}).get("stems", {}).get("vocal"):
            self.app.call_from_thread(self.update_ui_for_prompt, UIPromptRequest(
                type="log",
                message="Song has already been separated, skipping"
            ))
        else:
            if not config["vocal_separation"]:
                with WorkflowManager() as manager:
                    pipeline = manager.separate_vocals(self.selected_json_file)

                    try:
                        prompt_request = next(pipeline)

                        while True:
                            user_answer = self.app.call_from_thread(self.update_ui_for_prompt, prompt_request)
                            prompt_request = pipeline.send(user_answer)
                    except StopIteration as e:
                        if e.value is True:
                            ...
                        else:
                            ...

        if song_data.get("translated_lyrics"):
            self.app.call_from_thread(self.update_ui_for_prompt, UIPromptRequest(
                type="log",
                message="Song has already been translated, skipping"
            ))
        else:
            if not config["translate_lyrics"]:
                with WorkflowManager() as manager:
                    pipeline = manager.translate_lyrics(self.selected_json_file)

                    try:
                        prompt_request = next(pipeline)

                        while True:
                            user_answer = self.app.call_from_thread(self.update_ui_for_prompt, prompt_request)
                            prompt_request = pipeline.send(user_answer)
                    except StopIteration as e:
                        if e.value is True:
                            ...
                        else:
                            ...


        self.app.call_from_thread(self.update_ui_for_prompt, UIPromptRequest(
            type="hidden_request",
            sub_type="__finished__",
            message=""
        ))

    def update_ui_for_prompt(self, prompt_request: UIPromptRequest) -> None:
        switcher = self.query_one("#main_content_switcher", ContentSwitcher)

        if prompt_request.type == "log":
            self.query_one("#process_log", RichLog).write(prompt_request.message)
        elif prompt_request.type == "hidden_request":
            if prompt_request.sub_type == "__finished__":
                switcher.current = "finished"



    @on(Button.Pressed, "#confirm_json")
    def select_json_file(self):
        select_value = self.query_one("#select_json", Select).value

        if select_value == Select.NULL:
            self.notify("Please choose a song", severity="warning")
            return

        self.selected_json_file = select_value

        self.query_one("#main_content_switcher", ContentSwitcher).current = "process_menu"

        self.run_work()



    def action_self_dismiss(self, value: Any) -> None:
        self.dismiss(value)

    @on(FinishedAnyKeyContinue.Closed)
    def close_menu(self) -> None:
        self.action_self_dismiss(True)



        