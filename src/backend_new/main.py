class Analyzer:
    DEFAULT_CONFIG = {
        "version": "1.0.0",
    }

    DEFAULT_ENV_VARS = [
        "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET",
    ]

    def __init__(self) -> None:
        """Initialize the analyzer."""
        import logger
        self._logger = logger.Logger()

        self._setup_main_directories()
        self._load_env_file()
        self._setup_config_file()

    # region Helper Functions
    def _setup_main_directories(self) -> None:
        """Sets up the main directories for the analyzer."""
        from pathlib import Path

        self._base_dir = Path("../")
        folder = ["data", "config", "models", ".temp"]
        for path in folder:
            Path(self._base_dir / path).mkdir(parents=True, exist_ok=True)
        self._logger.debug("Main Directories created.")

    def _setup_config_file(self) -> None:
        """Sets up the config file for the analyzer. Writes default values if it doesn't exist."""
        from pathlib import Path
        import json

        self._config_file = Path(self._base_dir / "config/config.json")
        if not self._config_file.exists():
            config_json = json.dumps(self.DEFAULT_CONFIG, indent=4)
            self._config_file.write_text(config_json)
            self._logger.debug("Created config file and set default values.")
        else:
            config_json = self._config_file.read_text()
            self._logger.debug("Config file exists, read config file")

        self._config_json = json.loads(config_json)

        self._logger.info(f"miraa-alternative Version: {self._config_json['version']}")

    def _load_env_file(self) -> None:
        """
        Loads the environment variables from the .env file.
        Creates a new .env file if it doesn't exist.
        DOES NOT check if the file is filled
        """
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        self._env_file = Path(self._base_dir / "config/.env")
        if self._env_file.exists():
            load_dotenv(dotenv_path=self._env_file)
            self._logger.debug("Loaded .env file.")
        else:
            self._logger.critical("No .env file found. Creating empty .env file. Do NOT reorder the variables")
            self._env_file.write_text("\n".join([f"{var}=" for var in self.DEFAULT_ENV_VARS]))
            raise FileNotFoundError(".env file not found, creating one. Please add your credentials to the .env file.")

        load_dotenv()
        self._env_data = dict([(var, os.getenv(var))for var in self.DEFAULT_ENV_VARS])

    @staticmethod
    def _str_to_base58(string: str) -> str:
        import base58
        return base58.b58encode(string.encode('utf-8')).decode('utf-8')

    @staticmethod
    def _base58_to_str(string: str) -> str:
        import base58
        return base58.b58decode(string).decode('utf-8')
    # endregion

    def _download(self, link: str) -> None:
        """
        Downloads a file from a given link.
        :param link: The link to the file to download. Supports ...
        """
        import downloader


def main() -> None:
    ana = Analyzer()


if __name__ == "__main__":
    main()