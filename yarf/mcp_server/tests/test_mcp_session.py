import io

from PIL import Image

from yarf.mcp_server.session import MAX_DETAIL_LENGTH, describe, png_bytes


class TestDescribe:
    def test_values(self) -> None:
        assert describe(None) == "None"
        assert describe("text") == "'text'"
        assert describe({"a": 1}) == "{'a': 1}"

    def test_images_are_not_dumped(self) -> None:
        assert describe(Image.new("RGB", (4, 3))) == "<image 4x3>"

    def test_collections_describe_their_items(self) -> None:
        image = Image.new("RGB", (4, 3))
        assert describe(([1, "a"], image)) == "[[1, 'a'], <image 4x3>]"

    def test_long_values_are_truncated(self) -> None:
        text = describe("x" * (MAX_DETAIL_LENGTH * 2))
        assert text.endswith("... (truncated)")
        assert len(text) < MAX_DETAIL_LENGTH + 50


def test_png_bytes() -> None:
    image = Image.new("RGB", (4, 3), (1, 2, 3))

    decoded = Image.open(io.BytesIO(png_bytes(image)))

    assert decoded.format == "PNG"
    assert decoded.size == (4, 3)
    assert decoded.getpixel((0, 0)) == (1, 2, 3)
