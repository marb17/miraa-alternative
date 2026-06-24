# STANDARD LIBRARY
from pathlib import Path
from time import sleep, time
import json
from typing import Any
from collections.abc import Generator

# HELPER LIBRARIES
from backend_new.utils.helper_funcs import questionary_select, load_env_file, read_json_file

# PYPI LIBRARIES
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import questionary as q

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

# CONSTANTS
from backend_new.utils.constants import TEMP_DIR, CONFIG_FILE, UIPromptRequest


from backend_new.utils.logger import Logger
logger = Logger(__name__)

class Downloader:
    def __init__(self) -> None:
        """
        Initializes the downloader
        """
        current_dir = Path(__file__).resolve().parent
        while current_dir.name != "src" and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        self._base_dir = current_dir

        self._env_data = load_env_file()
        self._cli_output_format = read_json_file(CONFIG_FILE)["spotify_downloader"]["output_format"]

        self._authenticate()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._sp = None
        return False

    def _authenticate(self) -> None:
        """
        Initializes the spotipy client
        """
        auth_manager = SpotifyClientCredentials(client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                                                client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"])

        self._sp = spotipy.Spotify(auth_manager=auth_manager)

    def spotify_search_song_metadata_by_id(self, query: str) -> dict:
        """
        Searches for a song on Spotify and returns the metadata
        :param query: ID of spotify track
        :type query: str
        :return: metadata of the song
        :rtype: dict[str, Any]
        """
        return self._sp.track(query)

    @staticmethod
    def milliseconds_to_minutes_and_seconds(milliseconds: int) -> str:
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def get_title_artist(dict_metadata: dict) -> dict[str, str]:
        """
        Returns the title and artist given a metadata, only returns the featured artist
        :param dict_metadata: A dict from a song metadata, from search_song_metadata
        :type dict_metadata: dict[str, Any]
        :return: a dict in the form of "TITLE - ARTIST"
        :rtype: str
        """
        return {"title": dict_metadata["name"],
                "artist": dict_metadata["artists"][0]["name"]}

    def download_song(self, limit: int = 10) -> Generator[Any, dict[str, Any], None]:
        persistent_choices = [{"type": "__nav__", "display": "Next", "value": "__next__"},
                              {"type": "__nav__", "display": "Previous", "value": "__prev__"},
                              {"type": "__nav__", "display": "New Query", "value": "__new__"}]

        offset: int = 0

        query = yield UIPromptRequest(
            type="input",
            message="",
            placeholder="Query to search"
        )
        query = query["value"]

        while True:
            song_list = self._sp.search(q=query, offset=offset, limit=limit)["tracks"]["items"]

            formatted_choices = []

            for idx, song in enumerate(song_list):
                formatted_choices.append({
                    "type": "__option__",
                    "title": self.get_title_artist(song)["title"],
                    "artist": self.get_title_artist(song)["artist"],
                    "duration": self.milliseconds_to_minutes_and_seconds(song["duration_ms"]),
                    "album": song["album"]["name"],
                    "relevance": song["popularity"],
                    "value": idx,
                    "metadata": song
                })
            for per_choice in persistent_choices: formatted_choices.append(per_choice)

            user_choice: dict[str, Any] = yield UIPromptRequest(
                type="select",
                message="",
                choices=formatted_choices)

            match user_choice["value"]:
                case "__next__":
                    offset += limit
                case "__prev__":
                    if offset == 0:
                        continue
                    offset -= limit
                case "__new__":
                    query = yield UIPromptRequest(
                        type="input",
                        message="",
                        placeholder="Query to search"
                    )
                    query = query["value"]
                case _:
                    ...


if __name__ == "__main__":
    dl = Downloader()
    # 1. Initialize the generator pipeline
    pipeline = dl.download_song(limit=3)

    # 2. Start the pipeline and catch the first yield (The initial Query Input)
    prompt = next(pipeline)

    while True:
        if prompt.type == "input":
            user_input = input("Search for a song: ")
            # Send the dictionary back matching the shape your code expects: query["value"]
            prompt = pipeline.send({"value": user_input})

        elif prompt.type == "select":
            print(f"\n--- Select an Option ---")
            for i, choice in enumerate(prompt.choices):
                if choice["type"] == "__nav__":
                    print(f" [{i}] Navigation -> {choice['display']}")
                else:
                    print(f" [{i}] {choice['title']} - {choice['artist']}")

            idx = int(input("\nChoose a number: "))
            selected_choice = prompt.choices[idx]

            try:
                # Send the selected choice dictionary back to the generator
                prompt = pipeline.send(selected_choice)
            except StopIteration:
                # The generator returns (exits) once a non-navigation song is chosen
                print("\n🎉 Song selection complete! Generator exited cleanly.")
                break