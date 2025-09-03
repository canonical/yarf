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

    def check_test_plan(self, test_plan: TestSuite) -> None:
        """
        Check the test suite to see if it has all the required information for
        the TestSubmissionSchema output format.

        Arguments:
            test_plan: an initialized executable TestSuite

        Raises:
            ValueError: when any metadata or tag is missing / in the wrong format
        """
        # Check of all required metadata exists
        missing_metadata = {"title", "test_plan_id"}
        test_plan_id_regex = (
            r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+::[a-zA-Z0-9_]+$"
        )
        for data in test_plan.metadata:
            if data.lower() == "title" or (
                data.lower() == "test_plan_id"
                and re.fullmatch(test_plan_id_regex, test_plan.metadata[data])
            ):
                missing_metadata.remove(data.lower())

        # Add default for namespace if missing
        if test_plan.metadata.get("namespace", None) is None:
            test_plan.metadata["namespace"] = self.yarf_namespace
        else:
            self.yarf_namespace = test_plan.metadata["namespace"]

        # Check if all required tags exists
        test_err_msg = []
        category_id_regex = (
            r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+::[A-Za-z0-9_\-]+$"
        )
        for s in test_plan.suites:
            for test in s.tests:
                if len(test.doc) > 80:
                    test_err_msg.append(
                        f"[{test.parent.name}/{test.name}] Test case description is too long: {test.doc}"
                    )

                missing_tags = {
                    "certification_status",
                    "category_id",
                }
                for tag in test.tags:
                    if not tag.startswith(LABEL_PREFIX):
                        continue

                    _, tag_name, tag_value = tag.split(":", 2)
                    if tag_name in missing_tags:
                        missing_tags.remove(tag_name)

                    if (
                        tag_name == "certification_status"
                        and tag_value.strip() not in ["blocker", "non-blocker"]
                    ):
                        test_err_msg.append(
                            f"[{test.parent.name}/{test.name}] Invalid certification_status expression: {tag_value}"
                        )

                    elif tag_name == "category_id" and not re.fullmatch(
                        category_id_regex, tag_value.strip()
                    ):
                        test_err_msg.append(
                            f"[{test.parent.name}/{test.name}] Invalid category_id expression: {tag_value}"
                        )

                if len(missing_tags) > 0:
                    test_err_msg.append(
                        f"[{test.parent.name}/{test.name}] Missing tags: {', '.join(missing_tags)}"
                    )

        err_msg = ""
        if len(missing_metadata) > 0:
            err_msg = f"Missing/wrong pattern for required metadata: {', '.join(missing_metadata)}\n"

        if len(test_err_msg) > 0:
            err_msg += "\n".join(test_err_msg)

        if len(err_msg) > 0:
            raise ValueError(err_msg)

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
        session_data = {}
        for meta in self.test_plan.iter("meta"):
            meta_name = meta.attrib["name"].lower()
            if meta_name == "title":
                session_data["title"] = meta.text
            elif meta_name == "description":
                session_data["description"] = meta.text
            elif meta_name == "test_plan_id":
                session_data["test_plan_id"] = meta.text
            elif meta_name == "execution_id":
                session_data["execution_id"] = meta.text

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
            yarf_tags = {}
            for tag in test.findall("tag"):
                assert tag.text is not None, "Tag does not have text"
                if tag.text.startswith(LABEL_PREFIX):
                    _, tag_name, tag_value = tag.text.split(":", 2)
                    yarf_tags[tag_name] = tag_value.strip()

            id = (
                self.yarf_namespace
                + "::"
                + suite.attrib["name"]
                + "/"
                + test.attrib["name"]
            )
            assert status_tag is not None, "Status tag not found"
            status = status_tag.attrib["status"]
            if status == "PASS":
                outcome = "passed"
            elif status == "FAIL":
                outcome = "failed"
            elif status == "SKIP" or status == "NOT RUN":
                outcome = "skipped"

            io_log = self.get_io_log(test, [])
            result = {
                "id": id,
                "test_description": doc_tag.text if doc_tag else "",
                "certification_status": yarf_tags["certification_status"],
                "category_id": yarf_tags["category_id"],
                "outcome": outcome,
                "comments": "",
                "io_log": "".join(io_log),
                "duration": float(
                    (
                        parse(status_tag.attrib["endtime"]).timestamp()
                        - parse(status_tag.attrib["starttime"]).timestamp()
                    )
                ),
            }

            if yarf_tags.get("test_group_id", None) is not None:
                result["test_group_id"] = yarf_tags.get("test_group_id", None)

            test_results.append(result)
        return test_results

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
        curr = []
        if node.tag == "kw":
            keyword_name = node.attrib["name"]
            if len(keyword_chain) > 0:
                keyword_chain += f" -> {keyword_name}"
            else:
                keyword_chain = keyword_name

            if iter_count > 0:
                curr.append(f">> Iteration {iter_count}:\n")

            curr.append(f"Keyword: {keyword_chain}\n")

        elif node.tag == "msg":
            timestamp = node.attrib["timestamp"]
            msg_level = node.attrib["level"]
            msg_text = node.text.strip() if node.text else ""
            curr.append(f"[{timestamp} - {msg_level}] {msg_text}\n")

        elif node.tag == "branch":
            type = node.attrib["type"]
            condition = (
                node.attrib["condition"] if "condition" in node.attrib else ""
            )
            curr.append(f"{type}: {condition}\n")

        return curr, keyword_chain

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
        is_keyword = False
        is_if_statement = False
        is_for_statement = False
        tag_info = None
        if node.tag == "kw":
            tag_info = "=" * CONSOLE_COLUMN_SIZE
            is_keyword = True

        elif node.tag == "if":
            tag_info = ">> IF STATEMENT "
            is_if_statement = True

        elif node.tag == "for":
            tag_info = ">> FOR LOOP "
            is_for_statement = True

        if tag_info:
            res.append(
                tag_info + ">" * (CONSOLE_COLUMN_SIZE - len(tag_info)) + "\n"
            )

        curr, keyword_chain = self.get_node_info(
            node, keyword_chain, iter_count
        )
        if len(curr) > 0:
            res.extend(curr)

        for child in node:
            if child.tag == "iter":
                iter_count += 1
            res = self.get_io_log(child, res, keyword_chain, iter_count)

        if is_keyword:
            res.append("\n")
            is_keyword = False

        elif is_if_statement:
            end_if = "<< END IF "
            res.append(
                end_if + "<" * (CONSOLE_COLUMN_SIZE - len(end_if)) + "\n"
            )
            is_if_statement = False

        elif is_for_statement:
            end_for = "<< END FOR "
            res.append(
                end_for + "<" * (CONSOLE_COLUMN_SIZE - len(end_for)) + "\n"
            )
            is_for_statement = False

        return res
