import json
from pathlib import Path
from typing import Generator

from dotenv import set_key
from questionary import confirm, path

from engine.database.main_database import MainDatabase
from engine.main import logger
from engine.utils.default.default_var import DEFAULT_CONFIG, DEFAULT_DICTS_MESSAGE
from engine.utils.functions.filesystem import load_env_file, clear_temp_dir, read_json_file, write_json_file
from engine.utils.paths import SRC_DIR


class Analyzer:
    def __init__(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def init(self) -> Generator[str, None, None]:
        """Initialize the analyzer."""
        self.setup_main_directories()
        yield "Successfully created directory structure."

        load_env_file()
        yield "Successfully loaded environment variables."

        self.setup_config_file()
        yield "Successfully loaded configuration file."

        with MainDatabase() as db:
            db.create_table()
        yield "Successfully created database."

    # region Helper Functions
    def setup_main_directories(self) -> None:
        """Sets up the main directories for the analyzer."""
        folder = ["data", "config", "models", ".temp", "dicts", ".cache"]
        for p in folder:
            Path(SRC_DIR / p).mkdir(parents=True, exist_ok=True)
        logger.debug("Main Directories created.")

        self.create_misc_files()

    @staticmethod
    def setup_config_file() -> None:
        """Sets up the config file for the analyzer. Writes default values if it doesn't exist."""
        config_file = Path(SRC_DIR / "config/config.json")

        if not config_file.exists():
            config_json = json.dumps(DEFAULT_CONFIG, indent=4)
            config_file.write_text(config_json)
            logger.debug("Created config file and set default values.")
        else:
            config_json = config_file.read_text()
            logger.debug("Config file exists, read config file")

        config_json = json.loads(config_json)

        logger.info(f"miraa-alternative Version: {config_json['version']}")

    @staticmethod
    def create_misc_files() -> None:
        # dicts directory
        dicts_dir = Path(SRC_DIR / "dicts")
        dicts_file = dicts_dir / "readme.md"
        if not dicts_file.exists():
            dicts_file.write_text(DEFAULT_DICTS_MESSAGE, encoding="utf-8")
        else:
            pass

    # endregion

    # endregion
