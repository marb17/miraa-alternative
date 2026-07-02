import threading
import webbrowser

import requests.exceptions
from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import Container, CenterMiddle
from textual.screen import ModalScreen
from textual.widgets import Static, Link, Button
from uc_micro.properties import Any

from backend_new.extractors.downloader import Downloader
from backend_new.tui.widgets.interactive import PasteOnlyInputSubmit
from backend_new.utils.functions.filesystem import write_config


class SpotifyAuthenticateScreen(ModalScreen):
    DEFAULT_CSS = """
    #fullscreen {
        width: 100%;
        height: 100%;

        align: center middle;
        content-align: center middle;
        
        hatch: right $accent 10%;
    }

    #main_box {
        border: solid $secondary;
        border-title-color: $primary;
        border-title-style: bold;
        border-title-align: center;

        width: 85%;
        height: auto;

        align: center middle;
        content-align: center middle;

        padding: 1 2;
    }

    #main_box Static {

    }

    #main_box PasteOnlyInputSubmit {
        height: auto;
        width: 100%;
    }
    """

    spotify_client = None
    pipeline = None
    url = ""

    def compose(self) -> ComposeResult:
        with Container(id="fullscreen"):
            with CenterMiddle(id="main_box"):
                yield Static(
                    "This is probably your first time logging in to miraa-alternative.\nWe require you to link your spotify account to ensure all features work.\nPlease click the link below to authorize your spotify account.")
                yield Static()
                yield Link(
                    url=self.url,
                    text="Click Me!"
                )
                yield Static()
                yield Static(
                    "Don't worry if the website can't be reached, all services are ran locally on your machine, so there is no website to redirect to.\n\nPlease copy the link you have been redirected to after following the instructions below.\n\nP.S. you can only paste in the input box, and if you can't open the link press space to copy the link.")
                yield PasteOnlyInputSubmit(
                    placeholder="Enter Link Address",
                    id="input_box",
                    extra_buttons=[Button(label="Open Link", variant="primary", id="btn_open_link"),
                                   Button(label="Skip", variant="warning", id="btn_skip")],
                )

    def _on_mount(self, event: events.Mount) -> None:
        self.query_one("#main_box", CenterMiddle).border_title = "Spotify Authentication"

        self.spotify_client = Downloader()
        self.pipeline = self.spotify_client.authenticate()

        self.advance_pipeline()

    @on(PasteOnlyInputSubmit.Submitted, "#input_box")
    def handle_submit(self, event: PasteOnlyInputSubmit.Submitted) -> None:
        if event.triggered_by == "submit":
            self.advance_pipeline(response=event.value)

        elif event.triggered_by == "btn_open_link":
            try:
                webbrowser.open(self.url)
            except Exception as e:
                self.notify(f"Failed to open {self.url}, error: {e}")

        elif event.triggered_by == "btn_skip":
            write_config(False, ["spotify_downloader", "token"])
            self.dismiss()

    def _on_key(self, event: events.Key) -> None:
        if event.key == "space":
            # import pyperclip
            try:
                # pyperclip.copy(self.url)
                self.app.copy_to_clipboard(self.url)
            except Exception as e:
                self.notify(f"Failed to copy {self.url}, error: {e}")
            self.notify("Successfully copied URL!")

    def _update_url(self, url: str):
        self.url = url
        self.query_one(Link).url = self.url

    @work(thread=True)
    def advance_pipeline(self, response: Any = None):
        try:
            if response is not None:
                message = self.pipeline.send(response)
            else:
                message = next(self.pipeline)

            new_url = message.extra_info["url"]
            self.app.call_from_thread(self._update_url, new_url)

        except StopIteration as e:
            self.app.call_from_thread(self.dismiss, e.value)
        except requests.exceptions.ConnectionError as e:
            self.app.call_from_thread(self.notify, f"You are not possibly connected to the internet.\n\n{e}", severity="error")
            self.app.call_from_thread(self.dismiss, False)
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Authentication Error: {e}", severity="error")
            self.app.call_from_thread(self.dismiss, False)
