import xml.etree.ElementTree as ET
from datetime import date
from importlib import metadata
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, Mock, patch, sentinel
from xml.etree.ElementTree import Element

import pytest

from yarf.output.test_submission_schema import TestSubmissionSchema


class TestTestSubmissionSchema:
    """
    Tests for class TestSubmissionSchema.
    """

    @patch("yarf.output.test_submission_schema.ET")
    def test_get_output(self, mock_ET: MagicMock) -> None:
        """
        Test whether the function get the test plan from output.xml in the
        output directory and return the expected output in Test Submission
        Schema format.
        """
        converter = TestSubmissionSchema()
        converter.get_origin = Mock(return_value="origin")
        converter.get_session_data = Mock(return_value="session_data")
        converter.get_results = Mock(return_value="results")
        expected_output = {
            "version": 1,
            "origin": "origin",
            "session_data": "session_data",
            "results": "results",
        }

        output = converter.get_output(Path(str(sentinel.outdir)))

        mock_ET.parse.assert_called_once_with(
            Path(str(sentinel.outdir)) / "output.xml"
        )
        mock_ET.parse.return_value.getroot.assert_called_once()
        converter.get_origin.assert_called_once()
        converter.get_session_data.assert_called_once()
        converter.get_results.assert_called_once()
        assert output == expected_output

    def test_get_origin_has_snap(self) -> None:
        """
        Test whether the function get_origin returns the expected output when a
        snap is present.
        """
        converter = TestSubmissionSchema()
        converter.get_yarf_snap_info = Mock(
            return_value={
                "channel": "latest/beta",
                "version": "1.0.0",
                "revision": "124",
                "date": "2024-12-03",
                "name": "yarf",
            }
        )
        expected_output = {
            "name": "YARF",
            "version": "1.0.0",
            "packaging": {
                "type": "snap",
                "name": "yarf",
                "version": "1.0.0",
                "revision": "124",
                "date": "2024-12-03",
            },
        }

        output = converter.get_origin()
        converter.get_yarf_snap_info.assert_called_once()
        assert output == expected_output

    def test_get_origin_has_no_snap(self) -> None:
        """
        Test whether the function get_origin returns the expected output when a
        snap is not present.
        """
        converter = TestSubmissionSchema()
        converter.get_yarf_snap_info = Mock(return_value=None)
        expected_output = {
            "name": "YARF",
            "version": metadata.version("yarf"),
            "packaging": {
                "type": "source",
                "name": "yarf",
                "version": metadata.version("yarf"),
                "revision": None,
                "date": str(date.today()),
            },
        }

        output = converter.get_origin()
        converter.get_yarf_snap_info.assert_called_once()
        assert output == expected_output

    @patch("yarf.output.test_submission_schema.ET")
    def test_get_session_data(self, mock_ET: MagicMock) -> None:
        """
        Test whether the function get_session_data returns the expected output.
        """
        converter = TestSubmissionSchema()
        converter.test_plan = mock_ET

        attributes = ["title", "description", "test_plan_id", "execution_id"]
        elements = [None] * len(attributes)
        expected_output = {}
        for idx, meta in enumerate(attributes):
            elements[idx] = Element("meta", {"name": meta})
            elements[idx].text = str(getattr(sentinel, meta))
            expected_output[meta] = str(getattr(sentinel, meta))

        converter.test_plan.iter = Mock(return_value=elements)

        output = converter.get_session_data()
        converter.test_plan.iter.assert_called_once_with("meta")
        assert output == expected_output

    @patch("yarf.output.test_submission_schema.ET")
    def test_get_results(self, mock_ET: MagicMock) -> None:
        """
        Test whether the function get_results returns the results from the
        ElementTree.
        """
        suite = Element("suite", {"name": str(sentinel.suite_name)})
        test = Element("test", {"name": str(sentinel.test_name)})
        suite.append(test)

        expected_result = {
            str(sentinel.result_content): str(sentinel.result_content_value)
        }

        converter = TestSubmissionSchema()
        converter.test_plan = mock_ET
        converter.test_plan.iter = Mock(return_value=[suite])
        converter.get_tests_results_from_suite = Mock(
            return_value=[expected_result]
        )

        output = converter.get_results()
        converter.test_plan.iter.assert_called_once_with("suite")
        converter.get_tests_results_from_suite.assert_called_once_with(
            suite, []
        )
        assert output == [expected_result]

    @patch("yarf.output.test_submission_schema.ET")
    def test_get_results_no_tests(self, mock_ET: MagicMock) -> None:
        """
        Test whether the function get_results will skip suites with no tests.
        """
        suite = Element("suite", {"name": str(sentinel.suite_name)})

        converter = TestSubmissionSchema()
        converter.test_plan = mock_ET
        converter.test_plan.iter = Mock(return_value=[suite])
        converter.get_tests_results_from_suite = Mock()

        output = converter.get_results()
        converter.test_plan.iter.assert_called_once_with("suite")
        converter.get_tests_results_from_suite.assert_not_called()
        assert output == []

    def test_get_tests_results_from_suite(self) -> None:
        """
        Test whether the function get_tests_results_from_suite returns expected
        list of test results with expected fields.
        """
        xml_string = dedent(
            """
            <suite id="s1-s1" name="TestA" source="/tmp/tmpv7ethbc6/test.robot">
                <test id="s1-s1-t1" name="TaskA" line="7">
                    <kw name="KeywordA" library="LibA" sourcename="TemplateA">
                        <arg>/tmp/tmpv7ethbc6/testA.png</arg>
                        <doc>This is task A.</doc>
                        <msg timestamp="20241205 20:58:33.537" level="PASS"></msg>
                        <status status="PASS" starttime="20241205 20:58:33.524" endtime="20241205 20:58:33.539"/>
                    </kw>
                    <tag>yarf:category_id: com.canonical.category::categoryA</tag>
                    <tag>yarf:certification_status: non-blocker</tag>
                    <tag>yarf:namespace: com.canonical.yarf</tag>
                    <tag>yarf:type: typeA</tag>
                    <status status="PASS" starttime="20241205 20:58:33.523" endtime="20241205 20:58:33.540">
                    </status>
                </test>
                <test id="s1-s1-t2" name="TaskB" line="12">
                    <kw name="KeywordB" library="LibB">
                        <arg>/tmp/tmpv7ethbc6/testB.png</arg>
                        <doc>This is task B.</doc>
                        <msg timestamp="20241205 20:58:33.537" level="FAIL">
                            Full Error Message
                        </msg>
                        <status status="FAIL" starttime="20241205 20:59:33.524" endtime="20241205 20:59:33.539"/>
                    </kw>
                    <tag>yarf:category_id: com.canonical.category::categoryB</tag>
                    <tag>yarf:certification_status: non-blocker</tag>
                    <tag>yarf:namespace: com.canonical.yarf</tag>
                    <tag>yarf:type: typeB</tag>
                    <status status="FAIL" starttime="20241205 20:59:33.523" endtime="20241205 20:59:33.540">
                        Full Error Message
                    </status>
                </test>
            </suite>
            """
        )

        expected_result = [
            {
                "id": "com.canonical.yarf::TestA/TaskA",
                "test_description": "",
                "certification_status": "non-blocker",
                "category_id": "com.canonical.category::categoryA",
                "outcome": "PASS",
                "comments": "",
                "io_log": "io_logA",
                "duration": "0:00:00.017000",
                "type": "typeA",
                "template_id": "TemplateA",
            },
            {
                "id": "com.canonical.yarf::TestA/TaskB",
                "test_description": "",
                "certification_status": "non-blocker",
                "category_id": "com.canonical.category::categoryB",
                "outcome": "FAIL",
                "comments": "",
                "io_log": "io_logB",
                "duration": "0:00:00.017000",
                "type": "typeB",
                "template_id": None,
            },
        ]

        converter = TestSubmissionSchema()
        converter.get_io_log_and_templates = Mock(
            side_effect=[
                ("io_logA", ["TemplateA"]),
                ("io_logB", []),
            ]
        )
        result = converter.get_tests_results_from_suite(
            ET.fromstring(xml_string), []
        )
        assert result == expected_result

    @pytest.mark.parametrize(
        "mock_node_string,mock_key_chain,mock_iter_count,mock_templates,expected_curr,expected_templates,expected_keyword_chain",
        [
            # Case keyword with sourcename (template name)
            (
                dedent(
                    """
                    <kw name="KeywordA" library="LibA" sourcename="TemplateKeywordA"></kw>
                    """
                ),
                "",
                0,
                set(),
                ["Keyword: KeywordA\n", "Template: TemplateKeywordA\n"],
                {"TemplateKeywordA"},
                "KeywordA",
            ),
            # Case keyword with sourcename and has a preceeding keyword
            (
                dedent(
                    """
                    <kw name="KeywordB" library="LibB"></kw>
                    """
                ),
                "PrevKeyword",
                0,
                set(),
                [
                    "Keyword: PrevKeyword -> KeywordB\n",
                ],
                set(),
                "PrevKeyword -> KeywordB",
            ),
            # Case keyword with sourcename and is in iteration 1
            (
                dedent(
                    """
                    <kw name="KeywordC" library="LibC"></kw>
                    """
                ),
                "",
                1,
                set(),
                [
                    ">> Iteration 1:\n",
                    "Keyword: KeywordC\n",
                ],
                set(),
                "KeywordC",
            ),
            # Case keyword without sourcename
            (
                dedent(
                    """
                    <kw name="KeywordD" library="LibD"></kw>
                    """
                ),
                "",
                0,
                set(),
                ["Keyword: KeywordD\n"],
                set(),
                "KeywordD",
            ),
            # Case message with text
            (
                dedent(
                    """
                    <msg timestamp="20241205 20:58:33.537" level="FAIL">
                        ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5900)
                    </msg>
                    """
                ),
                "",
                0,
                set(),
                [
                    "[20241205 20:58:33.537 - FAIL] ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5900)\n"
                ],
                set(),
                "",
            ),
            # Case message without text
            (
                dedent(
                    """
                    <msg timestamp="20241205 20:58:33.537" level="PASS"></msg>
                    """
                ),
                "",
                0,
                set(),
                ["[20241205 20:58:33.537 - PASS] \n"],
                set(),
                "",
            ),
            # Case branch type IF
            (
                dedent(
                    """
                    <branch type="IF" condition="${{isinstance($destination, str)}}"></branch>
                    """
                ),
                "",
                0,
                set(),
                ["IF: ${{isinstance($destination, str)}}\n"],
                set(),
                "",
            ),
            # Case branch type ELSE
            (
                dedent(
                    """
                    <branch type="ELSE"></branch>
                    """
                ),
                "",
                0,
                set(),
                ["ELSE: \n"],
                set(),
                "",
            ),
        ],
    )
    def test_get_node_info(
        self,
        mock_node_string: str,
        mock_key_chain: str,
        mock_iter_count: int,
        mock_templates: set[str],
        expected_curr: list[str],
        expected_templates: set[str],
        expected_keyword_chain: str,
    ) -> None:
        """
        Test whether the function get_node_info returns the expected output.
        """
        converter = TestSubmissionSchema()
        curr, templates, keyword_chain = converter.get_node_info(
            ET.fromstring(mock_node_string),
            mock_key_chain,
            mock_iter_count,
            mock_templates,
        )
        assert curr == expected_curr
        assert templates == expected_templates
        assert keyword_chain == expected_keyword_chain

    def test_io_log_and_templates(self) -> None:
        pass
