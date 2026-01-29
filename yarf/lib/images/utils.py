from typing import Any, Optional

from yarf.vendor.RPA import RGB


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
