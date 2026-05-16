class Downloader:
    def __init__(self, spotify_client_id: str = '', spotify_client_secret: str = '', youtube_cookie_path: str = '') -> None:
        if spotify_client_id == '' or spotify_client_secret == '':
            raise Exception('Spotify client id and secret are required')

        self._spotify_client_id = spotify_client_id
        self._spotify_client_secret = spotify_client_secret
        self._youtube_cookie_path = youtube_cookie_path

        self._authenticate()

    def _authenticate(self) -> None:
        """
        Initializes the spotipy client
        """
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        auth_manager = SpotifyClientCredentials(client_id=self._spotify_client_id,
                                                client_secret=self._spotify_client_secret)

        self._sp = spotipy.Spotify(auth_manager=auth_manager)

    # region helper functions

    @staticmethod
    def _extract_title_artist(dict_metadata: dict) -> str:
        return f"{dict_metadata["name"]} - {dict_metadata["artists"][0]["name"]}"

    # endregion

    def search_song_metadata(self, query: str = '') -> dict:
        """
        Searches for a song on Spotify and returns the metadata
        :param query: Query to be searched for
        :return: metadata of the song
        """
        if query == '':
            raise Exception('Spotify query is required')

        track_url = query
        return self._sp.track(track_url)

    def get_title_artist(self, query: str | None = None, metadata: dict | None = None) -> str:
        """
        Returns the title and artist given a query or metadata, only returns the featured artist
        :param query: A query of a spotify song, a URL
        :param metadata: A dict from a song metadata, from search_song_metadata
        :return: a str in the form of "TITLE - ARTIST"
        """
        if query is not None and metadata is not None:
            raise Exception('Spotify query and metadata are mutually exclusive')
        if query is None and metadata is None:
            raise Exception('Spotify query or metadata is required')

        if query is not None:
            track_data = self.search_song_metadata(query)
            return self._extract_title_artist(track_data)
        elif metadata is not None:
            return self._extract_title_artist(metadata)
        return '' # so my static code checker doesn't get angry at me

    def cli_search_song(self, limit: int = 10, query: str = '') -> dict: # TODO make limit in config file
        """
        Searches a song using spotify querying
        :param query: A query to search for, defaults to none using CLI interface
        :param limit: How many songs to show at a time
        :return: A dict of the song metadata (spotify)
        """
        import questionary as q

        if query != '':
            _query = query
        else:
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

            _song_list_ask = [{"name": f"{self._extract_title_artist(song)}",
                               "value": song}
                              for song in _song_list['tracks']['items']]
            _song_list_ask.append(q.Separator())
            _song_list_ask.append({"name": "Next ->", "value:": "__next__"})
            _song_list_ask.append({"name": "Previous ->", "value:": "__prev__"})

            _user_song_choice = q.select("Please choose the song:", choices=_song_list_ask).ask()

            if _user_song_choice == '__next__':
                _offset += 5
            elif _user_song_choice == '__prev__':
                if _offset < 5:
                    pass
                else:
                    _offset -= 5
            else:
                break

        return _user_song_choice

    def youtube_query(self, query: str = '', limit: int = 3, choose_top_result: bool = False) -> str:
        """
        Searches for a song on YouTube and returns the id of the song
        :param query: Query to search for
        :param limit: How many to search for
        :param choose_top_result: Will always return the first result without asking the user
        :return: YouTube video id
        """
        import yt_dlp

        _limit = 1 if choose_top_result else limit
        search_query = f"ytsearch{_limit}:{query}"

        ydl_opts = {'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True}
        if self._youtube_cookie_path != '':
            ydl_opts["cookiefile"] = self._youtube_cookie_path
            ydl_opts['remote_components'] = ['ejs:github']
            ydl_opts['compat_opts'] = ['no-external-interpreter']

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            _info = ydl.extract_info(search_query, download=False)
            _info = ydl.sanitize_info(_info)
            if _info is None:
                raise Exception("No results found")
            _results = _info.get("entries", [])

            _formatted_results = []
            for track in _results:
                _formatted_results.append({
                    "id": track.get("id"),
                    "title": track.get("title"),
                    "channel": track.get("uploader")
                })

        if choose_top_result:
            return _formatted_results[0]["id"]
        else:
            import questionary as q
            _choices = [{"name": f"{song['title']} | {song['channel']} | {song['id']}", "value": index} for index, song in enumerate(_formatted_results)]
            _user_song_choice = q.select("Please choose the song:", choices=_choices).ask()
            return _formatted_results[int(_user_song_choice)]["id"]

    def download_youtube_video(self, url: str = '', sleep_time_if_fail: float = 5, retry_count: int = 5) -> None:
        """
        Downloads a YouTube video to .temp
        :param retry_count: How many times to retry downloading the video
        :param sleep_time_if_fail: How long to wait before retrying to download the video if a fail occurs
        :param url: A url to the video ID
        """
        import yt_dlp
        from yt_dlp.utils import DownloadError, ExtractorError
        from time import sleep

        if url == '':
            raise Exception('YouTube URL is required')

        ydl_opts = {'format': 'm4a/bestaudio/best',
                    'paths': {'home': '../.temp'},
                    'outtmpl': '%(id)s.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'wav',
                    }]}
        if self._youtube_cookie_path != '':
            ydl_opts["cookiefile"] = self._youtube_cookie_path
            ydl_opts['remote_components'] = ['ejs:github']
            ydl_opts['compat_opts'] = ['no-external-interpreter']

        _counter = 0
        while True:
            if _counter >= retry_count:
                raise Exception("Failed to download video")
            _counter += 1

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    break
            except (DownloadError, ExtractorError) as e:
                sleep(sleep_time_if_fail)