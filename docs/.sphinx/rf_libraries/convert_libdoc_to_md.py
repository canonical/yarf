"""
This script uses Robot Framework `libdoc` tool to generate resource documentation
and convert the JSON output in Markdown format for the YARF sphinx documentation site.
"""

import json
import logging
import os
import re
import urllib.parse
from enum import Enum
from pathlib import Path
from textwrap import dedent
from bs4 import BeautifulSoup
from generate_library_libdoc import generate_libdoc_for_abstract_libraries
from robot.libdoc import libdoc

logger = logging.getLogger(__name__)


class RobotFile(Enum):
    LIBRARY = 0
    RESOURCE = 1


SUFFIX = {
    RobotFile.LIBRARY: ".py",
    RobotFile.RESOURCE: ".resource",
}

EXAMPLE_HEADINGS = ("example:", "examples:")

PACKAGE = {
    RobotFile.LIBRARY: [
        Path("yarf/rf_libraries/libraries"),
        Path("yarf/rf_libraries/libraries/vnc"),
        Path("yarf/rf_libraries/libraries/mir"),
        Path("yarf/rf_libraries/libraries/llm_client"),
        Path("yarf/rf_libraries/interactive_console"),
    ],
    RobotFile.RESOURCE: [
        Path("yarf/rf_libraries/resources"),
    ],
}


def convert_json_to_markdown(json_file: Path, markdown_file: Path):
    """
    Converts a JSON file, which contains the documentation of Robot Framework
    resources, into a Markdown file. The JSON file should be generated using the
    `libdoc` command provided by the Robot Framework library.

    :param json_file: The path to the JSON file to be converted.
    :param markdown_file: The path to the Markdown file to be created.
    """
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    with open(markdown_file, "w", encoding="utf-8") as md:

        try:
            title = data["name"]
        except KeyError as exc:
            raise ValueError("Title not found in JSON data") from exc

        content = [f"# {title}\n\n"]
        description = fix_link_anchors(data.get("doc", "").strip())
        if description:
            content.append(f"{description}\n\n")

        # Add type and scope information if available, skipping empty values
        for key in ["type", "scope"]:
            value = data.get(key, "").strip()
            if value:
                content.append(f"- **{key.capitalize()}**: {value}\n")

        md_content = "".join(content) + "\n"
        md.write(md_content)

        # Write the keywords
        if "keywords" in data:

            md.write("## Keywords\n\n")

            for i, keyword in enumerate(data["keywords"]):
                content = []
                # Write section title
                # h2 title in contents panel
                content.append(f"### {keyword['name']}\n\n")
                # Write keyword description and fix URL-encoded anchors
                doc_html, example = extract_example(keyword['doc'])
                keyword_doc = fix_link_anchors(doc_html)
                content.append(f"{keyword_doc}\n\n")

                if (
                    "returnType" in keyword
                    and keyword["returnType"] is not None
                ):
                    return_type = format_type(keyword["returnType"])
                    content.append(
                        f"#### Return\n\n```\n{return_type}\n```\n\n"
                    )

                if keyword.get("args", []):
                    content.append("#### Positional and named arguments\n\n")
                    headers = [
                        "Name",
                        "Type",
                        "Default Value",
                        "Kind",
                        "Required",
                    ]
                    md_table = "| " + " | ".join(headers) + " |\n"
                    md_table += (
                        "| " + " | ".join(["---"] * len(headers)) + " |\n"
                    )

                    for arg in keyword["args"]:
                        name = arg.get("name", "")
                        arg_type = (
                            arg.get("type").get("typedoc")
                            if arg.get("type")
                            else ""
                        )
                        default = (
                            arg.get("defaultValue")
                            if arg.get("defaultValue")
                            else ""
                        )
                        kind = arg.get("kind", "")
                        required = (
                            "Yes" if arg.get("required", False) else "No"
                        )

                        md_table += f"| {name} | {arg_type} | {default} | {kind} | {required} |\n"

                    # Write the constructed table to markdown
                    content.append(md_table + "\n")

                if example:
                    content.append(
                        "#### Example\n\n"
                        f"```robotframework\n{example}\n```\n\n"
                    )

                md.write("".join(content))
                if i < len(data["keywords"]) - 1:
                    md.write("<hr style=\"border:1px solid grey\">\n\n")

    json_file.unlink(missing_ok=True)


def format_type(type_info):
    """
    Render a libdoc type entry as a readable type expression, for example
    ``list[dictionary]`` or ``tuple[integer, integer] | None``.

    :param type_info: A libdoc type mapping with ``name``, ``typedoc``,
        ``nested`` and ``union`` keys.
    :return: The type expression as a string.
    """
    if not type_info:
        return ""

    nested = [format_type(entry) for entry in type_info.get("nested") or []]
    name = type_info.get("typedoc") or type_info.get("name") or ""

    if not nested:
        return name
    if type_info.get("union"):
        return " | ".join(nested)
    return f"{name}[{', '.join(nested)}]"


def extract_example(html_text):
    """
    Pull the ``Example:`` section out of a keyword documentation body.

    The section is written in the docstring as a Robot Framework preformatted
    block (lines prefixed with ``|``) so that libdoc renders it as ``<pre>``.

    :param html_text: The keyword documentation rendered as HTML by libdoc.
    :return: A tuple of the documentation without the example section and the
        example source, or ``None`` when no example is present.
    """
    soup = BeautifulSoup(html_text, 'html.parser')
    for paragraph in soup.find_all('p'):
        if paragraph.get_text(strip=True).lower() not in EXAMPLE_HEADINGS:
            continue

        block = paragraph.find_next_sibling('pre')
        if block is None:
            continue

        example = block.get_text().strip("\n")
        block.decompose()
        paragraph.decompose()
        return str(soup).strip(), example

    return html_text, None

def fix_link_anchors(html_text):
    """
    Replace special characters in the URL anchors in the given HTML text with dashes
    """
    soup = BeautifulSoup(html_text, 'html.parser')
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '#' in href:
            # Split anchor part in URL and clean up decoded text
            parts = href.rsplit('#', 1)
            if len(parts) == 2:
                url_part, anchor_part = parts
                if anchor_part.strip():
                    decoded = urllib.parse.unquote(anchor_part)
                    clean = re.sub(r'[^a-zA-Z0-9]+', '-', decoded.lower()).strip('-')
                    if clean:
                        link['href'] = f'{url_part}#{clean}' if url_part else f'#{clean}'
    return str(soup)


def generate_libdoc(file: Path, output_file: Path):
    """
    Simply run `libdoc` on the file.
    """
    rc = libdoc(
        str(file),
        str(output_file),
        quiet=True,
    )
    if rc != 0:
        raise ValueError()


def generate_markdown(
    target: RobotFile,
    source_dir: Path,
    docs_ref_dir: Path,
):
    """
    Given a target directory and the expected file type,
    this function will invoke libdoc on every target file
    attempting to generate a documentation file in Markdown format.
    """
    for f in source_dir.iterdir():
        if not f.is_file():
            continue

        if f.suffix != SUFFIX[target]:
            continue

        # If a library, it should end not start with "test_"
        if target == RobotFile.LIBRARY and (
            f.stem.startswith("test_")
            or f.stem == "__init__"
        ):
            continue

        is_base_class = False
        if target == RobotFile.LIBRARY and f.parent.stem == "libraries":
            if f.stem.endswith("_base"):
                is_base_class = True
            else:
                continue

        robot_file = f
        input_json_file = docs_ref_dir / f"{f.stem}.json"
        output_md_file = (
            docs_ref_dir / f"{target.name.lower()}-{f.stem}.md"
        )

        try:
            if target in [RobotFile.RESOURCE, RobotFile.LIBRARY]:
                if is_base_class:
                    # For base classes, generate the libdoc for libraries
                    generate_libdoc_for_abstract_libraries(robot_file, input_json_file)
                else:
                    generate_libdoc(robot_file, input_json_file)
            else:
                logger.warning("Unknown robot file.")
                continue

        except ValueError:
            logger.warning(
                "Libdoc failed at generating the doc. Skipped %s",
                robot_file,
            )
            continue

        # Skip conversion if the JSON file was not created
        if not input_json_file.exists():
            logger.warning(
                "Expected JSON file not found. Skipped %s",
                input_json_file,
            )
            continue

        # Convert the JSON file to Markdown
        convert_json_to_markdown(input_json_file, output_md_file)
        print(f"  Converted to <{output_md_file}>")


def main():
    """
    Main entry point for the script. This script generates the Robot Framework
    resource documentation in Markdown format for the YARF project.
    The script first runs the `libdoc` command to generate a JSON file for each
    `.resource` file under `yarf/rf_libraries/resources/`, and
    then converts the JSON file to a Markdown file as
    `yarf/docs/reference/rf_libraries/resource-<name>.md`.
    """

    # this script is located in "yarf/docs/.sphinx/rf_libraries"
    docs_dir = Path(__file__).parent.parent.parent
    repo_root = docs_dir.parent

    for target in RobotFile:
        for source_pkg in PACKAGE[target]:
            source_dir = repo_root / source_pkg
            idx = source_dir.parts.index("rf_libraries")
            
            target_dir = docs_dir / Path("reference", *source_dir.parts[idx:])

            if not target_dir.exists():
                os.makedirs(target_dir)
            
            if target is RobotFile.LIBRARY and not (target_dir / "index.md").exists():
                with open(target_dir / "index.md", "w", encoding="utf-8") as index_file:
                    platform_name = re.sub(r'_+', ' ', target_dir.stem.strip('_'))
                    if platform_name == "libraries":
                        platform_name = "base"

                    index_file.write(f"# {platform_name.capitalize()} libraries\n\n")
                    if platform_name == "base":
                        index_file.write(
                            dedent(
                                """
                                YARF provides the following base classes for implementing a new platform plugin.\n
                                For details of how to implement a new platform plugin, please refer to the [Platform Plugin Development Guide](../../../how-to/platform-plugins.md).\n
                                """
                            )
                        )
                    else:
                        index_file.write(
                            f"YARF supports the following classes for {platform_name}:\n\n"
                        )

                    index_file.write(
                        dedent(
                            """
                            ```{toctree}
                            :maxdepth: 1
                            :glob:
                            library-*
                            ```
                            """
                        )
                    )

            generate_markdown(target, source_dir, target_dir)


if __name__ == "__main__":
    main()
