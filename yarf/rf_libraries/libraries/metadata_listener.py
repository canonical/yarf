"""
This module provides methods to process test suite metadata.
"""

from typing import Any

from robot.api import TestSuite
from robot.libraries.BuiltIn import BuiltIn

from yarf import LABEL_PREFIX, LABEL_PREFIX_LENGTH


class MetadataListener:
    """
    Listener for test suite metadata.

    Attributes:
        ROBOT_LISTENER_API_VERSION: The Robot Framework Listener API version
    """

    ROBOT_LISTENER_API_VERSION = 3

    def start_suite(self, test_suite: TestSuite, attrs: Any) -> None:
        """
        Register metadata from the test suite.

        Arguments:
            test_suite: test suite object
            attrs: attributes of the test suite
        """
        for key, value in test_suite.metadata.items():
            if not key.startswith(LABEL_PREFIX):
                continue
            BuiltIn().set_global_variable(
                f"${{{key[LABEL_PREFIX_LENGTH:]}}}", value
            )
