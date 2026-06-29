from textual import events
from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.widget import Widget
from textual.widgets import Static, ProgressBar

from backend_new.extractors.downloader import Downloader


class SpotifyCurrentlyPlayingWidget(Widget):
    downloader = None
    playing_song = dict()

    def compose(self) -> ComposeResult:
        yield Static("Title", id="title")
        yield Static("Artist", id="artist")
        with HorizontalGroup():
            yield Static("Timestamp", id="timestamp")
            yield ProgressBar(total=100,
                              show_percentage=False,
                              show_eta=False,
                              id="progressbar")
            yield Static("End Timestamp", id="end_timestamp")

    def _on_mount(self, event: events.Mount) -> None:
        self.downloader = Downloader()
        self.downloader.cache_authenticate()

        self.query_one("#title", Static).content = self.downloader.get_current_playing_song()