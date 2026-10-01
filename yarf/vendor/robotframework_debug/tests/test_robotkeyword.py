"""
Build the keyword documentation inside a real Robot Framework execution.
"""

import io
import textwrap

import robot

from yarf.vendor.robotframework_debug.robotkeyword import get_keywords

SUITE = """\
*** Settings ***
Library    {module}.Probe
Resource    probe.resource

*** Test Cases ***
Probe
    Probe
"""

RESOURCE = """\
*** Keywords ***
Resource Keyword
    No Operation
"""


class Probe:
    """
    Library checking the keyword documentation from within a test.
    """

    def probe(self) -> None:
        """
        Check that library and resource keywords are documented.
        """
        names = [keyword.name for keyword in get_keywords()]
        assert "No Operation" in names
        assert "Resource Keyword" in names


def test_get_keywords(tmp_path):
    """
    Test that the keywords of libraries and resources can be listed.
    """
    (tmp_path / "probe.resource").write_text(RESOURCE)
    suite = tmp_path / "suite.robot"
    suite.write_text(SUITE.format(module=__name__))
    stdout = io.StringIO()

    rc = robot.run(
        suite,
        output=None,
        log=None,
        report=None,
        stdout=stdout,
        stderr=stdout,
    )

    assert rc == 0, textwrap.indent(stdout.getvalue(), "  ")
