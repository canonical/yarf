from unittest.mock import patch

import pytest
from robot.errors import VariableError

from yarf.vendor.robotframework_stacktrace import (
    Kind,
    RobotStackTracer,
    StackElement,
)


@pytest.fixture
def mock_bi():
    with patch("yarf.vendor.robotframework_stacktrace.bi") as bi:
        bi.replace_variables.side_effect = lambda arg: arg
        yield bi


@pytest.fixture
def tracer():
    tracer = RobotStackTracer()
    tracer.start_suite("Suite", {"source": "/suite.robot"})
    tracer.start_test("Test", {"lineno": 3})
    return tracer


def kw_attrs(kwname: str, status: str = "PASS", **extra) -> dict:
    return {"kwname": kwname, "args": [], "status": status, **extra}


class TestStackElement:
    def test_resolve_args(self, mock_bi):
        """
        Test that only arguments with variables are resolved and errors are
        reported.
        """

        def replace(arg):
            if arg == "${bad}":
                raise VariableError("bad")
            return {"${num}": 5}.get(arg, arg)

        mock_bi.replace_variables.side_effect = replace
        element = StackElement(
            "f", "s", 1, "Keyword", ["plain", "${num}", "${bad}"]
        )

        assert list(element.resolve_args()) == [
            ("${num}", "5 (int)"),
            ("${bad}", "<Unable to define variable value>"),
        ]

    def test_defaults(self):
        """
        Test the default arguments and kind.
        """
        element = StackElement("f", "s", 1, "Keyword")
        assert element.args == []
        assert element.kind == Kind.Keyword


class TestRobotStackTracer:
    def test_imports(self):
        """
        Test that library and resource sources are tracked.
        """
        tracer = RobotStackTracer()
        tracer.library_import("Lib", {"source": "/lib.py"})
        tracer.resource_import("Res", {"source": "/res.resource"})
        assert tracer.lib_files == {"Lib": "/lib.py", "Res": "/res.resource"}

    def test_start_test(self, tracer):
        """
        Test that starting a test resets the stack trace.
        """
        assert len(tracer.StackTrace) == 1
        test = tracer.StackTrace[0]
        assert (test.file, test.source, test.lineno, test.name) == (
            "/suite.robot",
            "/suite.robot",
            3,
            "Test",
        )
        assert test.kind == Kind.Test

    def test_start_keyword_sources(self, tracer):
        """
        Test that keyword sources fall back to the caller and library file.
        """
        tracer.library_import("Lib", {"source": "/lib.py"})
        tracer.start_keyword("Lib.Kw", kw_attrs("Kw", libname="Lib"))
        tracer.start_keyword(
            "Inner", kw_attrs("Inner", source="/res.resource", lineno=7)
        )

        outer, inner = tracer.StackTrace[1:]
        assert (outer.file, outer.source, outer.lineno) == (
            "/lib.py",
            "/suite.robot",
            None,
        )
        assert (inner.file, inner.source, inner.lineno) == (
            "/res.resource",
            "/res.resource",
            7,
        )

    def test_start_keyword_without_test(self):
        """
        Test that suite-level keywords use the suite source.
        """
        tracer = RobotStackTracer()
        tracer.start_suite("Suite", {"source": "/suite.robot"})
        tracer.start_keyword("Setup", kw_attrs("Setup"))
        assert tracer.StackTrace[0].source == "/suite.robot"

    def test_fix_source(self, tmp_path):
        """
        Test that suite directories point to their init file.
        """
        with_init = tmp_path / "with_init"
        with_init.mkdir()
        (with_init / "__init__.robot").touch()
        without_init = tmp_path / "without_init"
        without_init.mkdir()

        tracer = RobotStackTracer()
        assert tracer.fix_source(str(with_init)) == str(
            with_init / "__init__.robot"
        )
        assert tracer.fix_source(str(without_init)) == str(without_init)
        assert tracer.fix_source(None) is None

    def test_failure_printed_once(self, tracer, mock_bi, capsys):
        """
        Test that a failure is printed at the deepest keyword only.
        """
        tracer.start_keyword(
            "Outer", {**kw_attrs("Outer"), "args": ["${x}"], "lineno": 5}
        )
        tracer.start_keyword("Inner", kw_attrs("Inner"))
        mock_bi.replace_variables.side_effect = lambda arg: 1

        tracer.end_keyword("Inner", kw_attrs("Inner", "FAIL"))
        tracer.end_keyword("Outer", kw_attrs("Outer", "FAIL"))

        output = capsys.readouterr().out
        assert output.count("Traceback (most recent call last):") == 1
        assert "File  /suite.robot:3" in output
        assert "T:  Test" in output
        assert "File  /suite.robot:5" in output
        assert "Outer    ${x}" in output
        assert "|  ${x} = 1 (int)" in output
        assert "File  /suite.robot:0" in output
        assert len(tracer.StackTrace) == 1

    def test_failure_muted(self, tracer, capsys):
        """
        Test that failures inside muting keywords are not printed.
        """
        muting = "Run Keyword And Ignore Error"
        tracer.start_keyword(muting, kw_attrs(muting))
        tracer.start_keyword("Inner", kw_attrs("Inner"))

        tracer.end_keyword("Inner", kw_attrs("Inner", "FAIL"))
        assert tracer.mutings == [muting]
        tracer.end_keyword(muting, kw_attrs(muting))

        assert tracer.mutings == []
        assert capsys.readouterr().out == ""

    def test_end_test_and_suite(self, tracer):
        """
        Test that ending a test and suite clears the traces.
        """
        tracer.end_test("Test", {})
        tracer.end_suite("Suite", {})
        assert tracer.StackTrace == []
        assert tracer.SuiteTrace == []
