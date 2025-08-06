# Recognition modules - OCR and template matching

from . import ocr
from . import templates
from . import utils
from .templates import ImageNotFoundError

__all__ = ["ocr", "templates", "utils", "ImageNotFoundError"]
