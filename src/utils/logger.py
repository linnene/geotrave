"""
Module: src.utils.logger
Responsibility: Configures and exports a unified global logger instance for the entire project.
Parent Module: src.utils
Dependencies: colorlog, logging, sys, src.utils.config

Provides color-coded console logging via colorlog, with env-var toggles for
plain-text mode (CI-friendly) and optional file output.
"""

import logging
import sys

import colorlog

from src.utils.config import LOG_FILE, LOG_LEVEL, LOG_NO_COLOR

_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red,bg_white",
}

_CONSOLE_FMT_COLOR = (
    "%(asctime)s %(log_color)s[%(levelname)-7s]%(reset)s "
    "%(cyan)s%(name)s%(reset)s - %(message)s"
)

_CONSOLE_FMT_PLAIN = (
    "%(asctime)s [%(levelname)-7s] %(name)s - %(message)s"
)

_FILE_FMT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    if not logger.handlers:
        # --- Console handler (color or plain) ---
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        if LOG_NO_COLOR:
            console_fmt = logging.Formatter(
                fmt=_CONSOLE_FMT_PLAIN, datefmt="%Y-%m-%d %H:%M:%S"
            )
        else:
            console_fmt = colorlog.ColoredFormatter(
                fmt=_CONSOLE_FMT_COLOR,
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors=_COLORS,
                secondary_log_colors={
                    "name": {"DEBUG": "blue", "INFO": "cyan", "WARNING": "yellow",
                             "ERROR": "red", "CRITICAL": "red"},
                },
            )
        console_handler.setFormatter(console_fmt)
        logger.addHandler(console_handler)

        # --- File handler (optional, plain text) ---
        if LOG_FILE:
            file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(logging.Formatter(
                fmt=_FILE_FMT, datefmt="%Y-%m-%d %H:%M:%S"
            ))
            logger.addHandler(file_handler)

    else:
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            handler.setLevel(numeric_level)

    return logger


logger = get_logger("GeoTrave")
