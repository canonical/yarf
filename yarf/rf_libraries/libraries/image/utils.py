import base64
from io import BytesIO

from PIL import Image
from robot.api import logger
from robot.api.deco import keyword

from yarf.vendor.RPA.Images import to_image


def to_base64(image: Image.Image) -> str:
    """
    Convert Pillow Image to b64.

    Args:
        image: Image to convert

    Returns:
        Image as base64 string
    """

    im_file = BytesIO()
    image = image.convert("RGB")
    image.save(im_file, format="PNG")
    im_bytes = im_file.getvalue()  # im_bytes: image in binary format.
    im_b64 = base64.b64encode(im_bytes)
    return im_b64.decode()


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
