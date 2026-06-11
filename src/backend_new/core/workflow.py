# STANDARD LIBRARIES
from concurrent.futures.thread import ThreadPoolExecutor

# PYPI LIBRARIES
from pathlib import Path

# HELPER LIBRARIES
from backend_new.utils.helper_funcs import read_json_file, write_json_file, questionary_select, load_env_file, contains_japanese

from backend_new.utils.constants import SongContext, DataMismatchError

# CONSTANTS
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

    # region all processes, returns True if already done
    def download(self, song_context_data: SongContext) -> bool:
        """
        Downloads the song, checks if the audio file is present in the .temp dir, if not handle appropriately
        :param song_context_data: SongContext for data
        :type song_context_data: SongContext
        :return: True if already downloaded, False if not
        :rtype: bool
        """
        from backend_new.extractors.downloader import Downloader

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
            with Downloader() as dl:
                dl.select_song_to_download(song_context_data.json_file_path)
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

            write_json_file(song_context_data.json_file_path, genius_data, ["genius_data"])

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
        if song_context_data.json_song_data.get("vocal_separation", {}).get("separated", {}).get("vocal", False) is True:
            if song_context_data.json_song_data.get("vocal_separation", {}).get("vocal_file", None) not in [
                file.stem for file in TEMP_DIR.iterdir() if file.suffix == ".wav"]:
                raise DataMismatchError(logger,
                                             "Data file says audio has been separated, but it isn't present in .temp directory")
            logger.debug(f"Vocal separation already done, skipping")
            return True
        else:
            with VocalSeparation() as vs:
                vs.separate_audio(
                    f"../.temp/{song_context_data.json_song_data["pre_processing"]["youtube_id"]}.wav")
                write_json_file(song_context_data.json_file_path, {"separated": {"vocal": True}, "vocal_file": f"{song_context_data.json_song_data["pre_processing"]["youtube_id"]}_vocal"},
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
