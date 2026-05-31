# STANDARD LIBRARIES
import json
import os
import asyncio
import gc
from concurrent.futures.thread import ThreadPoolExecutor

# PYPI LIBRARIES
from questionary import confirm, path

from enum import Enum, auto
from dotenv import load_dotenv, set_key
from pathlib import Path

# HELPER LIBRARIES
from backend_new.utils.helper_funcs import read_json_file, write_json_file, questionary_select, questionary_checkbox

from backend_new.extractors import downloader
from backend_new.extractors.geniusextractor import GeniusExtractor

from backend_new.core.processing import VocalSeparation, JPAnalyzer
from backend_new.core.translation_analysis import Translator

from backend_new.utils.constants import SongContext, DataMismatchError
from backend_new.utils.constants import TEMP_DIR

from backend_new.utils.logger import Logger
logger = Logger()

class WorkflowManager:
    def __init__(self, env_keys: dict[str, str] = None):
        if env_keys is None:
            raise ValueError("Please provide the env_keys")

        self._dl = None
        self._translator = None

    #! TODO move quesitonary to main
    def _init_downloader(self) -> None:
        """
        Initializes the downloader for spotify and YouTube
        """
        if self._dl is None:
            if self._config_json["youtube_downloader"]["use_cookies"]:
                if self._env_data["YOUTUBE_COOKIE_PATH"] == '' or self._env_data["YOUTUBE_COOKIE_PATH"] is None:
                    use_cookies = confirm("Do you want to use cookies?").ask()
                    if use_cookies:
                        cookie_path = path("Please enter the path to your cookies file (Netscape .txt file): ").ask()
                        self._env_data["YOUTUBE_COOKIE_PATH"] = cookie_path
                        set_key(self._env_file, "YOUTUBE_COOKIE_PATH", cookie_path, quote_mode="never")
                    else:
                        read_json_file(self._config_file)
                        write_json_file(self._config_file, False, ["youtube_downloader", "use_cookies"])
                        set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")
            else:
                if self._env_data["YOUTUBE_COOKIE_PATH"] != '':
                    set_key(self._env_file, "YOUTUBE_COOKIE_PATH", '', quote_mode="never")

            self._dl = downloader.Downloader(spotify_client_id=self._env_data["SPOTIFY_CLIENT_ID"],
                                             spotify_client_secret=self._env_data["SPOTIFY_CLIENT_SECRET"],
                                             youtube_cookie_path=self._env_data["YOUTUBE_COOKIE_PATH"],
                                             cli_output_format=self._config_json["spotify_downloader"]["output_format"])

    def download_song(self, json_file: Path) -> None:
        """
        Downloads a song from YouTube using metadata present in .temp
        When no files are present, it will query spotify
        :param json_file: A path to a JSON file containing metadata, optional
        """
        def get_youtube_id_from_json(file_path: Path) -> str | None:
            if file_path.suffix == ".json":
                return str(read_json_file(file_path)["pre_processing"]["youtube_id"])
            return None

        def _download(file_path: Path | str | None) -> None:
            if file_path is None:
                raise Exception("No file path provided")
            if type(file_path) is str:
                asyncio.to_thread(self._dl.download_youtube_video, url=file_path)
            if type(file_path) is Path:
                asyncio.to_thread(self._dl.download_youtube_video, url=get_youtube_id_from_json(file_path))

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
                        offset = 0

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
                    self.query_song_spotify()
        else:
            target_id = get_youtube_id_from_json(json_file)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_download(target_id))
            except RuntimeError:
                asyncio.run(_download(target_id))

    # region all processes, returns True if already done
    def _download(self, song_context_data: SongContext) -> bool:
        """
        Downloads the song, checks if the audio file is present in the .temp dir, if not handle appropriately
        :return: True if already downloaded, False if not
        """
        if song_context_data.json_song_data.get("pre_processing", {}).get("downloaded", False):
            # checks if the audio file is present in the .temp dir, if not handle appropriately
            if song_context_data.json_song_data["pre_processing"].get("youtube_id", None) not in [file.stem for file
                                                                                                  in
                                                                                                  TEMP_DIR.iterdir()
                                                                                                  if
                                                                                                  file.suffix == ".wav"]:
                logger.warning(
                    "Data file says audio has been downloaded, but it isn't present in .temp directory")
                logger.warning(
                    "Please do not rename, convert or alter files in .temp to prevent further errors")
                logger.warning("Please clear all files in .temp directory to ensure proper functionality")
                raise DataMismatchError(logger,
                                             "Data file says audio has been downloaded, but it isn't present in .temp directory")
            logger.debug(f"Song already downloaded, skipping")
            return True
        else:
            logger.debug(f"Song not downloaded, downloading it now.")
            self.download_song(song_context_data.json_file_path)
            write_json_file(song_context_data.json_file_path, True, ["pre_processing", "downloaded"])
            logger.debug(f"Song downloaded.")
            return False

    def _genius_pull(self, song_context_data: SongContext) -> bool:
        """
        Pulls Genius metadata for the song
        :return: True if already done, False if not
        """
        if song_context_data.json_song_data.get("genius_data", None) is not None:
            logger.debug(f"Genius data already present, skipping")
            return True
        else:
            logger.debug(f"Genius data not present, pulling it now.")
            genius_data = GeniusExtractor(self._env_data["GENIUS_ACCESS_TOKEN"]).return_metadata(
                title=song_context_data.json_song_data["pre_processing"]["raw_metadata"]["name"],
                artist=song_context_data.json_song_data["pre_processing"]["raw_metadata"]["artists"][0]["name"]
            )
            write_json_file(song_context_data.json_file_path, genius_data, ["genius_data"])
            logger.debug(f"Genius data pulled.")
            return False

    def _vocal_sep(self, song_context_data: SongContext) -> bool:
        """
        Separates the audio into its stems
        :return: True if already done, False if not
        """
        # TODO add vocal sep model chooser
        if song_context_data.json_song_data.get("vocal_separation", {}).get("separated", False) is True:
            if song_context_data.json_song_data.get("vocal_separation", {}).get("vocal_file", None) not in [
                file.stem for file in TEMP_DIR.iterdir() if file.suffix == ".wav"]:
                raise DataMismatchError(logger,
                                             "Data file says audio has been separated, but it isn't present in .temp directory")
            if song_context_data.json_song_data.get("vocal_separation", {}).get("inst_file", None) not in [file.stem
                                                                                                           for file
                                                                                                           in
                                                                                                           TEMP_DIR.iterdir()
                                                                                                           if
                                                                                                           file.suffix == ".wav"]:
                raise DataMismatchError(logger,
                                             "Data file says audio has been separated, but it isn't present in .temp directory")

            logger.debug(f"Vocal separation already done, skipping")
            return True
        else:
            with VocalSeparation() as vs:
                vs.separate_vocal(
                    f"../.temp/{song_context_data.json_song_data["pre_processing"]["youtube_id"]}.wav")
                write_json_file(song_context_data.json_file_path, {"separated": True,
                                                                   "vocal_file": f"{song_context_data.json_song_data["pre_processing"]["youtube_id"]}_vocal",
                                                                   "inst_file": f"{song_context_data.json_song_data["pre_processing"]["youtube_id"]}_inst"},
                                ["vocal_separation"])

            return False

    # TODO requires rework as processing is changing
    def _lyrics_tag(self, song_context_data: SongContext) -> bool:
        if song_context_data.json_song_data.get("split_and_tag", {}):
            logger.debug(f"Lyrics already tagged, skipping")
            return True
        else:
            logger.debug(f"Lyrics not tagged, tagging it now.")

            jp_analyzer = JPAnalyzer()

            lyrics = song_context_data.json_song_data["genius_data"]["lyrics"]
            # ! UNABLE TO BE USED FOR NOW
            data = jp_analyzer.tag(lyrics)
            write_json_file(song_context_data.json_file_path, data, ["split_and_tag"])
            return False

    def _translate_lyrics(self, song_context_data: SongContext) -> bool:
        if song_context_data.json_song_data.get("translated_lyrics", {}):
            logger.debug(f"Lyrics already translated, skipping")
            return True
        else:
            logger.debug(f"Lyrics not translated, translating it now.")

            if self._translator is None:
                self._translator = Translator()

            lyrics = song_context_data.json_song_data["genius_data"]["lyrics"]
            data = self._translator.translate_lyrics(lyrics)

            write_json_file(song_context_data.json_file_path, data, ["translated_lyrics"])

            return False

    # endregion
