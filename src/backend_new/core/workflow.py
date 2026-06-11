# STANDARD LIBRARIES
from concurrent.futures.thread import ThreadPoolExecutor

# PYPI LIBRARIES
from pathlib import Path

# HELPER LIBRARIES
from backend_new.utils.helper_funcs import read_json_file, write_json_file, questionary_select, load_env_file, contains_japanese

from backend_new.utils.exceptions import DataMismatchError
from backend_new.utils.structures import SongContext
from backend_new.utils.constants import TEMP_DIR

from backend_new.utils.logger import Logger

logger = Logger(__name__)

class WorkflowManager:
    def __init__(self, song_ctx: SongContext) -> None:
        """
        Loads the WorkflowManager for a specific song
        :param song_ctx: Song to be processed
        :type song_ctx: SongContext
        """
        self._env_data = load_env_file()
        self._song_ctx = song_ctx

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()
        return False

    @staticmethod
    def _cleanup() -> None:
        import gc
        gc.collect()

        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()


    def refresh_song_context(self) -> None:
        """
        Updates the .json data to be the newest
        :return: None
        :rtype: None
        """
        self._song_ctx.json_song_data = read_json_file(self._song_ctx.json_file_path)


    @staticmethod
    def _download_song(json_file: Path | None) -> None:
        """
        Downloads a song from YouTube using metadata present in .temp
        When no files are present, it will query spotify
        :param json_file: A path to a JSON file containing metadata
        :type json_file: Path | None
        :return: None
        :rtype: None
        """
        from backend_new.extractors.downloader import Downloader

        def get_youtube_id_from_json(file_path: Path) -> str | None:
            if file_path.suffix == ".json":
                return str(read_json_file(file_path)["pre_processing"]["youtube_id"])
            return None

        def _download(file_path: Path | str | None) -> None:
            if file_path is None:
                raise Exception("No file path provided")
            with Downloader() as downloader:
                if type(file_path) is str:
                    downloader.download_youtube_video(url=file_path)
                if type(file_path) is Path:
                    downloader.download_youtube_video(url=get_youtube_id_from_json(file_path))

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

    # region all processes, returns True if already done
    def download(self, song_context_data: SongContext) -> bool:
        """
        Downloads the song, checks if the audio file is present in the .temp dir, if not handle appropriately
        :param song_context_data: SongContext for data
        :type song_context_data: SongContext
        :return: True if already downloaded, False if not
        :rtype: bool
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
            self._download_song(song_context_data.json_file_path)
            write_json_file(song_context_data.json_file_path, True, ["pre_processing", "downloaded"])
            logger.debug(f"Song downloaded.")
            return False

    def genius_pull(self, song_context_data: SongContext) -> bool:
        """
        Pulls Genius metadata for the song
        :param song_context_data: SongContext for data
        :type song_context_data: SongContext
        :return: True if already done, False if not
        :rtype: bool
        """
        from backend_new.extractors.geniusextractor import GeniusExtractor
        from backend_new.core.translation_analysis import Translator

        if song_context_data.json_song_data.get("genius_data", None) is not None:
            logger.debug(f"Genius data already present, skipping")
            return True
        else:
            logger.debug(f"Genius data not present, pulling it now.")
            with GeniusExtractor(self._env_data["GENIUS_ACCESS_TOKEN"]) as genius:
                genius_data = genius.return_metadata(
                    title=song_context_data.json_song_data["pre_processing"]["raw_metadata"]["name"],
                    artist=song_context_data.json_song_data["pre_processing"]["raw_metadata"]["artists"][0]["name"]
                )
            write_json_file(song_context_data.json_file_path, genius_data, ["genius_data"])

            # check if lyrics are romanized
            if not contains_japanese(genius_data.get("lyrics", "")):
                logger.warning("Lyrics are romanized, using LLM to convert to Japanese script")

                with Translator() as translator:
                    script_lyrics = translator.romaji_to_script(genius_data["lyrics"])

                write_json_file(song_context_data.json_file_path, script_lyrics, ["lyrics_main"])
                write_json_file(song_context_data.json_file_path, genius_data["lyrics"], ["lyrics_sub"])
            else:
                write_json_file(song_context_data.json_file_path, genius_data["lyrics"], ["lyrics_main"])
                write_json_file(song_context_data.json_file_path, "", ["lyrics_sub"])

            logger.debug(f"Genius data pulled.")
            return False

    @staticmethod
    def vocal_sep(song_context_data: SongContext) -> bool:
        """
        Separates the audio into its stems
        :param song_context_data: SongContext for data
        :type song_context_data: SongContext
        :return: True if already done, False if not
        :rtype: bool
        """
        from backend_new.core.processing import VocalSeparation

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
    @staticmethod
    def lyrics_tag(song_context_data: SongContext) -> bool:
        """
        on work
        :param song_context_data:
        :type song_context_data:
        :return:
        :rtype:
        """
        from backend_new.core.processing import JPAnalyzer

        if song_context_data.json_song_data.get("split_and_tag", {}):
            logger.debug(f"Lyrics already tagged, skipping")
            return True
        else:
            logger.debug(f"Lyrics not tagged, tagging it now.")

            jp_analyzer = JPAnalyzer()

            lyrics = song_context_data.json_song_data["lyrics_main"]
            # ! UNABLE TO BE USED FOR NOW
            data = jp_analyzer.tag(lyrics)
            write_json_file(song_context_data.json_file_path, data, ["split_and_tag"])
            return False

    @staticmethod
    def translate_lyrics(song_context_data: SongContext) -> bool:
        """
        Translates the lyrics to English
        :param song_context_data: SongContext for data
        :type song_context_data: SongContext
        :return: True if already done, False if not
        :rtype: bool
        """
        from backend_new.core.translation_analysis import Translator

        if song_context_data.json_song_data.get("translated_lyrics", {}):
            logger.debug(f"Lyrics already translated, skipping")
            return True
        else:
            logger.debug(f"Lyrics not translated, translating it now.")

            lyrics = song_context_data.json_song_data["lyrics_main"]
            with Translator() as translator:
                data = translator.translate_lyrics(lyrics)

            write_json_file(song_context_data.json_file_path, data, ["translated_lyrics"])

            return False

    # endregion
