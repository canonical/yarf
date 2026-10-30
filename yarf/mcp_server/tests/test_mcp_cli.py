import io
import sys
from unittest.mock import MagicMock, Mock

import pytest

from yarf.mcp_server import cli
from yarf.mcp_server.McpHost import run_stdio
from yarf.rf_libraries.libraries import SUPPORTED_PLATFORMS
from yarf.rf_libraries.libraries.vnc import Vnc


@pytest.fixture(autouse=True)
def vnc_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(SUPPORTED_PLATFORMS, "Vnc", Vnc)


class TestCli:
    def test_parse_arguments_defaults(self) -> None:
        args = cli.parse_arguments([])

        assert args.platform == "Vnc"
        assert args.log_level == "INFO"
        assert args.outdir is None

    def test_parse_arguments(self, tmp_path) -> None:
        args = cli.parse_arguments(
            ["--platform", "Vnc", "--outdir", str(tmp_path), "--debug"]
        )

        assert args.outdir == str(tmp_path)
        assert args.log_level == "DEBUG"
        assert cli.parse_arguments(["--quiet"]).log_level == "WARNING"

    def test_parse_arguments_unknown_platform(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        with pytest.raises(SystemExit):
            cli.parse_arguments(["--platform", "Nope"])

        assert "invalid choice" in capsys.readouterr().err

    def test_build_suite(self) -> None:
        suite = cli.build_suite(
            "Vnc", ["/lib/Hid.py", "/lib/VideoInput.py"], ["/res/kvm.resource"]
        )

        assert suite.name == "Vnc MCP Server"
        assert [(imp.type, imp.name) for imp in suite.resource.imports] == [
            ("LIBRARY", cli.HOST_LIBRARY),
            ("LIBRARY", "/lib/Hid.py"),
            ("LIBRARY", "/lib/VideoInput.py"),
            ("RESOURCE", "/res/kvm.resource"),
        ]
        (test,) = suite.tests
        assert [step.name for step in test.body] == ["Serve Mcp"]

    def test_main_without_the_sdk(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setattr(
            cli,
            "importlib",
            Mock(util=Mock(find_spec=Mock(return_value=None))),
        )
        build_suite = Mock()
        monkeypatch.setattr(cli, "build_suite", build_suite)

        assert cli.main([]) == 1

        captured = capsys.readouterr()
        assert "pip install yarf[mcp]" in captured.err
        assert captured.out == ""
        build_suite.assert_not_called()


class TestRunStdio:
    def test_uses_the_real_standard_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Robot Framework replaces `sys.stdout` while keywords run, and the MCP
        SDK can't claim the standard output from it.
        """
        server = MagicMock()
        monkeypatch.setattr(sys, "stdout", io.StringIO())
        run = Mock()
        monkeypatch.setattr("yarf.mcp_server.McpHost.anyio.run", run)

        run_stdio(server)

        assert sys.stdout is sys.__stdout__
        run.assert_called_once_with(server.run_stdio_async)
