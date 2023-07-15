import unittest

class SampleTest(unittest.TestCase):
    def setUp(self):
        # Set up any resources or actions needed for the tests
        pass

    def test_addition(self):
        result = 2 + 2
        self.assertEqual(result, 4)

    def test_subtraction(self):
        result = 5 - 3
        self.assertNotEqual(result, 10)
