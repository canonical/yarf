from unittest.mock import patch

import pytest

from yarf.errors.yarf_errors import YARFExitCode
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

    @pytest.mark.asyncio
    async def test_safe_connect(self) -> None:
        vnc = Vnc()
        with patch("yarf.rf_libraries.libraries.vnc.connect"):
            async with vnc.safe_connect() as client:
                assert client is not None

    @pytest.mark.asyncio
    async def test_safe_connect_error(self) -> None:
        vnc = Vnc()
        with pytest.raises(SystemExit) as exc_info:
            async with vnc.safe_connect():
                pass
        assert exc_info.value.code == YARFExitCode.CONNECTION_ERROR
