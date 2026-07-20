import unittest

from src.orders import create_order, export_orders


class OrderTests(unittest.TestCase):
    def test_export_preserves_existing_orders(self):
        order = create_order("o-1", "user-1", "approved")
        self.assertEqual([order], export_orders([order]))


if __name__ == "__main__":
    unittest.main()
