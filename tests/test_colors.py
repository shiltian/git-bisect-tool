"""Tests for color handling."""

import sys
import unittest
from unittest.mock import patch

from git_bisect_tool.colors import Colors


class TestColors(unittest.TestCase):
    """Tests for Colors class."""

    def test_color_codes_defined(self):
        """All expected color codes are defined."""
        # These should be non-empty when TTY
        attrs = ['RESET', 'BOLD', 'DIM', 'RED', 'GREEN', 'YELLOW', 'BLUE', 'MAGENTA', 'CYAN', 'WHITE']
        for attr in attrs:
            self.assertTrue(hasattr(Colors, attr))

    def test_disable_clears_colors(self):
        """disable() sets all color codes to empty strings."""
        # Save original values
        original_red = Colors.RED
        original_bold = Colors.BOLD

        Colors.disable()

        self.assertEqual(Colors.RED, '')
        self.assertEqual(Colors.BOLD, '')
        self.assertEqual(Colors.RESET, '')

        # Restore for other tests (re-import would be cleaner but this works)
        Colors.RED = original_red
        Colors.BOLD = original_bold
        Colors.RESET = "\033[0m"

    @patch.object(sys.stdout, 'isatty', return_value=False)
    def test_init_disables_for_non_tty(self, mock_isatty):
        """init() disables colors when stdout is not a TTY."""
        # Save original
        original_red = Colors.RED

        Colors.init()

        self.assertEqual(Colors.RED, '')

        # Restore
        Colors.RED = original_red


if __name__ == '__main__':
    unittest.main()

