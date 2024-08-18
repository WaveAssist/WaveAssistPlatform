import unittest

test_loader = unittest.TestLoader()
test_suite = test_loader.discover('Tests')


test_runner = unittest.TextTestRunner()
test_runner.run(test_suite)
