import random
from itertools import chain
from unittest.mock import ANY, call, patch

import pytest

from yarf.lib.wayland import get_memfd

from .fixtures import mock_pwc  # noqa: F401


@pytest.fixture(autouse=True)
def mock_memfd(mock_pwc):  # noqa: F811
    with patch("os.memfd_create") as m:
        mock_pwc.attach_mock(m, "memfd_create")
        m.return_value = random.randint(0, 10)
        yield m


@pytest.fixture(autouse=True)
def mock_ctypes():  # noqa: F811
    with patch("yarf.lib.wayland.ctypes") as m:
        yield m


@pytest.fixture(autouse=True)
def mock_getpid():
    with patch("os.getpid") as m:
        yield m


class TestShmOpen:
    def test_get_memfd(self, mock_memfd):
        """
        Returns the `memfd_create` result.
        """
        assert get_memfd() == mock_memfd.return_value

    def test_get_memfd_multiple(self, mock_memfd):
        """
        Uses a different name every time.
        """
        open_count = random.randint(1, 10)
        open_results = tuple(random.randint(1, 10) for _n in range(open_count))
        mock_memfd.side_effect = tuple(open_results)

        assert open_results == tuple(get_memfd() for _n in range(open_count))

        assert (
            len(set(c.args[0] for c in mock_memfd.call_args_list))
            == open_count
        ), "`mock_memfd` reused the same name multiple times"

        mock_memfd.assert_has_calls(
            chain.from_iterable((call(ANY, ANY),) for n in range(open_count))
        )

    def test_memfd_create_error(self, mock_memfd):
        """
        Raises on memfd create error.
        """
        mock_memfd.return_value = -1

        with pytest.raises(AssertionError, match="creating memfd"):
            get_memfd()
