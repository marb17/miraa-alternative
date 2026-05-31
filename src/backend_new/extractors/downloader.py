# STANDARD LIBRARY
from pathlib import Path
from time import sleep, time
import json

# HELPER LIBRARIES
from backend_new.utils.helper_funcs import questionary_select, load_env_file, read_json_file

# PYPI LIBRARIES
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import questionary as q

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

# CONSTANTS
from backend_new.utils.constants import TEMP_DIR, CONFIG_FILE


from backend_new.utils.logger import Logger
logger = Logger()

class Downloader:
    def __init__(self) -> None:
        """
        Initializes the downloader
        :param spotify_client_id:
        :param spotify_client_secret:
        :param youtube_cookie_path: Path to the YouTube cookie file, not recommended to use. Cookies require extra authentication and are not guaranteed to work
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
        query = ''

        def _ask_for_query() -> None:
            nonlocal query

            if query != '':
                query = query
            else:
                if questionary_select("Please choose query type", choose_data=["Plain query", "Search by track and artist"]) == "Search by track and artist":

                    user_query = q.form(
                        user_title=q.text("Enter title of song: ").ask(),
                        user_artist = q.text("Enter artist of song (optional): ").ask()
                    ).ask()

                    query = f"track:{user_query['user_title']}"
                    if user_query['user_artist'] != '':
                        query += f" artist:{user_query['user_artist']}"
                else:
                    query = q.text("Enter the query to search: ").ask()

        _ask_for_query()

        def milliseconds_to_minutes_and_seconds(milliseconds: int) -> str:
            seconds = milliseconds // 1000
            minutes, seconds = divmod(seconds, 60)
            return f"{minutes:02d}:{seconds:02d}"

        def format_name(song_data: dict, duration: bool = True, album: bool = True, popularity: bool = True) -> str:
            if self._cli_output_format is not None:
                name = str(self._extract_title_artist(song_data))
                if duration:
                    name += f" | {milliseconds_to_minutes_and_seconds(song_data['duration_ms'])}"
                if album:
                    name += f" | {song_data['album']['name']} : {song_data['album']['release_date'][:4]}"
                if popularity:
                    name += f" | Relevance: {song_data['popularity']}%"
                return name
            else:
                return str(self._extract_title_artist(song_data))

        offset = 0
        while True:
            song_list = self._sp.search(q=query, limit=limit, offset=offset)
            if self._cli_output_format is not None:
                song_list_ask = [{"name": format_name(song, duration=self._cli_output_format.get('duration', False),
                                                       album=self._cli_output_format.get('album', False),
                                                       popularity=self._cli_output_format.get('popularity', False)),
                                   "value": song}
                                  for song in song_list['tracks']['items']]
            else:
                song_list_ask = [{"name": format_name(song), "value": song}
                                  for song in song_list['tracks']['items']]

            user_song_choice = questionary_select("Please choose the song: (prefer JP titles)",
                                                   choose_data=song_list_ask,
                                                   enable_pages=True,
                                                   extra_navigation_options=[q.Choice("Retry", value='__retry__', shortcut_key='r')])

            if user_song_choice == '__next__':
                offset += 5
            elif user_song_choice == '__prev__':
                if offset < 5:
                    pass
                else:
                    offset -= 5
            elif user_song_choice == '__retry__':
                _ask_for_query()
            else:
                break

        return user_song_choice

    def youtube_query(self, query: str = '', limit: int = 10, choose_top_result: bool = False) -> str:
        """
        Searches for a song on YouTube and returns the id of the song
        :param query: Query to search for
        :param limit: How many to search for
        :param choose_top_result: Will always return the first result without asking the user
        :return: YouTube video id
        """

        limit = 1 if choose_top_result else limit
        search_query = f"ytsearch{limit}:{query}"

        ydl_opts = {'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True}
        if self._env_data.get("YOUTUBE_COOKIE_PATH", "") != "":
            ydl_opts["cookiefile"] = self._env_data["YOUTUBE_COOKIE_PATH"]
            ydl_opts['remote_components'] = ['ejs:github']
            ydl_opts['compat_opts'] = ['no-external-interpreter']

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            info = ydl.sanitize_info(info)
            if info is None:
                raise Exception("No results found")
            results = info.get("entries", [])

            formatted_results = []
            for track in results:
                formatted_results.append({
                    "id": track.get("id"),
                    "title": track.get("title"),
                    "channel": track.get("uploader"),
                    "duration": track.get("duration"),
                    "view_count": track.get("view_count")
                })

        def format_to_minutes_and_seconds(seconds: int) -> str:
            minutes, seconds = divmod(int(seconds), 60)
            return f"{minutes:02d}:{seconds:02d}"

        if choose_top_result:
            return formatted_results[0]["id"]
        else:
            choices = [{"name": f"{song['title']} | {song['channel']} | {format_to_minutes_and_seconds(song['duration'])} | {song['view_count']} | {song['id']}", "value": index} for index, song in enumerate(formatted_results)]
            user_song_choice = questionary_select(f"Please choose the song: (prefer JP titles)", choose_data=choices)
            return formatted_results[int(user_song_choice)]["id"]

    def download_youtube_video(self, url: str = '', sleep_time_if_fail: float = 5, retry_count: int = 5) -> None:
        """
        Downloads a YouTube video to .temp
        :param retry_count: How many times to retry downloading the video
        :param sleep_time_if_fail: How long to wait before retrying to download the video if a fail occurs
        :param url: A url to the video ID
        """
        now = time()

        if url == '':
            raise Exception('YouTube URL is required')

        ydl_opts = {'format': 'm4a/bestaudio/best',
                    'paths': {'home': f'{str(self._base_dir / ".temp")}'},
                    'outtmpl': '%(id)s.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'wav',
                    }]}
        # TODO add option for macOS since idk if ffmpeg works for macOS

        if self._env_data.get("YOUTUBE_COOKIE_PATH", "") != "":
            ydl_opts["cookiefile"] = self._env_data["YOUTUBE_COOKIE_PATH"]
            ydl_opts['remote_components'] = ['ejs:github']
            ydl_opts['compat_opts'] = ['no-external-interpreter']

        counter = 0
        while True:
            if counter >= retry_count:
                raise Exception("Failed to download video")
            counter += 1

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    break
            except (DownloadError, ExtractorError):
                sleep(sleep_time_if_fail)
        logger.debug(f"Finished downloading video in {(time() - now):.2f} seconds")
        
    def query_song_spotify(self) -> None:
        """
        query a song from spotify and save it to a JSON file with all data needed
        """
        data = self.cli_search_song()
        view_name = self.get_title_artist(metadata=data)
        youtube_id = self.youtube_query(query=view_name)
        json_data = json.dumps(
            {"pre_processing": {"youtube_id": youtube_id, "view_name": view_name, "raw_metadata": data}}, indent=4)
        file_path = TEMP_DIR / f"{view_name}.json"

        file_path.write_text(json_data)
        logger.info(f"Saved song data: {view_name} -> {file_path}")
