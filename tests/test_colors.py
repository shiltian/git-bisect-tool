"""Tests for color handling."""

import sys
import unittest
from unittest.mock import patch

from git_bisect_tool.colors import Colors


class TestColors(unittest.TestCase):
    """Tests for Colors class."""

    def setUp(self):
        """Save original color values before each test."""
        self._saved = {attr: getattr(Colors, attr) for attr in Colors._COLOR_ATTRS}

    def tearDown(self):
        """Restore original color values after each test."""
        for attr, value in self._saved.items():
            setattr(Colors, attr, value)

    def test_color_codes_defined(self):
        """All expected color codes are defined as non-empty strings."""
        for attr in Colors._COLOR_ATTRS:
            self.assertTrue(hasattr(Colors, attr))
            self.assertIsInstance(getattr(Colors, attr), str)

    def test_disable_clears_colors(self):
        """disable() sets all color codes to empty strings."""
        Colors.disable()

        for attr in Colors._COLOR_ATTRS:
            self.assertEqual(getattr(Colors, attr), "", f"{attr} should be empty")

    @patch.object(sys.stdout, "isatty", return_value=False)
    def test_init_disables_for_non_tty(self, mock_isatty):
        """init() disables colors when stdout is not a TTY."""
        Colors.init()

        self.assertEqual(Colors.RED, "")
        self.assertEqual(Colors.BOLD, "")
        self.assertEqual(Colors.RESET, "")

    @patch.object(sys.stdout, "isatty", return_value=True)
    def test_init_preserves_for_tty(self, mock_isatty):
        """init() keeps colors when stdout is a TTY."""
        Colors.init()

        self.assertNotEqual(Colors.RED, "")
        self.assertNotEqual(Colors.BOLD, "")
        self.assertNotEqual(Colors.RESET, "")


if __name__ == "__main__":
    unittest.main()
