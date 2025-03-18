from collections import OrderedDict
from textwrap import dedent
from unittest.mock import call, patch

import pytest
from robot.api import TestSuite

from yarf.rf_libraries.libraries.metadata_listener import MetadataListener


class TestMetadataListener:
    @pytest.mark.parametrize(
        "mock_init_suite,expected_metadata",
        [
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            yarf:metadata_A              valueA
                    Metadata            yarf:metadata_B              valueB
                    """
                ),
                OrderedDict(
                    [
                        ("${metadata_A}", "valueA"),
                        ("${metadata_B}", "valueB"),
                    ]
                ),
            ),
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            yarf:displays      HDMI_1:1920x1080
                    Metadata            non_yarf:metadata_A           valueA
                    Metadata            other_metadata                valueB
                    """
                ),
                OrderedDict(
                    [
                        ("${displays}", "HDMI_1:1920x1080"),
                    ]
                ),
            ),
        ],
    )
    def test_start_suite(
        self, mock_init_suite: str, expected_metadata: str
    ) -> None:
        """
        Test whether the start_suite hook is called and the metadata is
        correctly registered to the test suite.
        """
        suite = TestSuite.from_string(mock_init_suite)
        with patch(
            "yarf.rf_libraries.libraries.metadata_listener.BuiltIn.set_global_variable"
        ) as mock_set_global_variable:
            suite.run(listener=MetadataListener())
            calls = []
            for key, value in expected_metadata.items():
                calls.append(call(key, value))

            mock_set_global_variable.assert_has_calls(calls)
