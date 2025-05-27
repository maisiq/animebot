import logging
import sys


class LogFormatter(logging.Formatter):
    """Colorful log formatter"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    green = "\x1b[32;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(levelname)s] %(asctime)s | %(name)s | %(message)s (%(filename)s:%(lineno)d)"
    datefmt = '%Y-%m-%d %H:%M'

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logger(file_logger: bool = True):
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(LogFormatter())
    logger.addHandler(ch)

    if file_logger:
        fh = logging.FileHandler('logs/logs.log')
        fh.setLevel(logging.WARNING)
        fh.setFormatter(LogFormatter())
        logger.addHandler(fh)
