from unittest.mock import MagicMock, patch

import pytest

from yarf.errors.yarf_errors import YARFConnectionError, YARFExitCode
from yarf.rf_libraries.libraries.vnc import Vnc


class TestVnc:
    def test_get_pkg_path(self) -> None:
        assert Vnc.get_pkg_path().endswith("/yarf/rf_libraries/libraries/vnc")

    @pytest.mark.asyncio
    async def test_init(self, monkeypatch) -> None:
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "1")
            m.setenv("VNC_HOST", "localhost")
            _ = Vnc()

    def test_bad_init(self, monkeypatch) -> None:
        with monkeypatch.context() as m:
            m.setenv("VNC_PORT", "3.14159265359")
            m.setenv("VNC_HOST", "localhost")
            with pytest.raises(AssertionError):
                _ = Vnc()

    def test_check_connection(self) -> None:
        vnc = Vnc()
        with patch(
            "yarf.rf_libraries.libraries.vnc.connect",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            with pytest.raises(YARFConnectionError) as exc_info:
                vnc.check_connection()
            assert exc_info.value.exit_code == YARFExitCode.CONNECTION_ERROR

    def test_check_connection_success(self) -> None:
        vnc = Vnc()
        with patch("yarf.rf_libraries.libraries.vnc.connect"):
            vnc.check_connection()

    def test_check_connection_asyncio_running(self) -> None:
        vnc = Vnc()

        def close_coroutine(coroutine, loop):
            coroutine.close()
            return MagicMock()

        with (
            patch("yarf.rf_libraries.libraries.vnc.connect"),
            patch("yarf.rf_libraries.libraries.vnc.asyncio.get_running_loop"),
            patch(
                "yarf.rf_libraries.libraries.vnc.asyncio.run_coroutine_threadsafe",
                side_effect=close_coroutine,
            ),
        ):
            vnc.check_connection()
