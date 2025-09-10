import xml.etree.ElementTree as ET
from importlib import metadata
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest.mock import ANY, MagicMock, Mock, patch, sentinel
from xml.etree.ElementTree import Element

import pytest
from robot.api import TestSuite

from yarf.output.test_submission_schema import TestSubmissionSchema


class TestTestSubmissionSchema:
    """
    Tests for class TestSubmissionSchema.
    """

    @pytest.mark.parametrize(
        "mock_init_suite,mock_test_suite,expected_namespace",
        [
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            title               Test Title
                    Metadata            test_plan_id        com.canonical.test::plan1
                    Metadata            execution_id        com.canonical.execution::exe1
                    Metadata            description         This is a test description
                    """
                ),
                dedent(
                    """
                    *** Settings ***
                    Resource        kvm.resource
                    Library         Hid.py    AS    PlatformHid


                    *** Test Cases ***
                    Task1
                        [Tags]                  yarf:certification_status: non-blocker        yarf:category_id: com.canonical.category::categoryA
                        Match                   ${CURDIR}/test1.png

                    Task2
                        [Tags]                  yarf:certification_status: non-blocker        yarf:category_id: com.canonical.category::categoryB
                        Click LEFT Button on ${CURDIR}/test2.png

                    Task3
                        [Tags]                  yarf:certification_status: non-blocker        yarf:category_id: com.canonical.category::categoryC
                        PlatformHid.Type String     1234567890
                    """
                ),
                "com.canonical.yarf",
            ),
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            title               Test Title
                    Metadata            test_plan_id        com.canonical.test::plan1
                    Metadata            execution_id        com.canonical.execution::exe1
                    Metadata            description         This is a test description
                    Metadata            namespace           com.sample.space
                    """
                ),
                dedent(
                    """
                    *** Settings ***
                    Resource        kvm.resource
                    Library         Hid.py    AS    PlatformHid


                    *** Test Cases ***
                    Task1
                        [Tags]                  yarf:certification_status: non-blocker        yarf:category_id: com.canonical.category::categoryA
                        Match                   ${CURDIR}/test1.png

                    Task2
                        [Tags]                  yarf:certification_status: non-blocker        yarf:category_id: com.canonical.category::categoryB
                        Click LEFT Button on ${CURDIR}/test2.png

                    Task3
                        [Tags]                  yarf:certification_status: non-blocker        yarf:category_id: com.canonical.category::categoryC
                        PlatformHid.Type String     1234567890
                    """
                ),
                "com.sample.space",
            ),
        ],
    )
    def test_check_test_plan(
        self,
        mock_init_suite: str,
        mock_test_suite: str,
        expected_namespace: str,
    ) -> None:
        """
        Test whether the function check_test_plan passes a correct test plan
        and get the correct namespace.
        """
        test_plan = TestSuite.from_string(
            f"{mock_init_suite}\n{mock_test_suite}"
        )
        converter = TestSubmissionSchema()
        converter.check_test_plan(test_plan)
        # default value for namespace
        assert test_plan.metadata.get("namespace") == expected_namespace
        assert converter.yarf_namespace == expected_namespace

    @pytest.mark.parametrize(
        "mock_init,mock_suite",
        [
            # test_plan_id missing
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            title               Test Title
                    Metadata            description         This is a test description
                    Metadata            namespace           com.canonical.yarf
                    """
                ),
                dedent(
                    """
                    *** Settings ***
                    Resource        kvm.resource
                    Library         Hid.py    AS    PlatformHid


                    *** Test Cases ***
                    Task1
                        [Tags]                  yarf:certification_status: non-blocker        yarf:category_id: com.canonical.category::categoryA
                        Match                   ${CURDIR}/test1.png
                    """
                ),
            ),
            # Documentation too long
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            title               Test Title
                    Metadata            test_plan_id        com.canonical.test::plan1
                    Metadata            execution_id        com.canonical.execution::exe1
                    Metadata            description         This is a test description
                    Metadata            namespace           com.canonical.yarf
                    """
                ),
                dedent(
                    f"""
                    *** Settings ***
                    Resource        kvm.resource
                    Library         Hid.py    AS    PlatformHid


                    *** Test Cases ***
                    Task1
                        [Documentation]         {"T" * 100}
                        [Tags]                  yarf:certification_status: non-blocker        yarf:category_id: com.canonical.category::categoryA
                        Match                   test1.png
                    """
                ),
            ),
            # Undefined certification status
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            title               Test Title
                    Metadata            test_plan_id        com.canonical.test::plan1
                    Metadata            execution_id        com.canonical.execution::exe1
                    Metadata            description         This is a test description
                    Metadata            namespace           com.canonical.yarf
                    """
                ),
                dedent(
                    """
                    *** Settings ***
                    Resource        kvm.resource
                    Library         Hid.py    AS    PlatformHid


                    *** Test Cases ***
                    Task1
                        [Tags]                  yarf:certification_status: undefined        yarf:category_id: com.canonical.category::categoryA
                        Match                   test1.png
                    """
                ),
            ),
            # Invalid category ID
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            title               Test Title
                    Metadata            test_plan_id        com.canonical.test::plan1
                    Metadata            execution_id        com.canonical.execution::exe1
                    Metadata            description         This is a test description
                    Metadata            namespace           com.canonical.yarf
                    """
                ),
                dedent(
                    """
                    *** Settings ***
                    Resource        kvm.resource
                    Library         Hid.py    AS    PlatformHid


                    *** Test Cases ***
                    Task1
                        [Tags]                  yarf:certification_status: blocker        yarf:category_id: !@#$%^::categoryA
                        Match                   test1.png
                    """
                ),
            ),
            # Missing category ID
            (
                dedent(
                    """
                    *** Settings ***
                    Metadata            title               Test Title
                    Metadata            test_plan_id        com.canonical.test::plan1
                    Metadata            execution_id        com.canonical.execution::exe1
                    Metadata            description         This is a test description
                    Metadata            namespace           com.canonical.yarf
                    """
                ),
                dedent(
                    """
                    *** Settings ***
                    Resource        kvm.resource
                    Library         Hid.py    AS    PlatformHid


                    *** Test Cases ***
                    Task1
                        [Tags]                  yarf:certification_status: blocker
                        Match                   test1.png
                    """
                ),
            ),
        ],
    )
    def test_check_test_plan_missing_metadata(
        self,
        mock_init: str,
        mock_suite: str,
    ) -> None:
        """
        Test whether the function check_test_plan raises a ValueError when the
        relevant data does not fulfill the requirement.
        """
        test_plan = TestSuite.from_string(mock_init)
        test_suite = TestSuite.from_string(mock_suite)
        test_suite.name = "Test Suite"
        test_plan.suites = [test_suite]
        converter = TestSubmissionSchema()
        with pytest.raises(ValueError):
            converter.check_test_plan(test_plan)

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
            "category_map": ANY,
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
        assert type(output["category_map"]) is dict

    def test_get_origin_has_snap(self) -> None:
        """
        Test whether the function get_origin returns the expected output when a
        snap is present.
        """
        converter = TestSubmissionSchema()
        converter.get_yarf_snap_info = Mock(
            return_value={
                "version": "1.0.0",
                "revision": "124",
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
                "version": metadata.version("yarf"),
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

    @pytest.mark.parametrize(
        "xml_string,expected_result",
        [
            (
                dedent(
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
                            <tag>yarf:test_group_id: com.canonical.group::testGroupA</tag>
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
                            <status status="FAIL" starttime="20241205 20:59:33.523" endtime="20241205 20:59:33.540">
                                Full Error Message
                            </status>
                        </test>
                        <test id="s1-s1-t2" name="TaskC" line="12">
                            <kw name="KeywordC" library="LibC">
                                <arg>/tmp/tmpv7ethbc6/testC.png</arg>
                                <doc>This is task C.</doc>
                                <msg timestamp="20241205 21:00:33.537" level="NOT RUN">
                                </msg>
                                <status status="NOT RUN" starttime="20241205 21:00:33.524" endtime="20241205 21:00:33.539"/>
                            </kw>
                            <tag>yarf:category_id: com.canonical.category::categoryC</tag>
                            <tag>yarf:certification_status: non-blocker</tag>
                            <status status="NOT RUN" starttime="20241205 21:00:33.523" endtime="20241205 21:00:33.540">
                            </status>
                        </test>
                    </suite>
                    """
                ),
                [
                    {
                        "id": "com.canonical.yarf::TestA/TaskA",
                        "test_description": "",
                        "certification_status": "non-blocker",
                        "category_id": "com.canonical.category::categoryA",
                        "outcome": "passed",
                        "comments": "",
                        "io_log": "io_logA",
                        "duration": 0.01699995994567871,
                        "test_group_id": "com.canonical.group::testGroupA",
                    },
                    {
                        "id": "com.canonical.yarf::TestA/TaskB",
                        "test_description": "",
                        "certification_status": "non-blocker",
                        "category_id": "com.canonical.category::categoryB",
                        "outcome": "failed",
                        "comments": "",
                        "io_log": "io_logB",
                        "duration": 0.01699995994567871,
                    },
                    {
                        "id": "com.canonical.yarf::TestA/TaskC",
                        "test_description": "",
                        "certification_status": "non-blocker",
                        "category_id": "com.canonical.category::categoryC",
                        "outcome": "skipped",
                        "comments": "",
                        "io_log": "io_logC",
                        "duration": 0.01699995994567871,
                    },
                ],
            ),
            # Robot Framework v7
            (
                dedent(
                    """
                    <suite id="s1-s1" name="TestA" source="/tmp/tmpv7ethbc6/test.robot">
                        <test id="s1-s1-t1" name="TaskA" line="7">
                            <kw name="KeywordA" library="LibA" sourcename="TemplateA">
                                <arg>/tmp/tmpv7ethbc6/testA.png</arg>
                                <doc>This is task A.</doc>
                                <msg time="20241205T20:58:33.537" level="PASS"></msg>
                                <status status="PASS" start="20241205T20:58:33.524126" elapsed="0.015"/>
                            </kw>
                            <tag>yarf:category_id: com.canonical.category::categoryA</tag>
                            <tag>yarf:certification_status: non-blocker</tag>
                            <tag>yarf:test_group_id: com.canonical.group::testGroupA</tag>
                            <status status="PASS" start="20241205T20:58:33.523157" elapsed="0.02">
                            </status>
                        </test>
                        <test id="s1-s1-t2" name="TaskB" line="12">
                            <kw name="KeywordB" library="LibB">
                                <arg>/tmp/tmpv7ethbc6/testB.png</arg>
                                <doc>This is task B.</doc>
                                <msg time="20241205T20:58:33.537" level="FAIL">
                                    Full Error Message
                                </msg>
                                <status status="FAIL" start="20241205T20:59:33.524236" elapsed="0.015"/>
                            </kw>
                            <tag>yarf:category_id: com.canonical.category::categoryB</tag>
                            <tag>yarf:certification_status: non-blocker</tag>
                            <status status="FAIL" start="20241205T20:59:33.523123" elapsed="0.015">
                                Full Error Message
                            </status>
                        </test>
                        <test id="s1-s1-t2" name="TaskC" line="12">
                            <kw name="KeywordC" library="LibC">
                                <arg>/tmp/tmpv7ethbc6/testC.png</arg>
                                <doc>This is task C.</doc>
                                <msg time="20241205T21:00:33.537" level="NOT RUN">
                                </msg>
                                <status status="NOT RUN" start="20241205T21:00:33.524" elapsed="0.017"/>
                            </kw>
                            <tag>yarf:category_id: com.canonical.category::categoryC</tag>
                            <tag>yarf:certification_status: non-blocker</tag>
                            <status status="NOT RUN" starttime="20241205T21:00:33.523789" elapsed="0.017">
                            </status>
                        </test>
                    </suite>
                    """
                ),
                [
                    {
                        "id": "com.canonical.yarf::TestA/TaskA",
                        "test_description": "",
                        "certification_status": "non-blocker",
                        "category_id": "com.canonical.category::categoryA",
                        "outcome": "passed",
                        "comments": "",
                        "io_log": "io_logA",
                        "duration": 0.02,
                        "test_group_id": "com.canonical.group::testGroupA",
                    },
                    {
                        "id": "com.canonical.yarf::TestA/TaskB",
                        "test_description": "",
                        "certification_status": "non-blocker",
                        "category_id": "com.canonical.category::categoryB",
                        "outcome": "failed",
                        "comments": "",
                        "io_log": "io_logB",
                        "duration": 0.015,
                    },
                    {
                        "id": "com.canonical.yarf::TestA/TaskC",
                        "test_description": "",
                        "certification_status": "non-blocker",
                        "category_id": "com.canonical.category::categoryC",
                        "outcome": "skipped",
                        "comments": "",
                        "io_log": "io_logC",
                        "duration": 0.017,
                    },
                ],
            ),
        ],
    )
    def test_get_tests_results_from_suite(
        self, xml_string: str, expected_result: list[dict[str, Any]]
    ) -> None:
        """
        Test whether the function get_tests_results_from_suite returns expected
        list of test results with expected fields.
        """
        converter = TestSubmissionSchema()
        converter.get_io_log = Mock(
            side_effect=[
                "io_logA",
                "io_logB",
                "io_logC",
            ]
        )
        result = converter.get_tests_results_from_suite(
            ET.fromstring(xml_string), []
        )
        assert result == expected_result

    @pytest.mark.parametrize(
        "mock_node_string,mock_key_chain,mock_iter_count,expected_curr,expected_keyword_chain",
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
                ["Keyword: KeywordA\n"],
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
                [
                    "Keyword: PrevKeyword -> KeywordB\n",
                ],
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
                [
                    ">> Iteration 1:\n",
                    "Keyword: KeywordC\n",
                ],
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
                ["Keyword: KeywordD\n"],
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
                [
                    "[20241205 20:58:33.537 - FAIL] ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5900)\n"
                ],
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
                ["[20241205 20:58:33.537 - PASS] \n"],
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
                ["IF: ${{isinstance($destination, str)}}\n"],
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
                ["ELSE: \n"],
                "",
            ),
        ],
    )
    def test_get_node_info(
        self,
        mock_node_string: str,
        mock_key_chain: str,
        mock_iter_count: int,
        expected_curr: list[str],
        expected_keyword_chain: str,
    ) -> None:
        """
        Test whether the function get_node_info returns the expected output.
        """
        converter = TestSubmissionSchema()
        curr, keyword_chain = converter.get_node_info(
            ET.fromstring(mock_node_string),
            mock_key_chain,
            mock_iter_count,
        )
        assert curr == expected_curr
        assert keyword_chain == expected_keyword_chain

    @pytest.mark.parametrize(
        "mock_node,expected_io_log",
        [
            # IF clause
            (
                dedent(
                    """
                    <if>
                        <branch type="IF" condition="${{isinstance($destination, str)}}">
                            <kw name="TaskA" library="LibA">
                                <var>varA</var>
                                <arg>argA</arg>
                                <doc>DocA.</doc>
                                <msg timestamp="20241205 20:58:33.558" level="FAIL">
                                    Fail message A
                                </msg>
                                <status status="FAIL" starttime="20241205 20:58:33.556" endtime="20241205 20:58:33.558"/>
                            </kw>
                            <kw name="TaskB" library="LibA" sourcename="TemplateB">
                                <var>varB</var>
                                <doc>DocB</doc>
                                <status status="NOT RUN" starttime="20241205 20:58:33.559" endtime="20241205 20:58:33.559"/>
                            </kw>
                            <status status="FAIL" starttime="20241205 20:58:33.548" endtime="20241205 20:58:33.559"/>
                        </branch>
                            <branch type="ELSE">
                            <kw name="TaskC" library="LibC">
                                <var>varC</var>
                                <arg>argC</arg>
                                <doc>DocC</doc>
                                <status status="NOT RUN" starttime="20241205 20:58:33.560" endtime="20241205 20:58:33.560"/>
                            </kw>
                            <status status="NOT RUN" starttime="20241205 20:58:33.559" endtime="20241205 20:58:33.560"/>
                            </branch>
                        <status status="FAIL" starttime="20241205 20:58:33.548" endtime="20241205 20:58:33.560"/>
                    </if>
                    """
                ),
                [
                    ">> IF STATEMENT >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n",
                    "IF: ${{isinstance($destination, str)}}\n",
                    "================================================================================\n",
                    "Keyword: TaskA\n",
                    "[20241205 20:58:33.558 - FAIL] Fail message A\n",
                    "\n",
                    "================================================================================\n",
                    "Keyword: TaskB\n",
                    "\n",
                    "ELSE: \n",
                    "================================================================================\n",
                    "Keyword: TaskC\n",
                    "\n",
                    "<< END IF <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n",
                ],
            ),
            # For loop
            (
                dedent(
                    """
                    <for flavor="IN">
                        <var>${item}</var>
                         <value>@{list}</value>
                        <iter>
                            <var name="${item}">item1</var>
                            <kw name="TaskA" library="LibA">
                                <arg>${item}</arg>
                                <doc>DocA</doc>
                                <status status="PASS" starttime="20241128 14:04:08.024" endtime="20241128 14:04:08.154"/>
                            </kw>
                            <status status="PASS" starttime="20241128 14:04:08.024" endtime="20241128 14:04:08.154"/>
                        </iter>
                        <iter>
                            <var name="${item}">item2</var>
                            <kw name="TaskA" library="LibA">
                                <arg>${item}</arg>
                                <doc>DocA</doc>
                                <status status="PASS" starttime="20241128 14:04:08.154" endtime="20241128 14:04:08.158"/>
                            </kw>
                            <status status="PASS" starttime="20241128 14:04:08.154" endtime="20241128 14:04:08.158"/>
                        </iter>
                        <status status="PASS" starttime="20241128 14:04:08.024" endtime="20241128 14:04:08.158"/>
                    </for>
                    """
                ),
                [
                    ">> FOR LOOP >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n",
                    "================================================================================\n",
                    ">> Iteration 1:\n",
                    "Keyword: TaskA\n",
                    "\n",
                    "================================================================================\n",
                    ">> Iteration 2:\n",
                    "Keyword: TaskA\n",
                    "\n",
                    "<< END FOR <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n",
                ],
            ),
            # Recursive keywords
            (
                dedent(
                    """
                    <kw name="KeywordA" library="LibA" sourcename="TemplateA">
                        <doc>DocA.</doc>
                        <kw name="KeywordB" library="LibB" sourcename="TemplateB">
                            <doc>DocB.</doc>
                            <kw name="KeywordC" library="LibC">
                                <var>varC</var>
                                <arg>argC</arg>
                                <doc>DocC.</doc>
                                <msg timestamp="20241128 14:05:15.543" level="INFO">
                                    Finished in in 0.07 seconds
                                </msg>
                                <msg timestamp="20241128 14:05:15.544" level="INFO">
                                    ${result} = ["A", "B", "C"]
                                </msg>
                                <status status="PASS" starttime="20241128 14:05:15.451" endtime="20241128 14:05:15.544"/>
                            </kw>
                            <status status="PASS" starttime="20241128 14:05:15.451" endtime="20241128 14:05:15.544"/>
                        </kw>
                        <status status="PASS" starttime="20241128 14:05:15.451" endtime="20241128 14:05:15.544"/>
                    </kw>
                    """
                ),
                [
                    "================================================================================\n",
                    "Keyword: KeywordA\n",
                    "================================================================================\n",
                    "Keyword: KeywordA -> KeywordB\n",
                    "================================================================================\n",
                    "Keyword: KeywordA -> KeywordB -> KeywordC\n",
                    "[20241128 14:05:15.543 - INFO] Finished in in 0.07 seconds\n",
                    '[20241128 14:05:15.544 - INFO] ${result} = ["A", "B", "C"]\n',
                    "\n",
                    "\n",
                    "\n",
                ],
            ),
            # Robot Framework v7
            (
                dedent(
                    """
                    <kw name="KeywordA" library="LibA" sourcename="TemplateA">
                        <doc>DocA.</doc>
                        <kw name="KeywordB" library="LibB" sourcename="TemplateB">
                            <doc>DocB.</doc>
                            <kw name="KeywordC" library="LibC">
                                <var>varC</var>
                                <arg>argC</arg>
                                <doc>DocC.</doc>
                                <msg time="20241128T14:05:15.543159" level="INFO">
                                    Finished in in 0.07 seconds
                                </msg>
                                <msg time="20241128T14:05:15.544138" level="INFO">
                                    ${result} = ["A", "B", "C"]
                                </msg>
                                <status status="PASS" start="20241128 14:05:15.451" elapsed="0.09"/>
                            </kw>
                            <status status="PASS" start="20241128 14:05:15.451" elapsed="0.09"/>
                        </kw>
                        <status status="PASS" start="20241128 14:05:15.451" elapsed="0.09"/>
                    </kw>
                    """
                ),
                [
                    "================================================================================\n",
                    "Keyword: KeywordA\n",
                    "================================================================================\n",
                    "Keyword: KeywordA -> KeywordB\n",
                    "================================================================================\n",
                    "Keyword: KeywordA -> KeywordB -> KeywordC\n",
                    "[20241128T14:05:15.543159 - INFO] Finished in in 0.07 seconds\n",
                    '[20241128T14:05:15.544138 - INFO] ${result} = ["A", "B", "C"]\n',
                    "\n",
                    "\n",
                    "\n",
                ],
            ),
        ],
    )
    def test_get_io_log(
        self,
        mock_node: str,
        expected_io_log: list[str],
    ) -> None:
        """
        Test whether the function get_io_log returns the expected io_log and
        template.
        """
        converter = TestSubmissionSchema()
        io_log = converter.get_io_log(
            ET.fromstring(mock_node),
            [],
            "",
            0,
        )
        assert io_log == expected_io_log
