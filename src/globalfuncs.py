# global functions

# string to base58
import base58

def str_to_base58(text_input: str) -> str:
    bytes = text_input.encode('utf-8')
    base58_string = base58.b58encode(bytes)
    return base58_string.decode('utf-8')

# base58 to string
def base58_to_str(base58_string: str) -> str:
    base58_bytes = base58_string.encode('ascii')
    decoded_bytes = base58.b58decode(base58_bytes)
    return decoded_bytes.decode('utf-8')


# logging
import logging
import coloredlogs

# Custom log levels
logging.addLevelName(1, "PLAIN")
logging.addLevelName(5, "SPAM")
logging.addLevelName(15, "VERBOSE")
logging.addLevelName(25, "NOTICE")
logging.addLevelName(35, "SUCCESS")

# Add convenience methods to logger
def plain(self, message, *args, **kwargs):
    if self.isEnabledFor(1):
        self._log(1, message, args, **kwargs)

def spam(self, message, *args, **kwargs):
    if self.isEnabledFor(5):
        self._log(5, message, args, **kwargs)

def verbose(self, message, *args, **kwargs):
    if self.isEnabledFor(15):
        self._log(15, message, args, **kwargs)

def notice(self, message, *args, **kwargs):
    if self.isEnabledFor(25):
        self._log(25, message, args, **kwargs)

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(35):
        self._log(35, message, args, **kwargs)

logging.Logger.plain = plain
logging.Logger.spam = spam
logging.Logger.verbose = verbose
logging.Logger.notice = notice
logging.Logger.success = success

logger = logging.getLogger("miraa-alt")
logger.setLevel(1)  # capture everything from spam up

# Define log format and date format
log_format = "%(asctime)s | %(name)s[%(process)d] | %(levelname)s | %(message)s"
date_format = "%H:%M:%S"

# Define level colors (matching your example)
level_styles = {
    "PLAIN": {"color": "white"},
    "SPAM": {"color": 22},       # ANSI color codes
    "DEBUG": {"color": 28},
    "VERBOSE": {"color": 34},
    "NOTICE": {"color": 220},
    "INFO": {"color": None},
    "SUCCESS": {"color": 118, "bold": True},
    "WARNING": {"color": 202},
    "ERROR": {"color": 124},
    "CRITICAL": {"background": "red"}
}

coloredlogs.install(
    level=1,
    logger=logger,
    fmt=log_format,
    datefmt=date_format,
    level_styles=level_styles,
    field_styles={"asctime": {"color": "white"},
                  "name": {"color": "white"},
                  "sep": {"color": "white"}},  # no styles for fields
    milliseconds=True,
)

logger.propagate = False

# logger.plain("Message with level plain (1)")
# logger.spam("Message with level spam (5)")
# logger.debug("Message with level debug (10)")
# logger.verbose("Message with level verbose (15)")
# logger.info("Message with level info (20)")
# logger.notice("Message with level notice (25)")
# logger.warning("Message with level warning (30)")
# logger.success("Message with level success (35)")
# logger.error("Message with level error (40)")
# logger.critical("Message with level critical (50)")