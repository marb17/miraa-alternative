# STANDARD LIBRARY
from pathlib import Path
from typing import Any, Generator

# HELPER LIBRARIES
from lyricsgenius.types import Song
from lyricsgenius import Genius

# PYPI PACKAGE
from questionary import Choice

from engine.utils.classes.dataclasses import UIPromptRequest
from engine.utils.functions.filesystem import load_env_file
from engine.utils.functions.other import fuzzy_partial_match
from engine.utils.logger import Logger
logger = Logger(__name__)

class GeniusExtractor:
    def __init__(self) -> None:
        access_token = load_env_file()["GENIUS_ACCESS_TOKEN"]
        self._genius = Genius(access_token)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._genius = None
        return False

    def _search_song(self, title: str, artist: str) -> Song | None:
        """
        Searches for a song on genius using title and artist
        :param title: Title of song to be searched
        :type title: str
        :param artist: Artist of song to be searched
        :type artist: str
        :return: Song object or None
        :rtype: Song | None
        """
        return self._genius.search_song(title=title, artist=artist, get_full_info=True)

    def return_metadata(self, title: str = '', artist: str = '', json_data: dict = None) -> Generator[UIPromptRequest, Any, dict[str, Any]]:
        """
        Returns the metadata of a song from genius, either choose Song or title and artist
        :param title: Title of the song
        :type title: str
        :param artist: Artist of the song
        :type artist: str
        :param json_data: Path to json file containing the song data
        :type json_data: dict | None
        :return: Data of the song
        :rtype: dict[str, Any]
        """
        def is_song_romanized(dict_data: dict) -> bool:
            if fuzzy_partial_match(dict_data["primary_artist"]["name"], "romanization"):
                return True

            if fuzzy_partial_match(dict_data["title"], "romanized"):
                return True

            if dict_data.get("language") == "romanization":
                return True

            return False

        try:
            try_force_jp = False
            tries = 0
            while True:
                if try_force_jp:
                    data = self._search_song(title=title + " jp", artist=artist)
                else:
                    data = self._search_song(title=title, artist=artist)

                if data is None:
                    raise ValueError

                if is_song_romanized(data.to_dict()):
                    try_force_jp = True
                    tries += 1
                    continue

                if tries >= 2:
                    raise ValueError

                break
        except ValueError:
            while True:
                all_data = self._genius.search_songs(title, per_page=5, page=1)

                response = yield UIPromptRequest(
                    type="select",
                    choices=all_data['hits'],
                    message="Genius wasn't able to find a single match, please choose the right song:",
                    extra_info={"song_reference": f"{json_data["pre_processing"]["view_name"]}" if json_data else ""}
                )

                data = self._genius.search_song(song_id=all_data["hits"][response]["result"]["id"])

                if is_song_romanized(data.to_dict()):
                    continue

                break

        return data.to_dict()
