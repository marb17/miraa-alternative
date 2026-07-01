# STANDARD LIBRARIES
import json

from dotenv import set_key
from pathlib import Path

from collections.abc import Generator

from typing import Any

# HELPER LIBRARIES
# from backend_new.utils.helper_funcs import (questionary_select, questionary_checkbox)
from backend_new.utils.functions.filesystem import read_json_file, write_json_file, write_config, write_env_key, \
    load_env_file, clear_temp_dir

from backend_new.core.workflow import WorkflowManager

# PYPI LIBRARIES
from questionary import Choice, confirm, path

# CONSTANTS
from backend_new.utils.classes.dataclasses import SongContext
from backend_new.utils.default.default_var import DEFAULT_CONFIG, DEFAULT_DICTS_MESSAGE

from backend_new.utils.logger import Logger
logger = Logger(__name__)


class Analyzer:
    def __init__(self) -> None:
        self.init()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def init(self) -> Generator[str, None, None]:
        """Initialize the analyzer."""
        self.setup_main_directories()
        yield "Successfully created directory structure."

        self._env_data = load_env_file()
        yield "Successfully loaded environment variables."

        self.setup_config_file()
        yield "Successfully loaded configuration file."

    # region Helper Functions
    def setup_main_directories(self) -> None:
        """Sets up the main directories for the analyzer."""
        current_dir = Path(__file__).resolve().parent
        while current_dir.name != "src" and current_dir != current_dir.parent:
            current_dir = current_dir.parent
        self._base_dir = current_dir

        folder = ["data", "config", "models", ".temp", "dicts", ".cache"]
        for p in folder:
            Path(self._base_dir / p).mkdir(parents=True, exist_ok=True)
        logger.debug("Main Directories created.")

        self._temp_dir = Path(self._base_dir / ".temp")
        self._config_file = Path(self._base_dir / "config/config.json")
        self._env_file = Path(self._base_dir / "config/.env")

        self.create_misc_files()

    def setup_config_file(self) -> None:
        """Sets up the config file for the analyzer. Writes default values if it doesn't exist."""
        if not self._config_file.exists():
            config_json = json.dumps(DEFAULT_CONFIG, indent=4)
            self._config_file.write_text(config_json)
            logger.debug("Created config file and set default values.")
        else:
            config_json = self._config_file.read_text()
            logger.debug("Config file exists, read config file")

        self._config_json = json.loads(config_json)

        logger.info(f"miraa-alternative Version: {self._config_json['version']}")

    def create_misc_files(self) -> None:
        # dicts directory
        dicts_dir = Path(self._base_dir / "dicts")
        dicts_file = dicts_dir / "readme.md"
        if not dicts_file.exists():
            dicts_file.write_text(DEFAULT_DICTS_MESSAGE, encoding="utf-8")
        else:
            pass

    @staticmethod
    def _clear_temp_directory() -> None:
        clear_temp_dir()
    # endregion

    # region pre-process checking
    def _check_downloader(self) -> None:
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

    def _pre_check_settings(self) -> None:
        ...

    # endregion


def main() -> None:
    ana = Analyzer()
    # ana._download("https://open.spotify.com/track/0UFmgncRMHavVzYxtpF0IZ?si=1c86deb161b24778")
    # ana._download("https://open.spotify.com/track/0VPkaJMRQIhYWXiE1LqaCK?si=a867127aa85a4769")
    # ana.download_song()
    # ana.query_song_spotify()
    ana.process_song()
    # ana._clear_temp_directory()

if __name__ == "__main__":
    main()