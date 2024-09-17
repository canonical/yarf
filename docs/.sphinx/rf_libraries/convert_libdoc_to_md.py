"""
This script uses Robot Framework `libdoc` tool to generate resource documentation
and convert the JSON output in Markdown format for the YARF sphinx documentation site.
"""

import json
import logging
import os
from enum import Enum
from pathlib import Path

from generate_library_libdoc import generate_libdoc_for_libraries
from robot.libdoc import libdoc

logger = logging.getLogger(__name__)


class RobotFile(Enum):
    LIBRARY = 0
    RESOURCE = 1


SUFFIX = {
    RobotFile.LIBRARY: ".py",
    RobotFile.RESOURCE: ".resource",
}

PACKAGE = {
    RobotFile.LIBRARY: Path("yarf/rf_libraries/libraries"),
    RobotFile.RESOURCE: Path("yarf/rf_libraries/resources"),
}


def convert_json_to_markdown(json_file, markdown_file):
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
        description = data.get("doc", "").strip()
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

            for keyword in data["keywords"]:
                content = []
                # Write section title
                # h2 title in contents panel
                content.append(f"### {keyword['name']}\n\n")
                content.append(f"{keyword['doc']}\n\n")

                if (
                    "returnType" in keyword
                    and keyword["returnType"] is not None
                ):
                    content.append(
                        f"### Return\n\n{keyword['returnType']}\n\n"
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
                    content.append(md_table + "\n\n")

                md.write("".join(content))


def generate_libdoc_for_resources(resource_file: Path, output_file: Path):
    """
    Simply run `libdoc` on the resource file.
    """
    rc = libdoc(
        str(resource_file),
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
    for root, _, files in os.walk(source_dir):
        root = Path(root)

        for file in files:
            file = Path(file)

            if file.suffix != SUFFIX[target]:
                continue

            # If a library, it should end not start with "test_"
            # and it should end with "_base".
            if target == RobotFile.LIBRARY and (
                not file.stem.endswith("_base")
                or file.stem.startswith("test_")
            ):
                continue

            robot_file = root / file
            input_json_file = docs_ref_dir / file.parent / f"{file.stem}.json"
            output_md_file = (
                docs_ref_dir / f"{target.name.lower()}-{file.stem}.md"
            )

            try:
                if target == RobotFile.RESOURCE:
                    generate_libdoc_for_resources(robot_file, input_json_file)
                elif target == RobotFile.LIBRARY:
                    generate_libdoc_for_libraries(robot_file, input_json_file)
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

        source_dir = repo_root / PACKAGE[target]
        target_dir = docs_dir / Path("reference/rf_libraries")

        if not target_dir.exists():
            os.makedirs(target_dir)

        generate_markdown(target, source_dir, target_dir)


if __name__ == "__main__":
    main()
