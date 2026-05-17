from lyricsgenius.types import Song

class Lyrics:
    def __init__(self, access_token: str | None = '') -> None:
        if access_token == '' or access_token is None:
            raise Exception('Access token is required')

        from lyricsgenius import Genius

        self._genius = Genius(access_token)

    def _search_song(self, title: str, artist: str) -> Song | None:
        return self._genius.search_song(title=title, artist=artist, get_full_info=True)

    def return_metadata(self, song: Song | None = None, title: str = '', artist: str = '') -> dict | None:
        if song is not None and (title != '' or artist != ''):
            raise Exception('Song and title/artist are mutually exclusive')
        if song is None and (title == '' or artist == ''):
            raise Exception('Song or title/artist is required')
        if song is None and (title == '' or artist == ''):
            raise Exception('Title/artist is required')

        if song is not None:
            _data = song
        elif title != '' and artist != '':
            _data = self._search_song(title=title, artist=artist)
        else:
            return None

        if _data is None:
            return None

        return _data.to_dict()