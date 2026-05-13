class Analyzer:
    def __init__(self) -> None:
        """Initialize the analyzer."""
        import logger
        self._logger = logger.Logger()

        self._setup_main_directories()
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

        defaults = {
            "version" : "1.0.0",
            "settings" : {
                "song_download_source" : ['youtube', 'spoti', 'apple', 'tidal']
            }
        }

        self._config_file = Path(self._base_dir / "config/config.json")
        if not self._config_file.exists():
            config_json = json.dumps(defaults, indent=4)
            self._config_file.write_text(config_json)
            self._logger.debug("Created config file and set default values.")
        else:
            config_json = self._config_file.read_text()
            self._logger.debug("Config file exists, read config file")

        self._config_json = json.loads(config_json)

        self._logger.info(f"miraa-alternative Version: {self._config_json['version']}")

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
        ...


def main() -> None:
    ana = Analyzer()
    # ana._download("https://open.spotify.com/track/0UFmgncRMHavVzYxtpF0IZ?si=1b46c029e46744db")
    ana._download("https://www.youtube.com/watch?v=0skXAu6h6To")


if __name__ == "__main__":
    main()