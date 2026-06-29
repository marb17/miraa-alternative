from textual import events, work
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Container
from textual.widget import Widget
from textual.widgets import Static, ProgressBar

from backend_new.extractors.downloader import Downloader


class SpotifyCurrentlyPlayingWidget(Widget):
    DEFAULT_CSS = """
    #main_widget {
        height: auto;
    }
    
    #progress_group {
        width: 100%;
    }
    
    #progress_group Static {
        width: auto;
        height: auto;
    }
    
    #progress_group ProgressBar {
        width: 1fr;
        height: auto;
    }
    
    #progress_group ProgressBar Bar {
        width: 100%;
        margin: 0 2;
    }
    
    #progress_group ProgressBar Bar > .bar--bar {
        color: $primary;
        background: $accent 30%;
    }
    
    #title {
        background: $secondary;
        text-style: bold;
        width: auto;
    }
    
    #artist {
        color: $text-muted
    }
    
    #is_playing {
        margin: 0 2 0 0;
    }
    """

    downloader = None
    response = None
    current_progress_ms = 0
    song_length_ms = 0
    is_playing = False
    playing_song = dict()

    def compose(self) -> ComposeResult:
        with Container(id="main_widget"):
            yield Static("Title", id="title")
            yield Static("Artist", id="artist")
            yield Static()
            with HorizontalGroup(id="progress_group"):
                yield Static("--:--", id="timestamp")
                yield ProgressBar(total=100,
                                  show_percentage=False,
                                  show_eta=False,
                                  id="progressbar")
                yield Static("⏹", id="is_playing")
                yield Static("--:--", id="end_timestamp")

    def _on_mount(self, event: events.Mount) -> None:
        self.downloader = Downloader()
        self.set_interval(0.1, self.increment_timestamp)

    @work(thread=True)
    def action_authenticate(self) -> None:
        self.app.call_from_thread(self._client_authenticate)

    def _client_authenticate(self) -> None:
        self.downloader.cache_authenticate()
        self.update_data()

    @work(exclusive=True, thread=True)
    def update_data(self) -> None:
        if getattr(self.downloader, "_sp_token") is None:
            self.app.call_from_thread(self._client_authenticate)
            return

        self.response = self.downloader.get_current_playing_song()

        if self.response is None:
            self.is_playing = False
        else:
            self.is_playing = self.response.get("is_playing")

        self.app.call_from_thread(self._update_widget_data)

    def increment_timestamp(self, increment_by_ms: int = 100) -> None:
        if self.response is None or not self.is_playing:
            return

        self.current_progress_ms += increment_by_ms
        self._update_timestamp()
        self._update_progressbar()


    def _update_widget_data(self) -> None:
        is_playing_static = self.query_one("#is_playing", Static)

        if self.response is None:
            self.query_one("#title", Static).update("Nothing Playing")
            self.query_one("#artist", Static).update("-")
            self.query_one("#timestamp", Static).update("--:--")
            self.query_one("#end_timestamp", Static).update("--:--")

            self.song_length_ms = 0
            self.current_progress_ms = 0

            is_playing_static.update("⏹")

            return


        title, artist = self.downloader.get_title_artist(self.response["item"]).values()
        self.current_progress_ms = self.response["progress_ms"]

        self.song_length_ms = self.response["item"]["duration_ms"]
        song_length_timestamp = self.downloader.milliseconds_to_minutes_and_seconds(
            self.song_length_ms
        )

        self.query_one("#title", Static).update(title)
        self.query_one("#artist", Static).update(artist)
        self.query_one("#end_timestamp", Static).update(song_length_timestamp)

        self._update_timestamp()
        self._update_progressbar()

        if self.is_playing:
            is_playing_static.update("▶")
        else:
            is_playing_static.update("⏸")

    def _update_timestamp(self) -> None:
        timestamp = self.downloader.milliseconds_to_minutes_and_seconds(
            self.current_progress_ms
        )
        self.query_one("#timestamp", Static).update(timestamp)

    def _update_progressbar(self) -> None:
        progress_bar_widget = self.query_one("#progressbar", ProgressBar)
        progress_bar_widget.update(
            total=self.song_length_ms,
            progress=self.current_progress_ms
        )
