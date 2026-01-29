import os
import re
import xml.etree.ElementTree as ET
from importlib import metadata
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element

from dateutil.parser import parse
from robot.api import TestSuite

from yarf import LABEL_PREFIX
from yarf.output import OutputConverterBase

try:
    CONSOLE_COLUMN_SIZE, _ = os.get_terminal_size()
except OSError:
    # Default to some reasonable dimensions
    CONSOLE_COLUMN_SIZE = 80


class TestSubmissionSchema(OutputConverterBase):
    """
    Output converter for Test Submission Schema format.
    https://github.com/canonical/test-submission-schema

    Attributes:
        yarf_namespace: The namespace for YARF, defaults to "com.canonical.yarf"
        submission_schema_version: The Test Submission Schema submission schema version
        category_map: A dictionary mapping category_id to category name
    """

    yarf_namespace = "com.canonical.yarf"
    submission_schema_version = 1
    category_map: dict[str, str] = {
        # Add category_id: category name pair here
    }

    _TEST_PLAN_ID_REGEX = re.compile(
        r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+::[a-zA-Z0-9_]+$"
    )
    _CATEGORY_ID_REGEX = re.compile(
        r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+::[A-Za-z0-9_\-]+$"
    )
    _VALID_CERT_STATUSES = frozenset(["blocker", "non-blocker"])
    _REQUIRED_TAGS = frozenset(["certification_status", "category_id"])

    def _check_metadata(self, test_plan: TestSuite) -> set[str]:
        """
        Check for required metadata in the test plan.

        Arguments:
            test_plan: an initialized executable TestSuite

        Returns:
            Set of missing metadata field names
        """
        missing_metadata = {"title", "test_plan_id"}
        for data in test_plan.metadata:
            data_lower = data.lower()
            if data_lower == "title":
                missing_metadata.discard("title")
            elif (
                data_lower == "test_plan_id"
                and self._TEST_PLAN_ID_REGEX.fullmatch(
                    test_plan.metadata[data]
                )
            ):
                missing_metadata.discard("test_plan_id")

        if test_plan.metadata.get("namespace") is None:
            test_plan.metadata["namespace"] = self.yarf_namespace
        else:
            self.yarf_namespace = test_plan.metadata["namespace"]

        return missing_metadata

    def _validate_tag(
        self, tag_name: str, tag_value: str, test_id: str
    ) -> str | None:
        """
        Validate a single tag value.

        Arguments:
            tag_name: name of the tag to validate
            tag_value: value of the tag
            test_id: identifier of the test for error messages

        Returns:
            Error message string if validation fails, None otherwise
        """
        if tag_name == "certification_status":
            if tag_value.strip() not in self._VALID_CERT_STATUSES:
                return f"[{test_id}] Invalid certification_status expression: {tag_value}"
        elif tag_name == "category_id":
            if not self._CATEGORY_ID_REGEX.fullmatch(tag_value.strip()):
                return (
                    f"[{test_id}] Invalid category_id expression: {tag_value}"
                )
        return None

    def _check_test_tags(self, test: Any, test_id: str) -> list[str]:
        """
        Check that a test has all required tags with valid values.

        Arguments:
            test: the test object to check
            test_id: identifier of the test for error messages

        Returns:
            List of error messages for any validation failures
        """
        errors = []
        if len(test.doc) > 80:
            errors.append(
                f"[{test_id}] Test case description is too long: {test.doc}"
            )

        found_tags: set[str] = set()
        for tag in test.tags:
            if not tag.startswith(LABEL_PREFIX):
                continue
            _, tag_name, tag_value = tag.split(":", 2)
            found_tags.add(tag_name)
            if error := self._validate_tag(tag_name, tag_value, test_id):
                errors.append(error)

        missing_tags = self._REQUIRED_TAGS - found_tags
        if missing_tags:
            errors.append(
                f"[{test_id}] Missing tags: {', '.join(missing_tags)}"
            )
        return errors

    def check_test_plan(self, test_plan: TestSuite) -> None:
        """
        Check the test suite to see if it has all the required information for
        the TestSubmissionSchema output format.

        Arguments:
            test_plan: an initialized executable TestSuite

        Raises:
            ValueError: when any metadata or tag is missing / in the wrong format
        """
        missing_metadata = self._check_metadata(test_plan)

        test_err_msg = []
        for s in test_plan.suites:
            for test in s.tests:
                test_id = f"{test.parent.name}/{test.name}"
                test_err_msg.extend(self._check_test_tags(test, test_id))

        err_parts = []
        if missing_metadata:
            err_parts.append(
                f"Missing/wrong pattern for required metadata: {', '.join(missing_metadata)}"
            )
        if test_err_msg:
            err_parts.append("\n".join(test_err_msg))

        if err_parts:
            raise ValueError("\n".join(err_parts))

    def get_output(self, outdir: Path) -> dict[str, Any]:
        """
        Convert the output to specified output format.

        Arguments:
            outdir: Path to the output directory

        Returns:
            Dictionary containing the converted output in Test Submission Schema format
        """
        tree = ET.parse(outdir / "output.xml")
        self.test_plan = tree.getroot()

        submission = {
            "version": self.submission_schema_version,
            "origin": self.get_origin(),
            "session_data": self.get_session_data(),
            "results": self.get_results(),
            "category_map": self.category_map,
        }

        return submission

    def get_origin(self) -> dict[str, Any]:
        """
        This function returns the origin of the test submission.

        Returns:
            Dictionary containing the origin of the test submission
        """
        origin: dict[str, str | dict[str, str]] = {}
        origin["name"] = "YARF"
        if (current_yarf_info := self.get_yarf_snap_info()) is not None:
            origin["version"] = current_yarf_info["version"]
            origin["packaging"] = {
                "type": "snap",
                "name": current_yarf_info["name"],
                "version": current_yarf_info["version"],
                "revision": current_yarf_info["revision"],
            }
        else:
            origin["version"] = metadata.version("yarf")
            origin["packaging"] = {
                "type": "source",
                "version": metadata.version("yarf"),
            }

        return origin

    def get_session_data(self) -> dict[str, Any]:
        """
        This function assembles and returns the session data of the test plan.

        Returns:
            Dictionary containing session data
        """
        session_data_keys = {
            "title",
            "description",
            "test_plan_id",
            "execution_id",
        }
        session_data = {}
        for meta in self.test_plan.iter("meta"):
            meta_name = meta.attrib["name"].lower()
            if meta_name in session_data_keys:
                session_data[meta_name] = meta.text

        return session_data

    def get_results(self) -> list[dict[str, str]]:
        """
        Convert the XML output file from Robot Framework to the result section
        in submission schema.

        Returns:
            List of dictionaries containing test results
        """
        test_results: list[dict[str, Any]] = []
        for suite in self.test_plan.iter("suite"):
            if len(suite.findall("test")) == 0:
                continue

            test_results = self.get_tests_results_from_suite(
                suite, test_results
            )

        return test_results

    _STATUS_OUTCOME_MAP: dict[str, str] = {
        "PASS": "passed",
        "FAIL": "failed",
        "SKIP": "skipped",
        "NOT RUN": "skipped",
    }

    def _get_duration(self, status_tag: Element) -> float:
        """
        Calculate test duration from status tag attributes.

        Arguments:
            status_tag: XML element containing timing information

        Returns:
            Duration in seconds as a float
        """
        if "endtime" in status_tag.attrib and "starttime" in status_tag.attrib:
            return float(
                parse(status_tag.attrib["endtime"]).timestamp()
                - parse(status_tag.attrib["starttime"]).timestamp()
            )
        return float(status_tag.attrib["elapsed"])

    def _extract_yarf_tags(self, test: Element) -> dict[str, str]:
        """
        Extract YARF-specific tags from a test element.

        Arguments:
            test: XML element representing a test

        Returns:
            Dictionary mapping tag names to their values

        Raises:
            AssertionError: if a tag element has no text content
        """
        yarf_tags = {}
        for tag in test.findall("tag"):
            assert tag.text is not None, "Tag does not have text"
            if tag.text.startswith(LABEL_PREFIX):
                _, tag_name, tag_value = tag.text.split(":", 2)
                yarf_tags[tag_name] = tag_value.strip()
        return yarf_tags

    def get_tests_results_from_suite(
        self,
        suite: Element,
        test_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Get all tests results.

        Arguments:
            suite: suite XML element
            test_results: list to store test results

        Returns:
            list of test results

        Raises:
            AssertionError: when tag does not have text
        """
        for test in suite.findall("test"):
            doc_tag = test.find("doc")
            status_tag = test.find("status")
            assert status_tag is not None, "Status tag not found"

            yarf_tags = self._extract_yarf_tags(test)
            test_id = f"{self.yarf_namespace}::{suite.attrib['name']}/{test.attrib['name']}"
            outcome = self._STATUS_OUTCOME_MAP[status_tag.attrib["status"]]

            result = {
                "id": test_id,
                "test_description": doc_tag.text
                if doc_tag is not None
                else "",
                "certification_status": yarf_tags["certification_status"],
                "category_id": yarf_tags["category_id"],
                "outcome": outcome,
                "comments": "",
                "io_log": "".join(self.get_io_log(test, [])),
                "duration": self._get_duration(status_tag),
            }

            if (test_group_id := yarf_tags.get("test_group_id")) is not None:
                result["test_group_id"] = test_group_id

            test_results.append(result)
        return test_results

    def _get_kw_node_info(
        self, keyword_chain: str, iter_count: int
    ) -> list[str]:
        """
        Get formatted information for a keyword node.

        Arguments:
            keyword_chain: chain of keyword names
            iter_count: current iteration count

        Returns:
            List of formatted strings for the keyword info
        """
        curr = []
        if iter_count > 0:
            curr.append(f">> Iteration {iter_count}:\n")
        curr.append(f"Keyword: {keyword_chain}\n")
        return curr

    def _get_msg_node_info(self, node: Element) -> list[str]:
        """
        Get formatted information for a message node.

        Arguments:
            node: XML element representing a message

        Returns:
            List containing the formatted message string
        """
        timestamp = node.attrib.get("time") or node.attrib.get("timestamp", "")
        msg_level = node.attrib["level"]
        msg_text = node.text.strip() if node.text else ""
        return [f"[{timestamp} - {msg_level}] {msg_text}\n"]

    def _get_branch_node_info(self, node: Element) -> list[str]:
        """
        Get formatted information for a branch node.

        Arguments:
            node: XML element representing a branch

        Returns:
            List containing the formatted branch string
        """
        type = node.attrib["type"]
        condition = node.attrib.get("condition", "")
        return [f"{type}: {condition}\n"]

    def get_node_info(
        self,
        node: Element,
        keyword_chain: str,
        iter_count: int,
    ) -> tuple[list[str], str]:
        """
        Get information from the given XML node.

        Arguments:
            node: XML node
            keyword_chain: keyword chain
            iter_count: iteration count

        Returns:
            current information
        """
        if node.tag == "kw":
            keyword_name = node.attrib["name"]
            keyword_chain_sep = " -> " if keyword_chain else ""
            keyword_chain += f"{keyword_chain_sep}{keyword_name}"
            return self._get_kw_node_info(
                keyword_chain, iter_count
            ), keyword_chain

        if node.tag == "msg":
            return self._get_msg_node_info(node), keyword_chain

        if node.tag == "branch":
            return self._get_branch_node_info(node), keyword_chain

        return [], keyword_chain

    _TAG_HEADERS: dict[str, str] = {
        "kw": "=" * CONSOLE_COLUMN_SIZE,
        "if": ">> IF STATEMENT ",
        "for": ">> FOR LOOP ",
    }
    _TAG_FOOTERS: dict[str, str] = {
        "kw": "\n",
        "if": "<< END IF ",
        "for": "<< END FOR ",
    }

    def get_io_log(
        self,
        node: Element,
        res: list[str] = [],
        keyword_chain: str = "",
        iter_count: int = 0,
    ) -> list[str]:
        """
        DFS Preorder get IO log for a given node.

        Arguments:
            node: XML node
            res: accumulated result
            keyword_chain: keyword chain
            iter_count: iteration count

        Returns:
            accumulated result with IO log information
        """
        tag_header = self._TAG_HEADERS.get(node.tag)
        if tag_header:
            res.append(
                tag_header
                + ">" * (CONSOLE_COLUMN_SIZE - len(tag_header))
                + "\n"
            )

        curr, keyword_chain = self.get_node_info(
            node, keyword_chain, iter_count
        )
        if curr:
            res.extend(curr)

        for child in node:
            if child.tag == "iter":
                iter_count += 1
            res = self.get_io_log(child, res, keyword_chain, iter_count)

        tag_footer = self._TAG_FOOTERS.get(node.tag)
        if tag_footer:
            if node.tag == "kw":
                res.append(tag_footer)
            else:
                res.append(
                    tag_footer
                    + "<" * (CONSOLE_COLUMN_SIZE - len(tag_footer))
                    + "\n"
                )

        return res
