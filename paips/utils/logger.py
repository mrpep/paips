import logging
import sys
from logging import FileHandler
FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")

def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler(log_file):
    file_handler = FileHandler(log_file, mode='w')
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name, log_file):
    logger_info = logging.getLogger(logger_name)
    #logger_debug = logger_info.getChild('debug')
    fh = get_file_handler(log_file)
    #logger_debug.setLevel(logging.DEBUG)
    # logger_debug.addHandler(get_console_handler())
    # logger_debug.addHandler(fh)
    logger_info.setLevel(logging.INFO)
    logger_info.addHandler(get_console_handler())
    logger_info.addHandler(fh)
    logger_info.propagate = False
    return logger_info
