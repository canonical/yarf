"""
Keyword lookup and execution helpers.
"""

import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from robot.libdocpkg.model import KeywordDoc, LibraryDoc
from robot.libraries.BuiltIn import BuiltIn
from robot.parsing import get_model
from robot.running import ResourceFile, TestCase, TestSuite

from .robotlib import (
    ImportedLibraryDocBuilder,
    ImportedResourceDocBuilder,
    Library,
    get_libs,
)

_lib_docs_cache: dict[str, LibraryDoc] = {}
_temp_resources: list[str] = []


def get_lib_keywords(library: Library) -> list[KeywordDoc]:
    """
    Get the keywords of an imported library or resource.

    Args:
        library: the imported library or resource

    Returns:
        the keyword documentations
    """
    if library.name not in _lib_docs_cache:
        if isinstance(library, ResourceFile):
            libdoc = ImportedResourceDocBuilder(doc_format=None).build(library)
        else:
            libdoc = ImportedLibraryDocBuilder(doc_format=None).build(library)
        _lib_docs_cache[library.name] = libdoc
    return _lib_docs_cache[library.name].keywords


def get_keywords() -> Iterator[KeywordDoc]:
    """
    Get the keywords of all the imported libraries and resources.

    Yields:
        the keyword documentations
    """
    for lib in get_libs():
        yield from get_lib_keywords(lib)


def normalize_kw(keyword_name: str) -> str:
    """
    Normalize a keyword name for comparison.

    Args:
        keyword_name: the keyword name

    Returns:
        the lowercase name without spaces and underscores
    """
    return keyword_name.lower().replace("_", "").replace(" ", "")


def find_keyword(keyword_name: str) -> list[KeywordDoc]:
    """
    Find the keywords with the given name in all libraries.

    Args:
        keyword_name: the keyword name

    Returns:
        the matching keyword documentations
    """
    name = normalize_kw(keyword_name)
    return [
        keyword
        for keyword in get_keywords()
        if normalize_kw(keyword.name) == name
    ]


def get_test_body_from_string(command: str) -> TestCase:
    """
    Parse keyword calls as the body of a test.

    Args:
        command: one or more lines of keyword calls

    Returns:
        the parsed test
    """
    command = "\n  ".join(command.split("\n"))
    suite_str = f"""
*** Test Cases ***
Fake Test
  {command}
"""
    suite = TestSuite.from_model(get_model(suite_str))
    return suite.tests[0]


def import_resource_from_string(command: str) -> None:
    """
    Import resource file content, giving precedence to its keywords.

    Args:
        command: content of a resource file
    """
    res_file = tempfile.NamedTemporaryFile(
        mode="w",
        prefix="RobotDebug_keywords_",
        suffix=".resource",
        encoding="utf-8",
        delete=False,
    )
    resource_path = Path(res_file.name)
    try:
        with res_file:
            res_file.write(command)
        _temp_resources.insert(0, resource_path.stem)
        BuiltIn().import_resource(resource_path.resolve().as_posix())
        BuiltIn().set_library_search_order(*_temp_resources)
    finally:
        resource_path.unlink(missing_ok=True)


def get_assignments(body_elem: Any) -> Iterator[str]:
    """
    Get the variables assigned in a test body element.

    Args:
        body_elem: test, keyword call, control structure or VAR statement

    Yields:
        the names of the assigned variables
    """
    if body_elem.type == "VAR":
        yield body_elem.name
    yield from getattr(body_elem, "assign", ())
    for child in getattr(body_elem, "body", ()):
        yield from get_assignments(child)
