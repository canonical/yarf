import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element

from dateutil.parser import parse

try:
    CONSOLE_COLUMN_SIZE, _ = os.get_terminal_size()
except OSError:
    # Default to some reasonable dimensions
    CONSOLE_COLUMN_SIZE = 80


class OutputConverter:
    supported_formats = set(["hexr"])

    def __init__(self, outdir: Path) -> None:
        if not outdir.exists():
            raise ValueError("Output directory does not exist")

        self.outdir = outdir

    def convert_to_format(self, output_format: str) -> None:
        """
        Convert the output to specified output format.

        Arguments:
            output_format: output format to process

        Raises:
            ValueError: if the output format is not supported
        """
        if output_format not in self.supported_formats:
            raise ValueError(f"Unsupported output format: {output_format}")

        # Convert output to the specified format and save to file
        if output_format == "hexr":
            self.convert_to_hexr()

    def convert_to_hexr(self) -> None:
        """
        Convert the XML output file from Robot Framework to the result section
        in submission schema.
        """
        output_file = self.outdir / "submission_to_hexr.json"
        tree = ET.parse(self.outdir / "output.xml")
        root = tree.getroot()
        submission = {}
        submission["version"] = 1

        # Get origin
        submission["origin"] = {}

        # Get session data
        submission["session_data"] = {}

        # Get results
        test_results = []
        for suite in root.findall("suite"):
            print(f"Child tag: {suite.tag}, Child attributes: {suite.attrib}")
            test_results = self.get_tests_results_from_suite(
                suite, test_results
            )

        submission["results"] = test_results
        with open(output_file, "w") as f:
            json.dump(submission, f, indent=4)

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

            test_results.append(
                {
                    "id": suite.attrib["name"]
                    + "/"
                    + test.attrib["name"],  # TODO: Add namespace
                    "test_description": doc_tag.text if doc_tag else "",
                    "certification_status": "non-blocker",  # TODO: Add yarf tag
                    "category_id": "uncategorized",  # TODO: Add yarf tag
                    "outcome": status_tag.attrib["status"],
                    "comments": "",  # TODO: Add comments,
                    "io_log": self.get_io_log(test),
                    "duration": str(
                        parse(status_tag.attrib["endtime"])
                        - parse(status_tag.attrib["starttime"])
                    ),
                    "type": "",  # TODO: Add test type
                    "template_id": "",  # TODO: Add yarf tag
                }
            )
        return test_results

    def get_node_info(
        self, node: Element, keyword_chain: str, iter_count: int
    ) -> str:
        """
        Get information from the given XML node.

        Arguments:
            node: XML node
            keyword_chain: keyword chain
            iter_count: iteration count

        Returns:
            string containing information from the given XML node
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

        return curr

    def get_io_log(
        self,
        node: Element,
        res: str = "",
        keyword_chain: str = "",
        iter_count: int = 0,
    ) -> str:
        """
        Get IO log for a given node.

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
            res += (
                tag_info + ">" * (CONSOLE_COLUMN_SIZE - len(tag_info)) + "\n"
            )

        curr = self.get_node_info(node, keyword_chain, iter_count)
        if len(curr) > 0:
            res += curr

        for child in node:
            if child.tag == "iter":
                iter_count += 1
            res = self.get_io_log(child, res, keyword_chain, iter_count)

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

        return res
