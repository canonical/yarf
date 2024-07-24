import unittest
from unittest.mock import patch
from yarf import main
import sys


class TestMain(unittest.TestCase):
    def test_main(self):
        with patch.object(sys, "argv", ["prog"]):
            main.main()
