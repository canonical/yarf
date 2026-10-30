"""
Run the Robot Framework helpers inside a real Robot Framework execution.
"""

import io
import textwrap

import robot
from robot.libraries.BuiltIn import BuiltIn

from yarf.vendor.robotframework_debug.debugcmd import ReplCmd, run_command
from yarf.vendor.robotframework_debug.robotkeyword import (
    find_keyword,
    get_lib_keywords,
)
from yarf.vendor.robotframework_debug.robotlib import (
    get_libraries,
    get_libs,
    get_resources,
    match_libs,
)

SUITE = """\
*** Settings ***
Library    {module}.Probe    {history}
Resource    probe.resource

*** Test Cases ***
Probe
    Probe
"""

RESOURCE = """\
*** Keywords ***
Resource Keyword
    [Documentation]    Documented resource keyword.
    No Operation
"""


class Probe:
    """
    Library checking the helpers from within a running test.
    """

    def __init__(self, history: str) -> None:
        self.repl = ReplCmd(history)

    def probe(self) -> None:
        """
        Check the helpers.
        """
        repl = self.repl
        assert run_command(repl, "${TEST NAME}") == [
            ("#", "${TEST NAME} = 'Probe'")
        ]
        assert run_command(repl, "${x}=    Set Variable    1") == [
            ("#", "${x} = '1'")
        ]
        assert repl.last_keyword_exec_time > 0
        assert run_command(repl, "Evaluate    1 + 1") == [("<", "2")]
        assert run_command(repl, "Evaluate    1\nEvaluate    2") == []
        assert run_command(repl, "No Operation") == []
        assert run_command(repl, "VAR    ${y}    2") == [("#", "${y} = '2'")]
        assert run_command(
            repl,
            "FOR    ${i}    IN    a\n    ${z}=    Set Variable    ${i}\nEND",
        ) == [("#", "${i} = 'a'"), ("#", "${z} = 'a'")]
        assert run_command(
            repl, "IF    True\n    ${a}=    Set Variable    1\nEND"
        ) == [("#", "${a} = '1'")]
        assert run_command(
            repl,
            "WHILE    $a == '1'\n    ${a}=    Set Variable    2\nEND",
        ) == [("#", "${a} = '2'")]
        assert run_command(
            repl,
            "TRY\n    ${b}=    Set Variable    3\n"
            "EXCEPT    AS    ${err}\n    No Operation\nEND",
        ) == [("#", "${b} = '3'"), ("#", "${err} = None")]
        assert (
            run_command(
                repl, "TRY\n    Fail    boom\nEXCEPT\n    No Operation\nEND"
            )
            == []
        )
        assert run_command(
            repl, "*** Keywords ***\nProbe Keyword\n    RETURN    42"
        ) == [("i:", "Resource imported.")]
        assert run_command(repl, "Probe Keyword") == [("<", "'42'")]
        assert BuiltIn().get_variable_value("${z}") == "a"

        names = [lib.name for lib in get_libs()]
        assert names == sorted(names)
        assert "BuiltIn" in [lib.name for lib in get_libraries()]
        assert "Reserved" not in names
        assert "probe" in [res.name for res in get_resources()]
        assert [lib.name for lib in match_libs("PROBE")] == ["probe"]

        (resource,) = match_libs("probe")
        keywords = get_lib_keywords(resource)
        assert [kw.name for kw in keywords] == ["Resource Keyword"]
        assert get_lib_keywords(resource) is keywords
        (probe,) = find_keyword("resource_keyword")
        assert probe.doc == "Documented resource keyword."
        assert [kw.name for kw in find_keyword("no operation")] == [
            "No Operation"
        ]
        catalog = repl.get_completer().keywords_catalog
        assert "probe.resourcekeyword" in catalog
        assert "probekeyword" in catalog


def test_in_robot(tmp_path):
    """
    Test the helpers in a real Robot Framework execution.
    """
    (tmp_path / "probe.resource").write_text(RESOURCE)
    suite = tmp_path / "suite.robot"
    suite.write_text(
        SUITE.format(module=__name__, history=tmp_path / "history")
    )
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
