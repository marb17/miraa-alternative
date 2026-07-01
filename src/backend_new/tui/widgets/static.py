from textual import events, work, on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Container
from textual.events import ScreenSuspend, ScreenResume
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Static, ProgressBar

from backend_new.extractors.downloader import Downloader


class SpotifyCurrentlyPlayingWidget(Widget):
    TITLE_ARTIST_ALIGN = "left"

    DEFAULT_CSS = f"""
    #main_widget {{
        height: auto;
    }}
    
    #progress_group {{
        width: 100%;
    }}
    
    #progress_group Static {{
        width: auto;
        height: auto;
    }}
    
    #progress_group ProgressBar {{
        width: 1fr;
        height: auto;
    }}
    
    #progress_group ProgressBar Bar {{
        width: 100%;
        margin: 0 2;
    }}
    
    #progress_group ProgressBar Bar > .bar--bar {{
        color: $primary;
        background: $accent 30%;
    }}
    
    #title {{
        background: $secondary;
        text-style: bold;
        width: auto;
    }}
    
    #title_con {{
        width: 100%;
        height: auto;
        
        content-align: {TITLE_ARTIST_ALIGN} middle;
        align: {TITLE_ARTIST_ALIGN} middle;
    }}
    
    #artist {{
        color: $text-muted;
        content-align: {TITLE_ARTIST_ALIGN} middle;
    }}
    
    #is_playing {{
        margin: 0 2 0 0;
    }}
    
    #song_data {{
        height: auto;
        width: 100%;
        
        content-align: {TITLE_ARTIST_ALIGN} middle;
        align: {TITLE_ARTIST_ALIGN} middle;
    }}
    """

    downloader = None
    response = None
    current_progress_ms = 0
    song_length_ms = 0
    is_playing = False
    playing_song = dict()

    def compose(self) -> ComposeResult:
        with Container(id="main_widget"):
            with Container(id="song_data"):
                with Container(id="title_con"):
                    yield Static("Disabled", id="title")
                yield Static("Disabled", id="artist")
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
        self.update_timer = self.set_interval(2, self.update_data)

    @property
    def song_available(self) -> bool:
        return bool(self.response)

    @work(thread=True)
    def action_authenticate(self) -> None:
        if not self.app.use_spotify_token:
            return

        self.app.call_from_thread(self._client_authenticate)

    def _client_authenticate(self) -> None:
        if not self.app.use_spotify_token:
            return

        self.downloader.cache_authenticate()
        self.update_data()

    def _client_no_cache_authenticate(self) -> None:
        if not self.app.use_spotify_token:
            return

        self.downloader.authenticate()

    @work(exclusive=True, thread=True)
    def update_data(self) -> None:
        if not self.app.use_spotify_token:
            self.app.call_from_thread(self._update_widget_data)
            return

        if getattr(self.downloader, "_sp_token") is None:
            return

        pipeline = self.downloader.get_current_playing_song()
        try:
            prompt_request = next(pipeline)

            if prompt_request.type == "hidden_request" and prompt_request.message == 401:
                self.notify("Expired Token")
                self.app.call_from_thread(self._client_no_cache_authenticate)
                pipeline.send(True)

        except StopIteration as e:
            self.response = e.value

        if self.response is None:
            self.is_playing = False
        else:
            self.is_playing = self.response.get("is_playing")

        self.app.call_from_thread(self._update_widget_data)

    def handle_start_updating(self):
        self.update_timer.resume()

    def handle_stop_updating(self) -> None:
        self.update_timer.pause()

    def increment_timestamp(self, increment_by_ms: int = 100) -> None:
        if self.response is None or not self.is_playing:
            return

        if self.current_progress_ms + increment_by_ms >= self.song_length_ms:
            self.current_progress_ms = self.song_length_ms + 1
        else:
            self.current_progress_ms += increment_by_ms
        self._update_timestamp()
        self._update_progressbar()


    def _update_widget_data(self) -> None:
        is_playing_static = self.query_one("#is_playing", Static)

        if not self.app.use_spotify_token:
            self.query_one("#title", Static).update("Disabled")
            self.query_one("#artist", Static).update("Disabled")
            self.query_one("#timestamp", Static).update("--:--")
            self.query_one("#end_timestamp", Static).update("--:--")

            self.song_length_ms = 0
            self.current_progress_ms = 0

            is_playing_static.update("⏹")
            return

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
