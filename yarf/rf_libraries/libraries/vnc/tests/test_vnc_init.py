import pytest

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
