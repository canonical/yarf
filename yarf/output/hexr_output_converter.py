import os
import xml.etree.ElementTree as ET
from datetime import date
from importlib import metadata
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element

from dateutil.parser import parse

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

    def get_output(self, outdir: Path) -> dict[str, Any]:
        """
        Convert the output to specified output format.

        Arguments:
            outdir: Path to the output directory

        Returns:
            Dictionary containing the converted output in Test Submission Schema format
        """
        submission = {}
        submission["version"] = self.submission_schema_version
        submission["origin"] = self.get_origin()
        submission["session_data"] = self.get_session_data()
        submission["results"] = self.get_hexr_results(outdir)

        return submission

    def get_origin(self) -> dict[str, Any]:
        origin = {}
        origin["name"] = "YARF"
        if "SNAP" in os.environ:
            current_yarf_info = self.get_yarf_snap_info()
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
                "revision": "No revision",
                "date": str(date.today()),
            }
        return origin

    def get_session_data(self) -> dict[str, Any]:
        session_data = {
            "title": "title",
            "description": "Optional field",
            "test_plan_id": "com.canonical.yarf::yarf-tillamook-auto-test-25.04-auto",
            "execution_id": "Optional field",
        }
        return session_data

    def get_hexr_results(self, outdir: Path) -> list[dict[str, str]]:
        """
        Convert the XML output file from Robot Framework to the result section
        in submission schema.

        Arguments:
            outdir: Path to the output directory

        Returns:
            List of dictionaries containing test results
        """
        tree = ET.parse(outdir / "output.xml")
        test_plan = tree.getroot()

        test_results = []
        for suite in test_plan.iter("suite"):
            print(f"Child tag: {suite.tag}, Child attributes: {suite.attrib}")
            test_results = self.get_tests_results_from_suite(
                suite, test_results
            )

        return test_results

    def check_missing_tags(self, yarf_tags: dict[str, str]) -> None:
        """
        Check if all required yarf namespace tags are present.

        Arguments:
            yarf_tags: dictionary containing yarf namespace tags

        Raises:
            AttributeError: if any required yarf tags are missing
        """
        required_tags = [
            "namespace",
            "category_id",
            "type",
            "certification_status",
        ]
        missing_tags_msg = ""
        for tag_name in required_tags:
            if tag_name not in yarf_tags:
                missing_tags_msg += f"yarf:{tag_name}: [value]\n"

        if len(missing_tags_msg) > 0:
            raise AttributeError(
                "Expected the following yarf tags to be present:\n"
                + missing_tags_msg
            )

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
                    tag_info = tag.text.split(":", 2)
                    yarf_tags[tag_info[1]] = tag_info[2].strip()

            self.check_missing_tags(yarf_tags)

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

            io_log, templates = self.get_io_log_and_templates(test, set())
            test_results.append(
                {
                    "id": id,
                    "test_description": doc_tag.text if doc_tag else "",
                    "certification_status": yarf_tags["certification_status"],
                    "category_id": yarf_tags["category_id"],
                    "outcome": outcome,
                    "comments": comments,
                    "io_log": io_log,
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
    ) -> tuple[str, set[str]]:
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
        curr = ""
        if node.tag == "kw":
            keyword_name = node.attrib["name"]
            if len(keyword_chain) > 0:
                keyword_chain += f" -> {keyword_name}"
            else:
                keyword_chain = keyword_name

            if iter_count > 0:
                curr += f">> Iteration {iter_count}:\n"

            curr += f"Keyword: {keyword_chain}\n"

            if "sourcename" in node.attrib:
                template = node.attrib["sourcename"]
                curr += f"Template: {template}\n"
                templates.add(template)

        elif node.tag == "msg":
            timestamp = node.attrib["timestamp"]
            msg_level = node.attrib["level"]
            curr += f"[{timestamp} - {msg_level}] "
            curr += node.text.strip() + "\n"

        elif node.tag == "branch":
            type = node.attrib["type"]
            condition = (
                node.attrib["condition"] if "condition" in node.attrib else ""
            )
            curr += f"{type}: {condition}\n"

        return curr, templates

    def get_io_log_and_templates(
        self,
        node: Element,
        templates: set[str],
        res: str = "",
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
            res += (
                tag_info + ">" * (CONSOLE_COLUMN_SIZE - len(tag_info)) + "\n"
            )

        curr, templates = self.get_node_info(
            node, keyword_chain, iter_count, templates
        )
        if len(curr) > 0:
            res += curr

        for child in node:
            if child.tag == "iter":
                iter_count += 1
            res, templates = self.get_io_log_and_templates(
                child, templates, res, keyword_chain, iter_count
            )

        if is_keyword:
            res += "\n"
            is_keyword = False

        elif is_if_statement:
            end_if = "<< END IF "
            res += end_if + "<" * (CONSOLE_COLUMN_SIZE - len(end_if)) + "\n"
            is_if_statement = False

        elif is_for_statement:
            end_for = "<< END FOR "
            res += end_for + "<" * (CONSOLE_COLUMN_SIZE - len(end_for)) + "\n"
            is_for_statement = False

        return res, templates
