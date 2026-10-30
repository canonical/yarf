"""
Run `yarf mcp` as a subprocess, speaking the protocol over its real stdio.

This is how an LLM client uses it, and the only way to check that
nothing but the protocol reaches the standard output of the server.
"""

import asyncio
import os
import socket
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

TIMEOUT = 180


def unused_vnc_port() -> int:
    """
    Get a VNC port number nothing is listening on.

    Returns:
        The number to give in `VNC_PORT`, which is relative to 5900.
    """
    with socket.socket() as sock:
        sock.bind(("localhost", 0))
        return sock.getsockname()[1] - 5900


@pytest.mark.asyncio
async def test_serves_over_stdio(tmp_path: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "yarf.main",
            "mcp",
            "--platform",
            "Vnc",
            "--outdir",
            str(tmp_path),
        ],
        # No VNC server is listening there, the server has to cope with that
        env={
            **os.environ,
            "VNC_HOST": "localhost",
            "VNC_PORT": str(unused_vnc_port()),
        },
    )

    async def session() -> dict[str, str]:
        async with Client(params) as client:
            tools = await client.list_tools()
            found = await client.call_tool(
                "search_keywords", {"query": "click"}
            )
            blocked = await client.call_tool(
                "run_keyword", {"keyword": "Evaluate", "args": ["1+1"]}
            )
            offline = await client.call_tool("check_connection", {})
        return {
            "tools": {tool.name for tool in tools.tools},
            "found": "\n".join(c.text for c in found.content),
            "blocked": blocked,
            "offline": offline,
        }

    result = await asyncio.wait_for(session(), TIMEOUT)

    assert "screenshot" in result["tools"]
    assert "Click ${button} Button On ${destination}" in result["found"]
    assert result["blocked"].is_error
    assert "not allowed" in result["blocked"].content[0].text
    assert result["offline"].is_error
    assert (
        "Failed to connect to VNC server" in result["offline"].content[0].text
    )
    # Written as it goes, unlike the Robot Framework log made on shutdown,
    # which clients may not wait for
    assert (tmp_path / "events.jsonl").exists()
