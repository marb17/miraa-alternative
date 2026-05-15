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

    # TODO search songs in spotify by qureying their data base

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
        return '' # so my static code checker doesnt get angry at me

    def search_song(self, limit: int = 5) -> dict:
        import questionary as q

        user_title = q.text("Enter song of title: ").ask()
        user_artist = q.text("Enter song of artist (optional): ").ask()

        query = f"track:{user_title}"
        if user_artist != '':
            query += f" artist:{user_artist}"

        offset = 0

        while True:
            song_list = self._sp.search(q=query, limit=limit, offset=offset)

            song_list_ask = [f"{song["name"]} | {song["artists"][0]["name"]}" for song in song_list['tracks']['items']]
            song_list_ask.append("Next ->")
            song_list_ask.append("Previous <-")

            user_song_choice = q.select("Please choose the song:", choices=song_list_ask).ask()

            if user_song_choice == 'Next ->':
                offset += 5
            elif user_song_choice == 'Previous <-':
                if offset < 5:
                    pass
                else:
                    offset -= 5
            else:
                break

        print(user_song_choice)