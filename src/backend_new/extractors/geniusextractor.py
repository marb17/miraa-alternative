from lyricsgenius.types import Song

class GeniusExtractor:
    def __init__(self, access_token: str | None = '') -> None:
        if access_token == '' or access_token is None:
            raise Exception('Access token is required')

        from lyricsgenius import Genius

        self._genius = Genius(access_token)

    def _search_song(self, title: str, artist: str) -> Song | None:
        """
        Searches for a song on genius using title and artist
        :param title:
        :param artist:
        :return:
        """
        return self._genius.search_song(title=title, artist=artist, get_full_info=True)

    def return_metadata(self, song: Song | None = None, title: str = '', artist: str = '') -> dict | None:
        """
        Returns the metadata of a song from genius, either choose Song or title and artist
        :param song: A song object to extract
        :param title: Title of the song
        :param artist: Artist of the song
        :return:
        """
        from backend_new.utils.helper_funcs import questionary_select
        from questionary import Choice

        if song is not None and (title != '' or artist != ''):
            raise Exception('Song and title/artist are mutually exclusive')
        if song is None and (title == '' or artist == ''):
            raise Exception('Song or title/artist is required')
        if song is None and (title == '' or artist == ''):
            raise Exception('Title/artist is required')

        if song is not None:
            _data = song
        elif title != '' and artist != '':
            _counter = 0
            _data = None
            while True:
                match _counter:
                    case 0: _data = self._search_song(title=title, artist=artist)
                    case 1:
                        _page = 1

                        while True:
                            try:
                                _all_data = self._genius.search_songs(title, per_page=5, page=_page)
                            except Exception:
                                _page = _page - 1 if _page > 1 else 1
                                continue

                            _choose_data = [Choice(f"{song['result']['title']} | {song['result']['primary_artist']['name']} | {song.get("result", {}).get("release_date_components", {}).get('year', 'Unknown') if song.get("result", {}).get("release_date_components", {}) is not None else "Unknown"}",
                                                   value=song['result']['id']) for song in _all_data['hits']]
                            _user_choice = questionary_select("Please choose the song: (automatic search failed)", choose_data=_choose_data, enable_pages=True)

                            if _user_choice == "__next__":
                                _page += 1
                            elif _user_choice == "__prev__":
                                if _page == 1:
                                    pass
                                else:
                                    _page -= 1
                            else:
                                return self._genius.search_song(song_id=_user_choice).to_dict()
                    case 2: break

                if _data is None:
                    _counter += 1
                    continue

                break
        else:
            return None

        if _data is None:
            return None

        return _data.to_dict()