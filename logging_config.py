from logging import getLogger, Formatter, StreamHandler, Logger
from os import environ
from sys import stdout

LOG_FORMAT = '{message:<80} | {asctime}:{levelname:<9} | {module}:{funcName}:{lineno}'


def setup_logging() -> Logger:
    log = getLogger()
    log.setLevel(environ.get('LOGGING_LEVEL', 'INFO'))
    log.addHandler(get_normal_formatter())

    return log


def get_normal_formatter():
    formatter = Formatter(LOG_FORMAT, "%Y-%m-%d %H:%M:%S", '{')
    stdout_handler = StreamHandler(stdout)
    stdout_handler.setFormatter(formatter)
    return stdout_handler


def get_tabbed_formatter():
    formatter = Formatter(f'\t{LOG_FORMAT}', "%Y-%m-%d %H:%M:%S", '{')
    stdout_handler = StreamHandler(stdout)
    stdout_handler.setFormatter(formatter)
    return stdout_handler
