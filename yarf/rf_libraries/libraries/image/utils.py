"""
Image logging keyword for Robot Framework.
"""

import os
import uuid

from PIL import Image, ImageDraw
from robot.api import logger
from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from yarf.lib.images.utils import to_base64
from yarf.vendor.RPA.Images import to_image


def _get_images_dir() -> str | None:
    """
    Return the configured image output directory, creating it if needed.

    The directory is read from the Robot Framework variable ``${YARF_IMAGE_DIR}``.
    Returns ``None`` when the variable is not set or when called outside a
    Robot Framework run (e.g. in unit tests).

    Returns:
        Path to the image output directory, or ``None`` if not configured.
    """
    try:
        images_dir = BuiltIn().get_variable_value("${YARF_IMAGE_DIR}")
    except RobotNotRunningError:
        return None
    if not images_dir:
        return None
    os.makedirs(images_dir, exist_ok=True)
    return images_dir


@keyword
def log_image(image: Image.Image | str, msg: str = "") -> None:
    """
    Log an image.

    When the Robot Framework variable ``${YARF_IMAGE_DIR}`` is set, the image
    is saved as a WebP file in that directory and referenced by a relative URL
    from the output directory, which keeps the HTML log small and lets the
    browser load images on demand.  When the variable is not set the image is
    base64-encoded and embedded inline as a fallback.

    Args:
        image: Image to log
        msg: Message to log with the image
    """
    pil_image = to_image(image)
    images_dir = _get_images_dir()

    if images_dir is not None:
        filename = f"{uuid.uuid4().hex}.webp"
        filepath = os.path.join(images_dir, filename)
        pil_image.convert("RGB").save(
            filepath, format="WEBP", quality=80, method=4
        )
        # Build a URL relative to ${OUTPUT_DIR} so it works when log.html and
        # the images/ directory are served from the same location.
        try:
            output_dir = BuiltIn().get_variable_value("${OUTPUT_DIR}")
        except RobotNotRunningError:
            output_dir = None
        if output_dir:
            src = os.path.relpath(filepath, output_dir)
        else:
            src = filepath
        image_string = (
            f'{msg}<br /><img style="max-width: 100%" src="{src}" />'
        )
    else:
        image_string = (
            f"{msg}<br />"
            '<img style="max-width: 100%" src="data:image/webp;base64,'
            f'{to_base64(pil_image, format="WEBP")}" />'
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
