import logging, coloredlogs

class Logger:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

        coloredlogs.install(logger=self._logger,
                            level="DEBUG")

        # all logger methods
        self.debug = self._logger.debug
        self.info = self._logger.info
        self.warning = self._logger.warning
        self.error = self._logger.error
        self.critical = self._logger.critical

        self._logger.debug("Logger initialized")