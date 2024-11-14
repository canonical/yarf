import pytest

from yarf.rf_libraries.libraries.vnc import Vnc, translate


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


class TestHidTranslator:
    @pytest.mark.parametrize(
        "test_input,expected",
        [
            ("LEFT_ALT", "Alt_L"),
            ("RIGHT_ALT", "Alt_R"),
            ("LEFT_CONTROL", "Control_L"),
            ("RIGHT_CONTROL", "Control_R"),
            ("ESCAPE", "Escape"),
            ("F10", "F10"),
            ("ENTER", "Return"),
            ("A", "A"),
        ],
    )
    def test_translations(self, test_input, expected) -> None:
        assert translate(test_input) == expected
