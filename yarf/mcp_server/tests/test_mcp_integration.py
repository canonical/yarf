"""
Run the MCP server for real, in-process, against a fake platform.

The Robot Framework suite, the host library, the bridge, the session and the
tools are the real ones, and so is `kvm.resource`. Only the platform libraries
are replaced, and the stdio transport is replaced by an in-memory client.
"""

import asyncio
import json
from importlib import metadata
from pathlib import Path
from typing import Any, Callable

import pytest
from mcp import Client

from yarf.errors.yarf_errors import YARFConnectionError
from yarf.mcp_server import cli
from yarf.rf_libraries.libraries import SUPPORTED_PLATFORMS

FAKE_HID = """
import os
from robot.api.deco import keyword, library


def log(*items):
    with open(os.environ["FAKE_PLATFORM_LOG"], "a") as log_file:
        log_file.write(" ".join(str(item) for item in items) + "\\n")


@library
class Hid:
    @keyword
    def type_string(self, string: str):
        log("type", string)

    @keyword
    def keys_combo(self, combo, *keys):
        log("keys", combo, *keys)

    @keyword
    def move_pointer_to_absolute(self, x: int, y: int):
        log("move", x, y)

    @keyword
    def click_pointer_button(self, button: str):
        log("click", button)
"""

FAKE_VIDEO_INPUT = """
from PIL import Image
from robot.api.deco import keyword, library


@library
class VideoInput:
    @keyword
    def grab_screenshot(self):
        image = Image.new("RGB", (64, 48), (10, 10, 10))
        image.paste((250, 250, 250), (8, 8, 24, 24))
        return image

    @keyword
    def match(self, template: str, timeout: int = 10):
        return [{"template": template, "timeout": timeout}]

    @keyword
    def match_text(self, text: str, timeout: int = 10):
        if text == "missing":
            raise ValueError("Timed out looking for 'missing'")
        return [{"text": text}]

    @keyword
    def read_text(self):
        return "hello world"

    @keyword
    def get_text_position(self, text: str, region=None):
        return (10, 20)

    @keyword
    def wait_still_screen(
        self, duration: float = 30.0, still_duration: float = 10.0
    ):
        pass
"""


@pytest.fixture
def platform_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Register a fake platform, and get the file where it logs its actions.
    """
    package = tmp_path / "fake_platform"
    package.mkdir()
    (package / "Hid.py").write_text(FAKE_HID)
    (package / "VideoInput.py").write_text(FAKE_VIDEO_INPUT)
    platform_log = tmp_path / "platform.log"
    monkeypatch.setenv("FAKE_PLATFORM_LOG", str(platform_log))
    monkeypatch.setenv("YARF_LOG_LEVEL", "INFO")

    class FakePlatform:
        connected = True

        @staticmethod
        def get_pkg_path() -> str:
            return str(package)

        def check_connection(self) -> None:
            if not FakePlatform.connected:
                raise YARFConnectionError("The fake platform is down")

    monkeypatch.setitem(SUPPORTED_PLATFORMS, "Fake", FakePlatform)
    return platform_log


def serve_with(
    monkeypatch: pytest.MonkeyPatch,
    scenario: Callable[[Client, Callable[..., Any]], Any],
) -> dict[str, Any]:
    """
    Replace the stdio transport with an in-memory client running a scenario.

    Args:
        monkeypatch: pytest's monkeypatch fixture
        scenario: coroutine function receiving the client, and a helper that
            calls a tool and returns its result

    Returns:
        The results of the scenario
    """
    results: dict[str, Any] = {}

    def run_stdio(server) -> None:
        async def drive() -> None:
            async with Client(server) as client:

                async def call(tool: str, **arguments: Any):
                    result = await client.call_tool(tool, arguments)
                    results[tool] = result
                    return result

                await scenario(client, call)

        asyncio.run(drive())

    monkeypatch.setattr("yarf.mcp_server.McpHost.run_stdio", run_stdio)
    return results


def text_of(result) -> str:
    return "\n".join(c.text for c in result.content if c.type == "text")


class TestMcpServer:
    def test_exploration_session(
        self,
        tmp_path: Path,
        platform_log: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        outdir = tmp_path / "out"
        seen: dict[str, Any] = {}

        async def scenario(client: Client, call) -> None:
            tools = await client.list_tools()
            seen["tools"] = {tool.name for tool in tools.tools}
            seen["server"] = client.server_info

            seen["connection"] = text_of(await call("check_connection"))
            seen["screenshot"] = await call("screenshot")
            seen["template"] = text_of(
                await call(
                    "save_template",
                    name="white",
                    x=8,
                    y=8,
                    width=16,
                    height=16,
                )
            )
            seen["click_on"] = text_of(await call("click_on", target="Save"))
            seen["click_at"] = text_of(await call("click_at", x=5, y=6))
            seen["type"] = text_of(await call("type_text", text="4+2=${x}"))
            seen["keys"] = text_of(
                await call("press_keys", keys=["Alt_L", "F4"])
            )
            seen["match_text"] = text_of(await call("match_text", text="ok"))
            seen["match_template"] = text_of(
                await call("match_template", template="a.png", timeout=2)
            )
            seen["read_text"] = text_of(await call("read_text"))
            seen["still"] = text_of(await call("wait_still_screen"))
            seen["search"] = (
                await call("search_keywords", query="click")
            ).structured_content
            seen["doc"] = text_of(
                await call("get_keyword_doc", keyword="Match Text")
            )
            seen["blocked_doc"] = await call(
                "get_keyword_doc", keyword="Evaluate"
            )
            seen["run"] = text_of(
                await call("run_keyword", keyword="Sleep", args=["0s"])
            )
            seen["failure"] = await call("match_text", text="missing")
            seen["blocked"] = await call(
                "run_keyword", keyword="Evaluate", args=["1+1"]
            )
            seen["injection"] = await call(
                "run_keyword", keyword="Log", args=["${{1+1}}"]
            )
            seen["unknown"] = await call(
                "run_keyword", keyword="No Such Thing"
            )
            seen["bad_region"] = await call(
                "save_template", name="big", x=0, y=0, width=999, height=1
            )
            seen["history"] = text_of(await call("get_history", limit=100))
            seen["export"] = text_of(
                await call("export_suite", name="Explored scenario")
            )

        serve_with(monkeypatch, scenario)

        return_code = cli.main(["--platform", "Fake", "--outdir", str(outdir)])

        assert return_code == 0
        assert {
            "screenshot",
            "click_on",
            "click_at",
            "type_text",
            "press_keys",
            "match_template",
            "match_text",
            "read_text",
            "wait_still_screen",
            "save_template",
            "search_keywords",
            "get_keyword_doc",
            "run_keyword",
            "get_history",
            "export_suite",
            "check_connection",
        } == seen["tools"]
        assert seen["server"].name == "yarf"
        assert seen["server"].version == metadata.version("yarf")
        assert seen["connection"] == "Connected."
        assert seen["screenshot"].content[0].type == "image"
        assert seen["screenshot"].content[0].mime_type == "image/png"
        assert (outdir / "templates" / "white.png").exists()
        assert seen["template"].startswith("Saved template")

        # What the fake platform received
        assert platform_log.read_text().splitlines() == [
            "move 10 20",
            "click LEFT",
            "move 5 6",
            "click LEFT",
            "type 4+2=${x}",
            "keys Alt_L F4",
        ]
        assert seen["match_text"] == "[{'text': 'ok'}]"
        assert seen["read_text"] == "'hello world'"
        assert seen["run"] == "None"

        # Discovery only shows what can be run
        assert any(
            "Click ${button} Button On ${destination}" in line
            for line in seen["search"]["result"]
        )
        assert seen["doc"].startswith("VideoInput.Match Text(")
        assert seen["blocked_doc"].is_error
        assert "no allowed keyword named 'Evaluate'" in text_of(
            seen["blocked_doc"]
        )

        # Failures are reported, and don't stop the session
        assert seen["failure"].is_error
        assert "Timed out looking for 'missing'" in text_of(seen["failure"])
        assert seen["blocked"].is_error
        assert "not allowed" in text_of(seen["blocked"])
        assert seen["injection"].is_error
        assert "not allowed" in text_of(seen["injection"])
        assert seen["unknown"].is_error
        assert "No keyword with name 'No Such Thing' found" in text_of(
            seen["unknown"]
        )
        assert seen["bad_region"].is_error
        assert "not within" in text_of(seen["bad_region"])

        # The event cache knows everything that happened
        assert "FAIL Match Text    missing" in seen["history"]
        assert "[screen " in seen["history"]
        events = [
            json.loads(line)
            for line in (outdir / "events.jsonl").read_text().splitlines()
        ]
        assert events[0]["keyword"] == "Grab Screenshot"
        assert (outdir / "log.html").exists()

        # The exported suite replays the successful actions
        suite = (
            outdir
            / "exports"
            / "Explored_scenario"
            / "Explored_scenario.robot"
        )
        assert seen["export"] == f"Exported to {suite}"
        steps = [
            line.strip()
            for line in suite.read_text().splitlines()
            if line.startswith("    ")
        ]
        assert steps == [
            "Click LEFT Button On Save",
            "Move Pointer To (5, 6)",
            "Click LEFT Button",
            "Type String    4+2\\=\\${x}",
            "Keys Combo    Alt_L    F4",
            "Match Text    ok    10",
            "Match    a.png    2",
            "Wait Still Screen    30.0    10.0",
            "Sleep    0s",
        ]

    def test_empty_history(
        self,
        tmp_path: Path,
        platform_log: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        seen: dict[str, Any] = {}

        async def scenario(client: Client, call) -> None:
            seen["history"] = text_of(await call("get_history"))
            seen["export"] = await call("export_suite", name="Nothing")

        serve_with(monkeypatch, scenario)

        assert cli.main(["--platform", "Fake", "--outdir", str(tmp_path)]) == 0
        assert seen["history"] == "No events yet."
        assert seen["export"].is_error
        assert "no steps" in text_of(seen["export"])

    def test_keeps_serving_when_platform_is_down(
        self,
        tmp_path: Path,
        platform_log: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        SUPPORTED_PLATFORMS["Fake"].connected = False
        seen: dict[str, Any] = {}

        async def scenario(client: Client, call) -> None:
            seen["connection"] = await call("check_connection")

        serve_with(monkeypatch, scenario)

        assert cli.main(["--platform", "Fake", "--outdir", str(tmp_path)]) == 0
        assert "The fake platform is down" in caplog.text
        assert seen["connection"].is_error
        assert "The fake platform is down" in text_of(seen["connection"])

    def test_fails_when_the_server_crashes(
        self,
        tmp_path: Path,
        platform_log: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def run_stdio(server) -> None:
            raise OSError("the transport broke")

        monkeypatch.setattr("yarf.mcp_server.McpHost.run_stdio", run_stdio)

        assert cli.main(["--platform", "Fake", "--outdir", str(tmp_path)]) == 1
