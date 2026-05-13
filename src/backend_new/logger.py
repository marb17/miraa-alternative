class Logger:
    def __init__(self):
        import logging, coloredlogs

        self._logger = logging.getLogger("backend")

        coloredlogs.install(logger=self._logger,
                            level="DEBUG")

        # all logger methods
        self.debug = self._logger.debug
        self.info = self._logger.info
        self.warning = self._logger.warning
        self.error = self._logger.error
        self.critical = self._logger.critical

        self._logger.debug("Logger initialized")