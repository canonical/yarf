"""
Wait until the VM on VNC display :0 shows the desktop.

The boot menu and splash screen are mostly black, so the desktop is
assumed to be up once less than 30% of the screen is near-black. A
screenshot is saved to the path given as the first argument.
"""

import asyncio
import sys
import time

from PIL import Image

from yarf.vendor.asyncvnc import connect

TIMEOUT = 900
POLL_INTERVAL = 5
# Extra time for the session to start its apps (e.g. the installer window)
SETTLE_TIME = 30


async def dark_fraction(screenshot_path: str) -> float:
    """
    Take a screenshot and measure how much of it is near-black.

    Args:
        screenshot_path: Where to save the screenshot.

    Returns:
        The fraction of near-black pixels.
    """
    async with connect("localhost", 5900) as client:
        pixels = await client.screenshot()
    Image.fromarray(pixels).convert("RGB").save(screenshot_path)
    return float((pixels[..., :3].sum(-1) < 30).mean())


async def main(screenshot_path: str) -> int:
    """
    Poll the screen until the desktop is up or the timeout expires.

    Args:
        screenshot_path: Where to save the last screenshot.

    Returns:
        The exit code: 0 if the desktop is up, 1 on timeout.
    """
    start = time.monotonic()
    while time.monotonic() - start < TIMEOUT:
        try:
            dark = await dark_fraction(screenshot_path)
        except OSError as error:
            print(f"VNC not ready: {error}")
        else:
            if dark < 0.3:
                await asyncio.sleep(SETTLE_TIME)
                await dark_fraction(screenshot_path)
                print(f"Desktop up after {time.monotonic() - start:.0f}s")
                return 0
        await asyncio.sleep(POLL_INTERVAL)
    print(f"Desktop not up after {TIMEOUT}s")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1])))
