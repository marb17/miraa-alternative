from pathlib import Path

from textual import work, events
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, LoadingIndicator, Static

from engine.database.main_database import MainDatabase
from engine.tui.widgets.static import SongEntry
from engine.utils.classes.dataclasses import DatabaseEntry


class SongListView(Screen):
    DEFAULT_CSS = """
    #fullscreen {
        hatch: right $accent 10%;
    }
    """

    @work(thread=True)
    def fetch_songs(self) -> None:
        with MainDatabase() as db:
            songs = db.get_all_entries()
        self.app.call_from_thread(self.populate_songs, songs)

    def _on_mount(self, event: events.Mount) -> None:
        self.fetch_songs()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with VerticalScroll(id="fullscreen"):
            yield LoadingIndicator(id="loading_indicator")

    def populate_songs(self, songs: list[DatabaseEntry]):
        container = self.query_one("#fullscreen", VerticalScroll)

        try:
            self.query_one("#loading_indicator", LoadingIndicator).remove()
        except Exception:
            pass

        for song in songs:
            container.mount(SongEntry(song))
