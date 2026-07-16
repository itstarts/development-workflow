import unittest

from src.account_utils import format_display_name


class FormatDisplayNameTests(unittest.TestCase):
    def test_joins_non_empty_names(self):
        self.assertEqual("Ada Lovelace", format_display_name("Ada", "Lovelace"))

    def test_omits_separator_for_empty_last_name(self):
        self.assertEqual("Ada", format_display_name("Ada", ""))


if __name__ == "__main__":
    unittest.main()
