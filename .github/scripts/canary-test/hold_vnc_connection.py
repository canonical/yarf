"""
Keep one idle client connected to wayvnc until wayvnc closes it.

wayvnc 0.9 stops its screen capture when the last client disconnects and
can fail to start it again for the next client, which makes it exit. YARF
opens a new VNC connection for each action, so an idle client that stays
connected keeps wayvnc from restarting the capture between actions.

Upstream issue: https://github.com/any1/wayvnc/issues/401

Run it with the Python of the YARF snap, which provides the vendored asyncvnc
client.
"""

import asyncio

from yarf.vendor.asyncvnc import connect


async def hold(host: str, port: int) -> None:
    """
    Connect as a shared client and wait until the server closes.

    The client never requests framebuffer updates, so the server sends
    nothing and the read only returns when the connection closes.

    Args:
        host: The VNC server host.
        port: The VNC server port.
    """
    async with connect(host, port) as client:
        await client.reader.read()


if __name__ == "__main__":
    asyncio.run(hold("127.0.0.1", 5900))
