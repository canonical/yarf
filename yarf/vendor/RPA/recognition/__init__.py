# Recognition modules - OCR and template matching

from . import ocr, templates, utils
from .templates import ImageNotFoundError

__all__ = ["ocr", "templates", "utils", "ImageNotFoundError"]
