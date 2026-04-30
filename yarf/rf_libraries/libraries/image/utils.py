"""
Image logging keyword for Robot Framework.
"""

from PIL import Image, ImageDraw
from robot.api import logger
from robot.api.deco import keyword

from yarf.lib.images.utils import to_base64
from yarf.vendor.RPA.Images import to_image


@keyword
def log_image(image: Image.Image | str, msg: str = "") -> None:
    """
    Log an image.

    Args:
        image: Image to log
        msg: Message to log with the image
    """
    pil_image = to_image(image)
    image_string = (
        f"{msg}<br />"
        '<img style="max-width: 100%" src="data:image/png;base64,'
        f'{to_base64(pil_image)}" />'
    )
    logger.info(image_string, html=True)


def normalize_point(point: list) -> list[float]:
    """
    Normalize a point to proportional screen coordinates.

    Args:
        point: A point as [x, y] on a 1000x1000 grid

    Returns:
        The point as normalized ``[x, y]`` coordinates.

    Raises:
        ValueError: If the point is not valid.
    """
    if len(point) != 2:
        raise ValueError("Point must contain exactly two coordinates.")

    try:
        x = float(point[0])
        y = float(point[1])
    except (TypeError, ValueError) as exc:
        raise ValueError("Point coordinates must be numeric.") from exc

    if not 0 <= x <= 1000 or not 0 <= y <= 1000:
        raise ValueError("Point coordinates must be inside the screen.")

    point = [x / 1000, y / 1000]
    return point


def draw_point_on_image(
    image: Image.Image | str,
    point: list[float] | list[int],
    label: str | None = None,
    size: int = 10,
) -> Image.Image:
    """
    Draw a highlighted point marker on a copy of an image.

    Args:
        image: Pillow image to annotate.
        point: Point in image or relative coordinates to draw
        label: Optional text label to draw near the marker.
        size: Size of the marker.

    Returns:
        Annotated image copy.

    Raises:
        ValueError: If the point is not valid.
    """
    image = to_image(image)
    
    if len(point) != 2:
        raise ValueError("Point must contain exactly two coordinates.")

    x, y = point

    # Check if the coordinates are relative (between 0 and 1) and convert to
    # absolute if so
    if 0 <= x <= 1 and 0 <= y <= 1:
        width, height = image.size
        x = round(x * width)
        y = round(y * height)

    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)

    draw.line([(x - size, y), (x + size, y)], fill="red", width=2)
    draw.line([(x, y - size), (x, y + size)], fill="red", width=2)

    if label:
        draw.text(
            (x + size + 4, max(0, y - size - 4)),
            label,
            fill="red",
            font_size=size * 2,
        )

    return annotated
