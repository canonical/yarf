from typing import List, Any, Optional

from yarf.vendor.RPA.Images import RGB

def to_RGB(obj: Any) -> Optional["RGB"]:
    """Convert `obj` to instance of RGB."""
    if obj is None or isinstance(obj, RGB):
        return obj
    if isinstance(obj, str):
        obj = obj.split(",")
        return RGB(red=obj[0], green=obj[1], blue=obj[2])
    if isinstance(obj, tuple):
        return RGB(red=obj[0], green=obj[1], blue=obj[2])
    return None

