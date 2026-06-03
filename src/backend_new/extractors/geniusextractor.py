# STANDARD LIBRARY
from typing import Any

# HELPER LIBRARIES
from lyricsgenius.types import Song
from lyricsgenius import Genius

from backend_new.utils.helper_funcs import questionary_select

# PYPI PACKAGE
from questionary import Choice

from backend_new.utils.logger import Logger
logger = Logger(__name__)

class GeniusExtractor:
    def __init__(self, access_token: str | None = '') -> None:
        if access_token == '' or access_token is None:
            raise Exception('Access token is required')

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

    def return_metadata(self, song: Song | None = None, title: str = '', artist: str = '') -> dict[str, Any] | None:
        """
        Returns the metadata of a song from genius, either choose Song or title and artist
        :param song: A song object to extract
        :type song: Song | None
        :param title: Title of the song
        :type title: str
        :param artist: Artist of the song
        :type artist: str
        :return: Data of the song
        :rtype: dict[str, Any]
        """
        if song is not None and (title != '' or artist != ''):
            raise Exception('Song and title/artist are mutually exclusive')
        if song is None and (title == '' or artist == ''):
            raise Exception('Song or title/artist is required')
        if song is None and (title == '' or artist == ''):
            raise Exception('Title/artist is required')

        # TODO pls fix this shitty match case system so ass smh
        if song is not None:
            data = song
        elif title != '' and artist != '':
            counter = 0
            data = None
            while True:
                match counter:
                    case 0: data = self._search_song(title=title, artist=artist)
                    case 1:
                        page = 1

                        while True:
                            try:
                                all_data = self._genius.search_songs(title, per_page=5, page=page)
                            except Exception:
                                page = page - 1 if page > 1 else 1
                                continue

                            choose_data = [Choice(f"{song['result']['title']} | {song['result']['primary_artist']['name']} | {song.get("result", {}).get("release_date_components", {}).get('year', 'Unknown') if song.get("result", {}).get("release_date_components", {}) is not None else "Unknown"}",
                                                   value=song['result']['id']) for song in all_data['hits']]
                            user_choice = questionary_select("Please choose the song: (automatic search failed)", choose_data=choose_data, enable_pages=True)

                            if user_choice == "__next__":
                                page += 1
                            elif user_choice == "__prev__":
                                if page == 1:
                                    pass
                                else:
                                    page -= 1
                            else:
                                return self._genius.search_song(song_id=user_choice).to_dict()
                    case 2: break

                if data is None:
                    counter += 1
                    continue

                break
        else:
            return None

        if data is None:
            return None

        return data.to_dict()