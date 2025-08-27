"""
Vendored RPA Framework modules

This package contains vendored code from the RPAFramework project, specifically
the modules needed for OCR and template matching functionality.

Original Project Information:
- Repository: https://github.com/robocorp/rpaframework
- Version: 29.0.0
- License: Apache License 2.0
- Copyright: Robocorp Technologies, Inc.

Included Modules:
- core.geometry: Region and Point classes for geometric operations
- Images: Basic image manipulation and template matching
- recognition.ocr: OCR functionality using pytesseract
- recognition.templates: Template matching using OpenCV
- recognition.utils: Image conversion and utility functions

This vendored version provides minimal OCR and template matching functionality
without the full RPAFramework dependency tree. Files have been modified to:
- Use relative imports within the vendor package
- Remove dependencies on unused RPAFramework modules
- Maintain compatibility with existing code

License:
This vendored code is distributed under the Apache License 2.0.
See the LICENSE file in this directory for the full license text.

Modifications:
All modifications to the original source code are documented in the NOTICE file.
"""

from . import Images
from . import core
from . import recognition

# Expose commonly used classes at package level
from .Images import Images, Region, to_image, ImageNotFoundError # type: ignore[no-redef]
from .core.geometry import Region, to_region

__version__ = "29.0.0-vendored"
__author__ = "Robocorp Technologies, Inc. (original), Canonical Ltd. (vendored)"
__license__ = "Apache License 2.0"
__repository__ = "https://github.com/robocorp/rpaframework"

__all__ = [
    "Images", 
    "Region", 
    "to_image", 
    "to_region",
    "ImageNotFoundError",
    "core",
    "recognition",
]
