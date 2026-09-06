from textual import events, work, on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Container
from textual.events import ScreenSuspend, ScreenResume
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Static, ProgressBar

from engine.extractors.downloader import Downloader


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
        max-width: 100%;
        
        text-overflow: ellipsis;
        text-wrap: nowrap;
    }
    
    #title_con {
        width: 1fr;

        height: auto;
        
        content-align: left middle;
        align: left middle;
    }
    
    #artist {
        color: $text-muted;
        content-align: left middle;
        
        width: auto;
        max-width: 100%;

        text-overflow: ellipsis;
        text-wrap: nowrap;
    }
    
    #is_playing {
        margin: 0 2 0 0;
    }
    
    #song_data {
        height: auto;
        width: 100%;
        
        content-align: left middle;
        align: left middle;
    }
    
    .text_line {
        width: 100%;
    }
    
    #up_next_song {
        dock: right;
        width: auto;
        max-width: 50%;
        
        margin: 0 0 0 5;
        
        color: 30%;
        background: 10%;
        
        text-overflow: ellipsis;
        text-wrap: nowrap;
    }
    
    #static_up_next {
        dock: right;
        width: auto;
        
        padding: 0 0 0 5;
        
        color: 30%;
    }
    """

    downloader = None
    playing_song_response = None
    queue_response = None
    current_progress_ms = 0
    song_length_ms = 0
    is_playing = False
    playing_song = dict()

    def compose(self) -> ComposeResult:
        with Container(id="main_widget"):
            with Container(id="song_data"):

                with HorizontalGroup(classes="text_line"):
                    with Container(id="title_con"):
                        yield Static("Disabled", id="title")

                    yield Static("Next", id="static_up_next")

                with HorizontalGroup(classes="text_line"):
                    yield Static("Disabled", id="artist")
                    yield Static("Disabled", id="up_next_song")

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
        if self.app.use_spotify_token:
            self.downloader = Downloader()
            self.set_interval(0.1, self.increment_timestamp)
            self.update_timer = self.set_interval(2, self.update_data)

    @property
    def song_available(self) -> bool:
        return bool(self.playing_song_response)



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


        # CURRENT SONG
        playing_song_pipeline = self.downloader.get_current_playing_song()
        try:
            prompt_request = next(playing_song_pipeline)

            if prompt_request.type == "hidden_request" and prompt_request.message == 401:
                self.notify(f"Expired Token (current song)")
                self.app.call_from_thread(self._client_no_cache_authenticate)
                playing_song_pipeline.send(True)

        except StopIteration as e:
            self.playing_song_response = e.value

        if self.playing_song_response is None:
            self.is_playing = False
        else:
            self.is_playing = self.playing_song_response.get("is_playing")

        self.app.call_from_thread(self._update_widget_data)


        # SPOTIFY QUEUE
        queue_pipeline = self.downloader.get_user_spotify_queue()
        try:
            prompt_request = next(queue_pipeline)

            if prompt_request.type == "hidden_request" and prompt_request.message == 401:
                self.notify("Expired Token (spotify queue)")
                self.app.call_from_thread(self._client_no_cache_authenticate)
                queue_pipeline.send(True)

        except StopIteration as e:
            self.queue_response = e.value



    def handle_start_updating(self):
        if not self.app.use_spotify_token:
            return

        self.update_timer.resume()

    def handle_stop_updating(self) -> None:
        if not self.app.use_spotify_token:
            return

        self.update_timer.pause()



    def increment_timestamp(self, increment_by_ms: int = 100) -> None:
        if self.playing_song_response is None or not self.is_playing:
            return

        if self.current_progress_ms + increment_by_ms >= self.song_length_ms:
            self.current_progress_ms = self.song_length_ms + 1
        else:
            self.current_progress_ms += increment_by_ms
        self._update_timestamp()
        self._update_progressbar()



    def _update_widget_data(self) -> None:
        is_playing_static = self.query_one("#is_playing", Static)
        up_next_static = self.query_one("#up_next_song", Static)

        if not self.app.use_spotify_token:
            self.query_one("#title", Static).update("Disabled")
            self.query_one("#artist", Static).update("Disabled")
            up_next_static.update("Disabled")
            self.query_one("#timestamp", Static).update("--:--")
            self.query_one("#end_timestamp", Static).update("--:--")

            self.song_length_ms = 0
            self.current_progress_ms = 0

            is_playing_static.update("⏹")
            return

        if self.playing_song_response is None:
            self.query_one("#title", Static).update("Nothing Playing")
            self.query_one("#artist", Static).update("-")
            up_next_static.update("Nothing Playing")
            self.query_one("#timestamp", Static).update("--:--")
            self.query_one("#end_timestamp", Static).update("--:--")

            self.song_length_ms = 0
            self.current_progress_ms = 0

            is_playing_static.update("⏹")
            return


        title, artist = self.downloader.get_title_artist(self.playing_song_response["item"]).values()
        self.current_progress_ms = self.playing_song_response["progress_ms"]

        self.song_length_ms = self.playing_song_response["item"]["duration_ms"]
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


        # UPNEXT SECTION
        if self.queue_response:
            try:
                up_next_static.update(
                    f"{self.queue_response["queue"][0]["name"]} - {self.queue_response["queue"][0]["artists"][0]["name"]}"
                )
            except IndexError:
                up_next_static.update("-")
        else:
            ...



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
