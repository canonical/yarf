from unittest.mock import patch

from yarf.rf_libraries.libraries.zapper import Zapper, zapper_api


class TestZapper:
    """
    Test the Mir class.
    """

    def test_get_pkg_path(self) -> None:
        """
        Test whether the "get_pkg_path" method returns the expected path.
        """

        assert Zapper.get_pkg_path().endswith(
            "/yarf/rf_libraries/libraries/zapper"
        )


class TestConnection:
    """
    Test the RPyC connection.
    """

    @patch("rpyc.connect")
    def test_connection_cm(self, mock_connect):
        """
        Test whether the `connection` context manager creates and yields a
        connection to the Zapper service.
        """

        with patch.dict("os.environ", {"ZAPPER_IP": "192.168.1.1"}):
            with zapper_api() as service:
                service.function(1, 2, arg1="value1")

        function = mock_connect.return_value.root.function
        mock_connect.assert_called_once_with(
            "192.168.1.1",
            Zapper.RPYC_PORT,
            config={
                "allow_all_attrs": True,
                "sync_request_timeout": Zapper.RPYC_TIMEOUT,
            },
        )
        function.assert_called_once_with(1, 2, arg1="value1")

    @patch("rpyc.connect")
    def test_connection_cm_timeout(self, mock_connect):
        """
        Test whether the `zapper_api` context manager creates and yields a
        connection to the Zapper service with the provided timeout.
        """

        with patch.dict("os.environ", {"ZAPPER_IP": "192.168.1.1"}):
            with zapper_api(timeout=5) as service:
                service.function()

        mock_connect.assert_called_once_with(
            "192.168.1.1",
            Zapper.RPYC_PORT,
            config={
                "allow_all_attrs": True,
                "sync_request_timeout": 5,
            },
        )
