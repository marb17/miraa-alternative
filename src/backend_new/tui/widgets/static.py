from textual import events, work
from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.widget import Widget
from textual.widgets import Static, ProgressBar

from backend_new.extractors.downloader import Downloader


class SpotifyCurrentlyPlayingWidget(Widget):
    downloader = None
    response = None
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

    @work(thread=True)
    def action_authenticate(self) -> None:
        self.app.call_from_thread(self._client_authenticate)

    def _client_authenticate(self) -> None:
        self.downloader.cache_authenticate()

    @work(exclusive=True, thread=True)
    def update_data(self) -> None:
        self.response = self.downloader.get_current_playing_song()

        self.app.call_from_thread(self._update_widget_data)

    def _update_widget_data(self) -> None:
        self.notify("asdfdf")
        self.query_one("#title", Static).update("asdfjkl;")