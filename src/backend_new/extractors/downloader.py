# STANDARD LIBRARY
import functools
import queue
import threading
import types
from pathlib import Path
from time import sleep, time
import json
from typing import Any
from collections.abc import Generator

import requests.exceptions
from spotipy import cache_handler, CacheFileHandler

# HELPER LIBRARIES
from backend_new.utils.functions.filesystem import read_json_file, load_env_file, read_config

# PYPI LIBRARIES
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

import questionary as q

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

# CONSTANTS
from backend_new.utils.constants import TEMP_DIR, CONFIG_FILE, UIPromptRequest, CACHE_DIR

from backend_new.utils.logger import Logger
logger = Logger(__name__)

def handle_spotify_token_errors(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)

            if isinstance(result, types.GeneratorType):
                try:
                    yield from result
                except spotipy.SpotifyException as e:
                    if e.http_status == 401:
                        resolved = yield UIPromptRequest(
                            type="hidden_request",
                            message=401
                        )

                        if resolved:
                            return self._sp_token.current_user_playing_track()
                    else:
                        raise e
            else:
                return result
        except spotipy.SpotifyException as e:
            if e.http_status == 401:
                resolved = yield UIPromptRequest(
                    type="hidden_request",
                    message=401
                )

                if resolved:
                    return self._sp_token.current_user_playing_track()
            else:
                raise e

    return wrapper



class Downloader:
    def __init__(self) -> None:
        """
        Initializes the downloader
        """
        self._env_data = load_env_file()
        self._use_token = read_config()['spotify_downloader']["token"]
        self._sp = None
        self._sp_token = None

        self._cache_handler = CacheFileHandler(
            cache_path=CACHE_DIR / ".spotify_cache",
            username="spotipy"
        )


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._sp = None
        self._sp_token = None
        return False

    #TODO fix dup lines
    def authenticate(self, force_cache: bool = False) -> Generator[UIPromptRequest, None, bool]:
        """
        Initializes the spotipy client
        """
        if self._sp and self._sp_token:
            return

        auth_manager_no_token = SpotifyClientCredentials(client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                                                client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"])

        if self._use_token:
            scope = "user-read-currently-playing user-read-playback-state"

            auth_manager = SpotifyOAuth(
                client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=self._env_data["SPOTIFY_REDIRECT_URI"],
                scope=scope,
                open_browser=True,
                cache_handler=self._cache_handler
            )

            cached_token = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())

            if cached_token or force_cache:
                access_token = cached_token["access_token"]
            else:
                url = ""
                while not url:
                    url = yield UIPromptRequest(
                        type="input",
                        extra_info={"url": auth_manager.get_authorize_url()},
                        message="",
                    )

                try:
                    code = auth_manager.parse_response_code(url)
                    token_info = auth_manager.get_access_token(code, as_dict=True)
                    access_token = token_info["access_token"]
                except Exception as e:
                    raise RuntimeError(f"Authentication Handshake Failed: {e}")

            self._sp_token = spotipy.Spotify(auth=access_token)

        self._sp = spotipy.Spotify(auth_manager=auth_manager_no_token)
        return True

    def cache_authenticate(self) -> None:
        if self._sp and self._sp_token:
            return

        auth_manager_no_token = SpotifyClientCredentials(client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                                                         client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"])

        if self._use_token:

            scope = "user-read-currently-playing user-read-playback-state"

            auth_manager = SpotifyOAuth(
                client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=self._env_data["SPOTIFY_REDIRECT_URI"],
                scope=scope,
                open_browser=True,
                cache_handler=self._cache_handler
            )
            cached_token = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
            if not cached_token:
                raise Exception("No cached token is available")
            access_token = cached_token["access_token"]


            self._sp_token = spotipy.Spotify(auth=access_token)

        self._sp = spotipy.Spotify(auth_manager=auth_manager_no_token)

    @handle_spotify_token_errors
    def get_current_playing_song(self) -> Generator[UIPromptRequest, Any, dict[str, Any]]:
        """
        Gets the current playing song from user's spotify (using the tokens)
        :return: A dict of the song metadata (spotify)
        :rtype: dict[str, Any]
        """
        return self._sp_token.current_user_playing_track()

    def spotify_search_song_metadata_by_id(self, query: str) -> dict:
        """
        Searches for a song on Spotify and returns the metadata
        :param query: ID of spotify track
        :type query: str
        :return: metadata of the song
        :rtype: dict[str, Any]
        """
        return self._sp.track(query)

    def spotify_search_song(self, query: str, offset: int, limit: int) -> dict:
        return self._sp.search(q=query, offset=offset, limit=limit)

    @staticmethod
    def milliseconds_to_minutes_and_seconds(milliseconds: int | float) -> str:
        if isinstance(milliseconds, float):
            milliseconds = int(milliseconds)

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


    def download_song(self, limit: int = 10,
                      retry_count: int = 3,
                      retry_sleep: float = 5) -> Generator[Any, dict[str, Any], bool | str]:
        # SPOTIFY SECTION
        offset: int = 0
        youtube_query: str = ""
        song_list = None

        query = yield UIPromptRequest(
            type="input",
            message="Please input song to query: ",
            sub_type="query",
            placeholder="Query to search",
        )
        first_yt = query["first_yt"]
        query = query["value"]

        if query == "__current_song__":
            pipeline = self.get_current_playing_song()
            try:
                prompt_request = next(pipeline)

                if prompt_request.type == "hidden_request" and prompt_request.message == 401:
                    self.authenticate()
                    pipeline.send(True)

            except StopIteration as e:
                current_track = e.value

            current_track_metadata = current_track["item"]
            spotify_metadata = current_track_metadata
            title, artist = self.get_title_artist(current_track_metadata).values()
            duration: str = self.milliseconds_to_minutes_and_seconds(current_track_metadata["duration_ms"])
            youtube_query: str = f"ytsearch{limit}:{title} - {artist}"
        else:
            persistent_choices = [{"type": "__nav__", "display": "Next", "value": "__next__"},
                                  {"type": "__nav__", "display": "Previous", "value": "__prev__"},
                                  {"type": "__nav__", "display": "New Query", "value": "__new__"}]
            while True:
                for _ in range(retry_count):
                    try:
                        song_list = self.spotify_search_song(query, offset, limit)["tracks"]["items"]
                    except Exception as e:
                        # TODO add exception handling
                        sleep(retry_sleep)
                        song_list = None
                        raise e
                if song_list is None:
                    # TODO add exception handling
                    raise Exception(f"Could not retrieve songs from {query}")

                formatted_choices: list[dict[str, Any]] = []

                for list_idx, song in enumerate(song_list):
                    formatted_choices.append({
                        "type": "__option__",
                        "title": self.get_title_artist(song)["title"],
                        "artist": self.get_title_artist(song)["artist"],
                        "duration": self.milliseconds_to_minutes_and_seconds(song["duration_ms"]),
                        "album": song["album"]["name"],
                        "relevance": song["popularity"],
                        "value": list_idx,
                        "metadata": song
                    })
                formatted_choices.extend(persistent_choices)

                user_choice: dict[str, Any] = yield UIPromptRequest(
                    type="select",
                    message="Please choose your song:",
                    choices=formatted_choices,
                    sub_type="spotify",
                    extra_info={"page": (offset // limit) + 1}
                )

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
                            placeholder="Query to search",
                            sub_type="query"
                        )
                        query = query["value"]
                    case _:
                        song_choice: dict[str, Any] = formatted_choices[user_choice["value"]]
                        spotify_metadata = song_choice["metadata"]
                        title = song_choice["title"]
                        artist = song_choice["artist"]
                        duration: str = self.milliseconds_to_minutes_and_seconds(spotify_metadata["duration_ms"])
                        youtube_query: str = f"ytsearch{limit}:{title} - {artist}"
                        break


        # YOUTUBE SECTION
        ydl_opts = {'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for _ in range(retry_count):
                try:
                    info = ydl.extract_info(youtube_query, download=False)
                except Exception as e:
                    # TODO add exception handling
                    sleep(retry_sleep)
                    info = None

            if info is None:
                # TODO add fall back query
                raise Exception(f"Could not extract info from {youtube_query}")
            info = ydl.sanitize_info(info)
            results = info.get("entries", [])

            persistent_choices = [
                                  {"type": "__nav__", "display": "New Query", "value": "__new__"}
            ]

            formatted_choices = []
            for list_idx, track in enumerate(results):
                formatted_choices.append({
                    "type": "__option__",
                    "id": track.get("id"),
                    "title": track.get("title"),
                    "uploader": track.get("uploader"),
                    "duration": self.milliseconds_to_minutes_and_seconds(track.get("duration") * 1000),
                    "view_count": track.get("view_count"),
                    "value": list_idx,
                    "metadata": track
                })
            formatted_choices.extend(persistent_choices)

            if first_yt:
                user_choice = formatted_choices[0]
            else:
                user_choice: dict[str, Any] = yield UIPromptRequest(
                    type="select",
                    message=f"Song: {title} | {artist}\nDuration: {duration}\n\nPlease choose the matching song previously: ",
                    choices=formatted_choices,
                    sub_type="youtube"
                )

            user_choice = formatted_choices[user_choice["value"]]
            youtube_id = user_choice["id"]
            youtube_metadata = user_choice["metadata"]

        try:
            file_path = Path(TEMP_DIR / f"{youtube_id}.wav")
            if file_path.exists():
                return "File already exists, exiting early."
        except FileNotFoundError:
            pass

        class YTInfoLogger():
            def __init__(self, input_queue: queue.Queue):
                self.log_queue = input_queue

            def debug(self, msg):
                self.log_queue.put(("log", msg))

            def info(self, msg):
                self.log_queue.put(("log", msg))

            def error(self, msg):
                self.log_queue.put(("log", msg))

            def warning(self, msg):
                self.log_queue.put(("log", msg))

        log_queue = queue.Queue()

        ydl_opts = {'format': 'm4a/bestaudio/best',
                    "logger": YTInfoLogger(log_queue),
                    'paths': {'home': f'{str(TEMP_DIR)}'},
                    'outtmpl': '%(id)s.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'wav',
                    }]}

        success_downloading = False

        yield UIPromptRequest(type="info",
                              message=f"Downloading {youtube_id}")

        def _target_download():
            nonlocal success_downloading
            for _ in range(retry_count):
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([youtube_id])
                    success_downloading = True
                    break
                except Exception as e:
                    log_queue.put(("log", e))
                    sleep(retry_sleep)

            log_queue.put(("__done__", ""))


        downloader_thread = threading.Thread(target=_target_download)
        downloader_thread.start()

        while downloader_thread.is_alive() or not log_queue.empty():
            try:
                msg_type, msg_text = log_queue.get(timeout=0.1)

                if msg_type == "__done__":
                    break

                # Yield the message smoothly straight back up to your Textual screen UI!
                yield UIPromptRequest(type=msg_type, message=msg_text)

            except queue.Empty:
                continue

        if not success_downloading:
            raise Exception(f"Could not download {youtube_id}")
        # FINAL WRITE

        final_data = {
            "pre_processing": {
                "youtube_id": youtube_id,
                "view_name": f"{title} - {artist}",
                "raw_metadata": spotify_metadata,
                "youtube_metadata": youtube_metadata,
                "downloaded": True
            }
        }
        file_path = TEMP_DIR / f"{title} - {artist}.json"
        json_data = json.dumps(final_data, indent=4, ensure_ascii=True)
        file_path.write_text(json_data)

        return True