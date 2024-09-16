from unittest.mock import AsyncMock, call, patch

import pytest

from yarf.robot.libraries.hid_base import HidBase, Size


@pytest.fixture
def mock_sleep():
    with patch("asyncio.sleep", AsyncMock()) as mock:
        yield mock


class StubHid(HidBase):
    async def click_pointer_button(self, *args):
        pass

    async def keys_combo(self, *args):
        pass

    async def type_string(self, *args):
        pass

    async def _get_display_size(self):
        pass

    async def _move_pointer(self, *args):
        pass

    async def press_pointer_button(self, *args):
        pass

    async def release_pointer_button(self, *args):
        pass

    async def release_pointer_buttons(self, *args):
        pass


@pytest.fixture
def stub_hid():
    ph = StubHid()
    ph._get_display_size = AsyncMock(return_value=Size(1000, 1000))
    ph._move_pointer = AsyncMock()
    yield ph


class TestHidBase:
    @pytest.mark.asyncio
    async def test_move_pointer_to_absolute(self, stub_hid):
        """
        Test the mouse movement processing.
        """
        await stub_hid.move_pointer_to_absolute(100, 200)
        stub_hid._move_pointer.assert_called_with(
            100 / 1000,
            200 / 1000,
        )

    @pytest.mark.asyncio
    async def test_move_pointer_to_absolute_raises(self, stub_hid):
        """
        Test the mouse movement processing.
        """
        with pytest.raises(AssertionError):
            await stub_hid.move_pointer_to_absolute(1001, 0)

        with pytest.raises(AssertionError):
            await stub_hid.move_pointer_to_absolute(0, 1001)

    @pytest.mark.asyncio
    async def test_move_pointer_to_proportional(self, stub_hid):
        """
        Test the proportional mouse movement processing.
        """
        await stub_hid.move_pointer_to_proportional(0.5, 0.5)
        stub_hid._move_pointer.assert_called_with(0.5, 0.5)

    @pytest.mark.asyncio
    async def test_move_pointer_to_proportional_raises(self, stub_hid):
        """
        Test the function raises an exception if the target position is out of
        screen.
        """
        with pytest.raises(AssertionError):
            await stub_hid.move_pointer_to_proportional(1.1, 0)

        with pytest.raises(AssertionError):
            await stub_hid.move_pointer_to_proportional(0, 1.1)

    @pytest.mark.asyncio
    async def test_walk_pointer_to_proportional(self, stub_hid, mock_sleep):
        """
        Test the function moves the pointer by the requested step to the target
        position given in proportional coordinates.
        """
        await stub_hid.move_pointer_to_proportional(0.15, 0.35)
        await stub_hid.walk_pointer_to_proportional(0.5, 0.5, 0.05, 0.2)

        stub_hid._move_pointer.assert_has_calls(
            (
                call(pytest.approx(0.2), pytest.approx(0.4)),
                call(pytest.approx(0.25), pytest.approx(0.45)),
                call(pytest.approx(0.3), pytest.approx(0.5)),
                call(pytest.approx(0.35), pytest.approx(0.5)),
                call(pytest.approx(0.4), pytest.approx(0.5)),
                call(pytest.approx(0.45), pytest.approx(0.5)),
                call(pytest.approx(0.5), pytest.approx(0.5)),
            )
        )

        mock_sleep.assert_has_calls(7 * [call(0.2)])

    @pytest.mark.asyncio
    async def test_walk_pointer_to_absolute(self, stub_hid, mock_sleep):
        """
        Test the function moves the pointer by the requested step to the target
        position given in absolute coordinates.
        """
        await stub_hid.move_pointer_to_proportional(0.15, 0.35)
        await stub_hid.walk_pointer_to_absolute(100, 200, 0.05, 0.2)

        stub_hid._move_pointer.assert_has_calls(
            (
                call(pytest.approx(0.1), pytest.approx(0.3)),
                call(pytest.approx(0.1), pytest.approx(0.25)),
                call(pytest.approx(0.1), pytest.approx(0.2)),
            )
        )

        mock_sleep.assert_has_calls(3 * [call(0.2)])
