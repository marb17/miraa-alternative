import logging, coloredlogs

class Logger:
    def __init__(self, name: str, init_message: bool = False):
        self._logger = logging.getLogger(name)

        # LOG FILTER
        logging.getLogger("audio_separator").setLevel(logging.WARNING)
        logging.getLogger("audio_separator.separator").setLevel(logging.WARNING)
        logging.getLogger("torch").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("yt_dlp").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("numba").setLevel(logging.WARNING)
        logging.getLogger("pydub").setLevel(logging.WARNING)

        coloredlogs.install(logger=self._logger,
                            level="DEBUG")

        # all logger methods
        self.debug = self._logger.debug
        self.info = self._logger.info
        self.warning = self._logger.warning
        self.error = self._logger.error
        self.critical = self._logger.critical

        if init_message:
            self._logger.debug("Logger initialized")