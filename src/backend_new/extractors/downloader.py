# STANDARD LIBRARY
from pathlib import Path
from time import sleep, time
import json
from typing import Any
from concurrent.futures import ThreadPoolExecutor

# HELPER LIBRARIES
from backend_new.utils.helper_funcs import questionary_select, load_env_file, read_json_file, write_json_file

# PYPI LIBRARIES
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import questionary as q

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

# CONSTANTS
from backend_new.utils.constants import TEMP_DIR, CONFIG_FILE


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

    # region helper functions

    @staticmethod
    def extract_title_artist_from_youtube_metadata(dict_metadata: dict) -> str:
        return f"{dict_metadata["name"]} - {dict_metadata["artists"][0]["name"]}"

    # endregion

    # region SPOTIFY
    def _search_song_metadata(self, query: str = '') -> dict:
        """
        Searches for a song on Spotify and returns the metadata
        :param query: Query to be searched for
        :type query: str
        :return: metadata of the song
        :rtype: dict[str, Any]
        """
        if query == '':
            raise Exception('Spotify query is required')

        track_url = query
        return self._sp.track(track_url)

    def _get_title_artist(self, query: str | None = None, metadata: dict | None = None) -> str:
        """
        Returns the title and artist given a query or metadata, only returns the featured artist
        :param query: A query of a spotify song, a URL
        :type query: str | None
        :param metadata: A dict from a song metadata, from search_song_metadata
        :type metadata: dict[str, Any]
        :return: a str in the form of "TITLE - ARTIST"
        :rtype: str
        """
        if query is not None and metadata is not None:
            raise Exception('Spotify query and metadata are mutually exclusive')
        if query is None and metadata is None:
            raise Exception('Spotify query or metadata is required')

        if query is not None:
            track_data = self._search_song_metadata(query)
            return self.extract_title_artist_from_youtube_metadata(track_data)
        elif metadata is not None:
            return self.extract_title_artist_from_youtube_metadata(metadata)
        return '' # so my static code checker doesn't get angry at me

    def _cli_search_song(self, limit: int = 10, query: str = '') -> dict[str, Any]: # TODO make limit in config file
        """
        Searches a song using spotify querying
        :param query: A query to search for, defaults to none using CLI interface
        :type query: str
        :param limit: How many songs to show at a time
        :type limit: int
        :return: A dict of the song metadata (spotify)
        :rtype: dict[str, Any]
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
                name = str(self.extract_title_artist_from_youtube_metadata(song_data))
                if duration:
                    name += f" | {milliseconds_to_minutes_and_seconds(song_data['duration_ms'])}"
                if album:
                    name += f" | {song_data['album']['name']} : {song_data['album']['release_date'][:4]}"
                if popularity:
                    name += f" | Relevance: {song_data['popularity']}%"
                return name
            else:
                return str(self.extract_title_artist_from_youtube_metadata(song_data))

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
                query = ''
                _ask_for_query()
            else:
                break

        return user_song_choice

    def query_song_spotify(self) -> None:
        """
        query a song from spotify and save it to a JSON file with all data needed
        """
        data = self._cli_search_song()
        view_name = self._get_title_artist(metadata=data)
        youtube_id = self.youtube_query(query=view_name)
        json_data = json.dumps(
            {"pre_processing": {"youtube_id": youtube_id, "view_name": view_name, "raw_metadata": data}}, indent=4)
        file_path = TEMP_DIR / f"{view_name}.json"

        file_path.write_text(json_data)
        logger.info(f"Saved song data: {view_name} -> {file_path}")

    # endregion

    # region YOUTUBE
    def youtube_query(self, query: str = '', limit: int = 10, choose_top_result: bool = False) -> str:
        """
        Searches for a song on YouTube and returns the id of the song
        :param query: Query to search for
        :type query: str
        :param limit: How many to search for
        :type limit: int
        :param choose_top_result: Will always return the first result without asking the user
        :type choose_top_result: bool
        :return: YouTube video id
        :rtype: str
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

    def download_youtube_video(self, url: str = '', sleep_time_if_fail: float = 5, retry_count: int = 5) -> tuple[Any, Any]:
        """
        Downloads a YouTube video to .temp
        :param retry_count: How many times to retry downloading the video
        :type retry_count: int
        :param sleep_time_if_fail: How long to wait before retrying to download the video if a fail occurs
        :type sleep_time_if_fail: float
        :param url: A url to the video ID
        :type url: str
        :return: A tuple consisting of the Video ID and all the metadata
        :rtype: tuple[Path, dict[str, Any]]
        """
        now = time()

        if url == '':
            raise Exception('YouTube URL is required')

        ydl_opts = {'format': 'm4a/bestaudio/best',
                    'paths': {'home': f'{str(TEMP_DIR)}'},
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
                    # ydl.download([url])
                    video_data = ydl.extract_info(url, download=True)
                    break
            except (DownloadError, ExtractorError):
                sleep(sleep_time_if_fail)
        logger.debug(f"Finished downloading video in {(time() - now):.2f} seconds")

        video_id = video_data.get("id")
        if not video_id:
            raise Exception(f"Could not extract video ID from {url}")
        expected_file = TEMP_DIR / f"{video_id}.wav"

        return expected_file, video_data

    def select_song_to_download(self, json_file: Path | None) -> None:
        """
        Downloads a song from YouTube using metadata present in .temp
        When no files are present, it will query spotify
        :param json_file: A path to a JSON file containing metadata
        :type json_file: Path | None
        :return: None
        :rtype: None
        """
        def get_youtube_id_from_json(file_path: Path) -> str | None:
            if file_path.suffix == ".json":
                return str(read_json_file(file_path)["pre_processing"]["youtube_id"])
            return None

        def _download(file_path: Path | str | None) -> None:
            if file_path is None:
                raise Exception("No file path provided")
            if type(file_path) is str:
                self.download_youtube_video(url=file_path)
            if type(file_path) is Path:
                self.download_youtube_video(url=get_youtube_id_from_json(file_path))

        break_off = False

        if json_file is None:
            while True:
                if break_off:
                    break

                all_files = list(TEMP_DIR.iterdir())
                all_files_stem = [file.stem for file in all_files]
                available_json_files = [file for file in all_files if
                                        file.suffix == ".json" and get_youtube_id_from_json(
                                            file) not in all_files_stem]

                # if songs are available, ask user which one to download or download the only one present
                if available_json_files:
                    # if only one song is available, download it
                    if len(available_json_files) == 1:
                        target_id = get_youtube_id_from_json(available_json_files[0])
                        _download(target_id)
                    # if multiple songs are available, ask user which one to download
                    elif len(available_json_files) > 1:
                        while True:
                            all_files = list(TEMP_DIR.iterdir())
                            all_files_stem = [file.stem for file in all_files]
                            available_json_files = [file for file in all_files
                                                    if file.suffix == ".json" and
                                                    get_youtube_id_from_json(file) not in all_files_stem]

                            file_list = [{"name": file.stem, "value": file} for file in available_json_files]

                            user_choice = questionary_select("Please choose the song:",
                                                             choose_data=file_list,
                                                             enable_pages=True,
                                                             enable_all="Download All",
                                                             enable_exit="Exit",
                                                             batch_data=True)

                            if user_choice == "__all__":
                                target_ids = [get_youtube_id_from_json(file) for file in available_json_files]

                                with ThreadPoolExecutor(max_workers=5) as executor:
                                    _ = executor.map(_download, target_ids)

                                for file in available_json_files:
                                    write_json_file(file, True, ["pre_processing", "downloaded"])
                                break_off = True
                                break
                            else:
                                file_data = read_json_file(user_choice)
                                _download(file_data["pre_processing"]["youtube_id"])

                # if no songs are available, query spotify
                else:
                    with Downloader() as down:
                        down.query_song_spotify()
        else:
            target_id = get_youtube_id_from_json(json_file)
            _download(target_id)
    # endregion