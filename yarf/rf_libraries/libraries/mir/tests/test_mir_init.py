from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yarf.errors.yarf_errors import YARFConnectionError
from yarf.rf_libraries.libraries.mir import Mir


class TestMir:
    """
    Test the Mir class.
    """

    def test_get_pkg_path(self) -> None:
        """
        Test whether the "get_pkg_path" method returns the expected path.
        """

        assert Mir.get_pkg_path().endswith("/yarf/rf_libraries/libraries/mir")

    def test_check_connection(self) -> None:
        """
        Test whether the "check_connection" method raises a YARFConnectionError
        when it fails to connect.
        """

        mir = Mir()
        with pytest.raises(YARFConnectionError):
            mir.check_connection()

    def test_check_connection_success(self) -> None:
        """
        Test whether the "check_connection" method does not raise an exception
        when it successfully connects.
        """

        mir = Mir()
        with (
            patch(
                "yarf.rf_libraries.libraries.mir.screencopy.Screencopy.connect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.VirtualPointer.connect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.VirtualKeyboard.connect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.WaylandClient.disconnect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.VirtualPointer.disconnect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.VirtualKeyboard.disconnect",
                new_callable=AsyncMock,
            ),
        ):
            mir.check_connection()

    def test_check_connection_loop_is_running(self) -> None:
        """
        Test whether the "check_connection" method uses the existing event loop
        if it's already running.
        """

        mir = Mir()

        def close_coroutine(coroutine, loop):
            coroutine.close()
            return MagicMock()

        with (
            patch("yarf.rf_libraries.libraries.mir.asyncio.get_running_loop"),
            patch(
                "yarf.rf_libraries.libraries.mir.asyncio.run_coroutine_threadsafe",
                side_effect=close_coroutine,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.screencopy.Screencopy.connect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.VirtualPointer.connect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.VirtualKeyboard.connect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.WaylandClient.disconnect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.VirtualPointer.disconnect",
                new_callable=AsyncMock,
            ),
            patch(
                "yarf.rf_libraries.libraries.mir.VirtualKeyboard.disconnect",
                new_callable=AsyncMock,
            ),
        ):
            mir.check_connection()
