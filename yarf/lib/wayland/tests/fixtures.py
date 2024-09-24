import random
from unittest.mock import MagicMock, Mock, patch, sentinel

import pytest

from yarf.lib.wayland.protocols.wayland import WlOutput as wl_output


@pytest.fixture(autouse=True)
def mock_pwc():
    with patch("pywayland.client") as mock:
        yield mock


@pytest.fixture
def wl_client(request, mock_pwc, output_count):  # noqa: F811
    client_cls = request.node.get_closest_marker("wayland_client").args[0]
    client = client_cls(sentinel.display_name)

    wl_globals = request.node.get_closest_marker("wayland_globals").args

    for iface in wl_globals:
        mock_pwc.attach_mock(MagicMock(), iface.name)
        client.registry_global(
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
        client.registry_global(
            getattr(mock_pwc, f"wl_output_{n}"),
            sentinel.id,
            wl_output.name,
            random.randint(1, 10),
        )

    if output_size := request.node.get_closest_marker("output_size"):
        client.connected()
        client.xdg_output_logical_size(
            mock_pwc.xdg_output_0, *output_size.args
        )

    yield client
