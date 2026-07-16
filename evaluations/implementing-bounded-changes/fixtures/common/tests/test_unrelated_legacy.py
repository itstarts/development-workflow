import unittest

from src.account_utils import legacy_banner


class LegacyBannerTests(unittest.TestCase):
    def test_preserves_legacy_banner(self):
        self.assertEqual("old banner", legacy_banner())


if __name__ == "__main__":
    unittest.main()
