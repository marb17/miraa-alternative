from backend_new.utils.logger import Logger

#===================================================
#       ERRORS / EXCEPTIONS
#===================================================

# region FILE SYSTEM
class DataMismatchError(Exception):
    def __init__(self, logger: Logger, message: str = 'Files do not match the data in .temp directory') -> None:
        """
        An error occurring when a data file does not match the expected files or other data required
        :param logger: Logger object used for logging instructions
        :type logger: Logger
        :param message: Custom message to display
        :type message: str
        """
        self.logger = logger
        self.message = message

        self.data_mismatch_error()

        super().__init__(self.message)

    def data_mismatch_error(self):
        self.logger.warning(self.message)
        self.logger.warning("Please do not rename, convert or alter files in .temp to prevent further errors")
        self.logger.warning("Please clear all files in .temp directory to ensure proper functionality")
# endregion

# region YOMITAN DICTS
class InvalidDictDefinitionFormatError(Exception):
    """Format of the raw dictionary entry is not as expected"""
    pass
# endregion