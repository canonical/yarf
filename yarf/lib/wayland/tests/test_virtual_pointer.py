import itertools
import random
from unittest.mock import ANY, MagicMock, Mock, call, patch, sentinel

import pytest

from yarf.lib.wayland.protocols import WlOutput as wl_output
from yarf.lib.wayland.protocols import (
    ZwlrVirtualPointerManagerV1 as pointer_manager,
)
from yarf.lib.wayland.protocols import ZxdgOutputManagerV1 as output_manager
from yarf.lib.wayland.virtual_pointer import VirtualPointer

from .fixtures import mock_pwc  # noqa: F401

OUTPUT_SIZE = (random.randint(800, 4000), random.randint(800, 4000))


@pytest.fixture(scope="class")
def output_count():
    return random.randint(1, 4)


@pytest.fixture
def virtual_pointer(request, mock_pwc, output_count):  # noqa: F811
    vp = VirtualPointer(sentinel.display_name)

    wayland_globals = getattr(
        request.node.get_closest_marker("wayland_globals"),
        "args",
        (output_manager, pointer_manager),
    )

    for iface in wayland_globals:
        mock_pwc.attach_mock(MagicMock(), iface.name)
        vp.registry_global(
            MagicMock(**{"bind.return_value": getattr(mock_pwc, iface.name)}),
            sentinel.id,
            iface.name,
            random.randint(1, 10),
        )

    # Simulate registering outputs
    mock_pwc.zxdg_output_manager_v1.get_xdg_output.side_effect = (
        mock_xdg_outputs
    ) = tuple(MagicMock() for _n in range(output_count))
    for n in range(output_count):
        mock_pwc.attach_mock(Mock(), f"wl_output_{n}")
        mock_pwc.attach_mock(mock_xdg_outputs[n], f"xdg_output_{n}")
        vp.registry_global(
            getattr(mock_pwc, f"wl_output_{n}"),
            sentinel.id,
            wl_output.name,
            random.randint(1, 10),
        )

    if output_size := request.node.get_closest_marker("output_size"):
        vp.connected()
        vp.xdg_output_logical_size(mock_pwc.xdg_output_0, *output_size.args)

    yield vp


class TestVirtualPointer:
    @patch("yarf.lib.wayland.wayland_client.WaylandClient.__init__")
    def test_init(self, mock_super_init):
        VirtualPointer(sentinel.display_name)
        mock_super_init.assert_called_once_with(sentinel.display_name)

    @pytest.mark.parametrize(
        "interface",
        (wl_output, pointer_manager, output_manager),
    )
    def test_registry_global(self, virtual_pointer, interface):
        registry = Mock()
        version = random.randint(1, 10)
        virtual_pointer.registry_global(
            registry, registry.id, interface.name, version
        )
        registry.bind.assert_called_once_with(
            registry.id,
            interface,
            min(interface.version, version),
        )

    @pytest.mark.parametrize(
        ("missing"),
        (
            pytest.param(
                "pointer manager",
                marks=(pytest.mark.wayland_globals.with_args(output_manager),),
            ),
            pytest.param(
                "output manager",
                marks=(
                    pytest.mark.wayland_globals.with_args(pointer_manager),
                ),
            ),
        ),
    )
    def test_connected_raises_on_missing_manager(
        self, virtual_pointer, missing
    ):
        with pytest.raises(AssertionError, match=missing):
            virtual_pointer.connected()

    def test_connected(self, virtual_pointer, mock_pwc, output_count):  # noqa: F811
        virtual_pointer.connected()

        output_calls = itertools.chain.from_iterable(
            (
                call.zxdg_output_manager_v1.get_xdg_output(ANY),
                getattr(call, f"xdg_output_{n}").dispatcher.__setitem__(
                    "logical_size",
                    virtual_pointer.xdg_output_logical_size,
                ),
            )
            for n in range(output_count)
        )

        mock_pwc.assert_has_calls(
            [
                *output_calls,
                call.Display().roundtrip(),
                call.zwlr_virtual_pointer_manager_v1.create_virtual_pointer_with_output(
                    None, mock_pwc.wl_output_0.bind()
                ),
            ]
        )

    def test_disconnected(self, mock_pwc):  # noqa: F811
        assert not mock_pwc.mock_calls

    @pytest.mark.parametrize(
        (),
        (
            pytest.param(
                marks=[pytest.mark.output_size(random.randint(-1000, 0), 1)],
                id="width",
            ),
            pytest.param(
                marks=[pytest.mark.output_size(1, random.randint(-1000, 0))],
                id="height",
            ),
            pytest.param(
                marks=[
                    pytest.mark.output_size(
                        random.randint(-1000, 0), random.randint(-1000, 0)
                    )
                ],
                id="wh",
            ),
        ),
    )
    def test_move_to_absolute_asserts_dimensions(self, virtual_pointer):
        with pytest.raises(AssertionError, match="must be greater than 0"):
            virtual_pointer.move_to_absolute(0, 0)

    @pytest.mark.parametrize(
        ("x", "y"),
        (
            pytest.param(random.randint(-1000, -1), 0, id="W"),
            pytest.param(0, random.randint(-1000, -1), id="N"),
            pytest.param(
                random.randint(-1000, -1), random.randint(-1000, -1), id="NW"
            ),
            pytest.param(OUTPUT_SIZE[0] + random.randint(1, 1000), 0, id="E"),
            pytest.param(0, OUTPUT_SIZE[1] + random.randint(1, 1000), id="S"),
            pytest.param(
                OUTPUT_SIZE[0] + random.randint(1, 1000),
                OUTPUT_SIZE[1] + random.randint(1, 1000),
                id="SE",
            ),
        ),
    )
    @pytest.mark.output_size(*OUTPUT_SIZE)
    def test_move_to_absolute_asserts_range(self, virtual_pointer, x, y):
        with pytest.raises(AssertionError, match="not in range"):
            virtual_pointer.move_to_absolute(x, y)

    @pytest.mark.output_size(*OUTPUT_SIZE)
    def test_move_to_absolute(self, virtual_pointer, mock_pwc):  # noqa:F811
        point = tuple(random.randint(1, d) for d in OUTPUT_SIZE)

        virtual_pointer.timestamp = Mock()
        virtual_pointer.move_to_absolute(*point)

        mock_pwc.assert_has_calls(
            (
                call.zwlr_virtual_pointer_manager_v1.create_virtual_pointer_with_output().motion_absolute(
                    virtual_pointer.timestamp(), *point, *OUTPUT_SIZE
                ),
                call.zwlr_virtual_pointer_manager_v1.create_virtual_pointer_with_output().frame(),
                call.Display().roundtrip(),
            )
        )

    @pytest.mark.output_size(*OUTPUT_SIZE)
    def test_move_to_proportional(self, virtual_pointer):
        virtual_pointer.move_to_absolute = Mock()

        point = (1 / random.randint(1, 100), 1 / random.randint(1, 100))

        virtual_pointer.move_to_proportional(*point)

        virtual_pointer.move_to_absolute.assert_called_once_with(
            int(point[0] * OUTPUT_SIZE[0]), int(point[1] * OUTPUT_SIZE[1])
        )

    @pytest.mark.parametrize("state", (True, False))
    def test_button(self, virtual_pointer, mock_pwc, state):  # noqa:F811
        virtual_pointer.timestamp = Mock()

        virtual_pointer.connected()
        virtual_pointer.button(sentinel.button, state)

        mock_pwc.assert_has_calls(
            [
                call.zwlr_virtual_pointer_manager_v1.create_virtual_pointer_with_output().button(
                    virtual_pointer.timestamp(), sentinel.button, int(state)
                ),
                call.zwlr_virtual_pointer_manager_v1.create_virtual_pointer_with_output().frame(),
                call.Display().roundtrip(),
            ]
        )
