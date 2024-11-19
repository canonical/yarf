import sys
from typing import Generator

import pytest
from pyfakefs.fake_filesystem_unittest import FakeFilesystem, Patcher


@pytest.fixture
def fs() -> Generator[FakeFilesystem, None, None]:
    """
    A custom FakeFileSystem working around pyfakefs not able to deal with some
    libraries.
    """
    xkb_lib = None
    if "xkbcommon._ffi.lib" in sys.modules:
        xkb_lib = sys.modules.pop("xkbcommon._ffi.lib")

    with Patcher() as patcher:
        if xkb_lib is not None:
            sys.modules["xkbcommon._ffi.lib"] = xkb_lib
        yield patcher.fs
