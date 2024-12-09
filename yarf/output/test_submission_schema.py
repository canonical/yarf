import os
import re
import xml.etree.ElementTree as ET
from datetime import date
from importlib import metadata
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element

from dateutil.parser import parse
from robot.api import TestSuite

from yarf.output import OutputConverterBase

try:
    CONSOLE_COLUMN_SIZE, _ = os.get_terminal_size()
except OSError:
    # Default to some reasonable dimensions
    CONSOLE_COLUMN_SIZE = 80


class TestSubmissionSchema(OutputConverterBase):
    """
    Output converter for Test Submission Schema format.

    Attributes:
        submission_schema_version: The Test Submission Schema submission schema version
    """

    submission_schema_version = 1

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

        if len(missing_metadata) > 0:
            raise ValueError(
                f"Missing/wrong pattern for required metadata: {', '.join(missing_metadata)}"
            )

        # Check if all required tags exists
        tags_err_msg = []
        category_id_regex = (
            r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+::[A-Za-z0-9_\-]+$"
        )
        for s in test_plan.suites:
            for test in s.tests:
                missing_tags = {
                    "certification_status",
                    "type",
                    "namespace",
                    "category_id",
                }
                for tag in test.tags:
                    if not tag.startswith("yarf:"):
                        continue

                    _, tag_name, tag_value = tag.split(":", 2)
                    if tag_name in missing_tags:
                        missing_tags.remove(tag_name)

                    if (
                        tag_name == "certification_status"
                        and tag_value.strip() not in ["blocker", "non-blocker"]
                    ):
                        tags_err_msg.append(
                            f"[{test.parent.name}/{test.name}] Invalid certification_status expression: {tag_value}"
                        )

                    elif tag_name == "category_id" and not re.fullmatch(
                        category_id_regex, tag_value.strip()
                    ):
                        tags_err_msg.append(
                            f"[{test.parent.name}/{test.name}] Invalid category_id expression: {tag_value}"
                        )

                if len(missing_tags) > 0:
                    tags_err_msg.append(
                        f"[{test.parent.name}/{test.name}] Missing tags: {', '.join(missing_tags)}"
                    )

        if len(tags_err_msg) > 0:
            raise ValueError("\n".join(tags_err_msg))

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
        }

        return submission

    def get_origin(self) -> dict[str, Any]:
        """
        This function returns the origin of the test submission.

        Returns:
            Dictionary containing the origin of the test submission
        """
        origin = {}
        origin["name"] = "YARF"
        if (current_yarf_info := self.get_yarf_snap_info()) is not None:
            origin["version"] = current_yarf_info["version"]
            origin["packaging"] = {
                "type": "snap",
                "name": current_yarf_info["name"],
                "version": current_yarf_info["version"],
                "revision": current_yarf_info["revision"],
                "date": current_yarf_info["date"],
            }
        else:
            origin["version"] = metadata.version("yarf")
            origin["packaging"] = {
                "type": "source",
                "name": "yarf",
                "version": metadata.version("yarf"),
                "revision": None,
                "date": str(date.today()),
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
        test_results = []
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
        """
        for test in suite.findall("test"):
            doc_tag = test.find("doc")
            status_tag = test.find("status")
            yarf_tags = {}
            for tag in test.findall("tag"):
                if tag.text.startswith("yarf:"):
                    _, tag_name, tag_value = tag.text.split(":", 2)
                    yarf_tags[tag_name] = tag_value.strip()

            id = (
                yarf_tags["namespace"]
                + "::"
                + suite.attrib["name"]
                + "/"
                + test.attrib["name"]
            )
            outcome = status_tag.attrib["status"]
            comments = (
                ""  # no comments for now since we haven't support interactive
            )

            io_log, templates = self.get_io_log_and_templates(test, set(), [])
            test_results.append(
                {
                    "id": id,
                    "test_description": doc_tag.text if doc_tag else "",
                    "certification_status": yarf_tags["certification_status"],
                    "category_id": yarf_tags["category_id"],
                    "outcome": outcome,
                    "comments": comments,
                    "io_log": "".join(io_log),
                    "duration": str(
                        parse(status_tag.attrib["endtime"])
                        - parse(status_tag.attrib["starttime"])
                    ),
                    "type": yarf_tags["type"],
                    # templates in Robot Framework is by keyword, not by test case, so we join all keyword templates used under a test together
                    "template_id": ",".join(templates)
                    if len(templates) > 0
                    else None,
                }
            )
        return test_results

    def get_node_info(
        self,
        node: Element,
        keyword_chain: str,
        iter_count: int,
        templates: set[str],
    ) -> tuple[list[str], set[str], str]:
        """
        Get information from the given XML node.

        Arguments:
            node: XML node
            keyword_chain: keyword chain
            iter_count: iteration count
            templates: set of templates encountered

        Returns:
            current information and updated set of templates encountered
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

            if "sourcename" in node.attrib:
                template = node.attrib["sourcename"]
                curr.append(f"Template: {template}\n")
                templates.add(template)

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

        return curr, templates, keyword_chain

    def get_io_log_and_templates(
        self,
        node: Element,
        templates: set[str],
        res: list[str] = [],
        keyword_chain: str = "",
        iter_count: int = 0,
    ) -> tuple[str, set[str]]:
        """
        Get IO log for a given node.

        Arguments:
            node: XML node
            templates: set of templates encountered
            res: accumulated result
            keyword_chain: keyword chain
            iter_count: iteration count

        Returns:
            accumulated result with IO log information and templates encountered
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

        curr, templates, keyword_chain = self.get_node_info(
            node, keyword_chain, iter_count, templates
        )
        if len(curr) > 0:
            res.extend(curr)

        for child in node:
            if child.tag == "iter":
                iter_count += 1
            res, templates = self.get_io_log_and_templates(
                child, templates, res, keyword_chain, iter_count
            )

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

        return res, templates
