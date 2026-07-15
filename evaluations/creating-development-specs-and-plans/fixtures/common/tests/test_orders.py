import unittest

from src.orders import create_order


class OrderTests(unittest.TestCase):
    def test_new_order_is_created(self):
        self.assertEqual("created", create_order("o-1", "user-1")["status"])


if __name__ == "__main__":
    unittest.main()
