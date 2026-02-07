"""Logging configuration for the git bisect tool."""

import copy
import logging
import sys

from .colors import Colors


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors based on log level.

    Creates a shallow copy of each log record before modifying it so
    that other handlers attached to the same logger are not affected.
    """

    LEVEL_COLORS = {
        logging.DEBUG: Colors.DIM,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BG_RED + Colors.WHITE,
    }

    def format(self, record: logging.LogRecord) -> str:
        record = copy.copy(record)
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        if record.levelno >= logging.WARNING:
            record.msg = f"{color}{record.msg}{Colors.RESET}"
        return super().format(record)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging with optional verbose mode.

    Args:
        verbose: If True, show DEBUG level messages with level prefix.
                 If False, show INFO+ messages without prefix.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("git-bisect-tool")

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    # Use stdout instead of stderr for consistent output ordering with print()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    fmt = "%(levelname)s %(message)s" if verbose else "%(message)s"
    handler.setFormatter(ColoredFormatter(fmt))

    logger.addHandler(handler)
    return logger
