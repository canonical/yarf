import base64
from io import BytesIO
from typing import Any, Optional

from PIL import Image

from yarf.vendor.RPA.Images import RGB


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


def to_RGB(obj: Any) -> Optional["RGB"]:
    """
    Convert `obj` to instance of RGB.

    Args:
        obj: a RGB, 3-items tuple (r,g,b) or None object.
    Returns:
        An instance of RGB or None.
    """
    if isinstance(obj, RGB):
        return obj
    if isinstance(obj, str):
        obj = obj.split(",")
        return RGB(red=int(obj[0]), green=int(obj[1]), blue=int(obj[2]))
    if isinstance(obj, tuple):
        return RGB(red=obj[0], green=obj[1], blue=obj[2])
    return None
