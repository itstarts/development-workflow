import unittest

from src.account_utils import retry_delay


class RetryDelayTests(unittest.TestCase):
    def test_uses_exponential_backoff_below_cap(self):
        self.assertEqual(8, retry_delay(3))

    def test_caps_delay_at_sixty_seconds(self):
        self.assertEqual(60, retry_delay(10))


if __name__ == "__main__":
    unittest.main()
