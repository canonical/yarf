from PIL import Image, ImageDraw

from yarf.rf_libraries.libraries.image.windows import find_windows
from yarf.vendor.RPA.core.geometry import Region


def screen(*windows: tuple[int, int, int, int]) -> Image.Image:
    image = Image.new("RGB", (800, 600), "black")
    draw = ImageDraw.Draw(image)
    for window in windows:
        draw.rectangle(window, fill="white")
    return image


def close_to(found: Region, expected: Region, tolerance: int = 4) -> bool:
    return all(
        abs(a - b) <= tolerance
        for a, b in zip(found.as_tuple(), expected.as_tuple())
    )


class TestFindWindows:
    def test_finds_window(self):
        windows = find_windows(screen((100, 100, 400, 300)))

        assert len(windows) == 1
        assert close_to(windows[0], Region(100, 100, 400, 300))

    def test_largest_first(self):
        windows = find_windows(
            screen((50, 50, 300, 250), (400, 100, 750, 550))
        )

        assert len(windows) == 2
        assert close_to(windows[0], Region(400, 100, 750, 550))
        assert close_to(windows[1], Region(50, 50, 300, 250))

    def test_ignores_small_and_full_screen(self):
        # A 50px button is too small; the whole screen is not a window.
        assert find_windows(screen((100, 100, 150, 150))) == []
        assert find_windows(screen((0, 0, 799, 599))) == []

    def test_blank_screen(self):
        assert find_windows(screen()) == []
