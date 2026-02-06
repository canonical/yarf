from PIL import Image
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
