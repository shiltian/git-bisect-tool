"""ANSI color codes for terminal output."""

import sys


class Colors:
    """ANSI color codes for terminal output.

    Call ``Colors.init()`` once at startup to auto-detect TTY capability.
    Colors are enabled by default; ``init()`` disables them when stdout
    is not a terminal.
    """

    _COLOR_ATTRS = (
        "RESET",
        "BOLD",
        "DIM",
        "RED",
        "GREEN",
        "YELLOW",
        "BLUE",
        "MAGENTA",
        "CYAN",
        "WHITE",
        "BG_RED",
        "BG_GREEN",
        "BG_YELLOW",
        "BG_BLUE",
    )

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @classmethod
    def disable(cls):
        """Disable colors (set all codes to empty strings)."""
        for attr in cls._COLOR_ATTRS:
            setattr(cls, attr, "")

    @classmethod
    def init(cls):
        """Initialize colors based on terminal capabilities.

        Disables colors when stdout is not a TTY.  Call this once from
        the CLI entry point rather than at import time.
        """
        if not sys.stdout.isatty():
            cls.disable()
