class Downloader:
    def __init__(self, spotify_client_id: str = '', spotify_client_secret: str = '') -> None:
        if spotify_client_id == '' or spotify_client_secret == '':
            raise Exception('Spotify client id and secret are required')

        self._spotify_client_id = spotify_client_id
        self._spotify_client_secret = spotify_client_secret

        self._authenticate()

    def _authenticate(self) -> None:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        auth_manager = SpotifyClientCredentials(client_id=self._spotify_client_id,
                                                client_secret=self._spotify_client_secret)

        self._sp = spotipy.Spotify(auth_manager=auth_manager)

    def search_song_metadata(self, query: str = '') -> dict:
        if query == '':
            raise Exception('Spotify query is required')

        track_url = query
        return self._sp.track(track_url)

    def get_title_artist(self, query: str | None = None, metadata: dict | None = None) -> str:
        """
        Returns the title and artist given a query or metadata, only returns the featured artist
        :param query: A query of a spotify song, a URL
        :param metadata: A dict from a songs metadata, from search_song_metadata
        :return: a str in the form of "TITLE - ARTIST"
        """
        if query is not None and metadata is not None:
            raise Exception('Spotify query and metadata are mutually exclusive')
        if query is None and metadata is None:
            raise Exception('Spotify query or metadata is required')

        extract_title_artist = lambda dict_metadata: f"{dict_metadata["name"]} - {dict_metadata["artists"][0]["name"]}"

        if query is not None:
            track_data = self.search_song_metadata(query)
            return extract_title_artist(track_data)
        elif metadata is not None:
            return extract_title_artist(metadata)
        return '' # so my static code checker doesn't get angry at me

    def cli_search_song(self, limit: int = 10) -> dict:
        import questionary as q

        if q.select("Please choose query type", choices=["Plain query", "Search by track and artist"]).ask() == "Search by track and artist":
            _user_title = q.text("Enter title of song: ").ask()
            _user_artist = q.text("Enter artist of song (optional): ").ask()

            _query = f"track:{_user_title}"
            if _user_artist != '':
                _query += f" artist:{_user_artist}"
        else:
            _query = q.text("Enter the query to search: ").ask()

        _offset = 0

        while True:
            _song_list = self._sp.search(q=_query, limit=limit, offset=_offset)

            _song_list_ask = [f"{song["name"]} | {song["artists"][0]["name"]}" for song in _song_list['tracks']['items']]
            _song_list_ask.append("Next ->")
            _song_list_ask.append("Previous <-")

            _user_song_choice = q.select("Please choose the song:", choices=_song_list_ask).ask()

            if _user_song_choice == 'Next ->':
                _offset += 5
            elif _user_song_choice == 'Previous <-':
                if _offset < 5:
                    pass
                else:
                    _offset -= 5
            else:
                break

        return _user_song_choice

    def download_song_youtube(self, query: str = ''):
        import yt_dlp
        # TODO finish downlad song

    # TODO add lyric puller
