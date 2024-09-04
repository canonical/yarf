from unittest.mock import patch

from yarf.robot.libraries.zapper.Smoke import Smoke


class TestZapperSmoke:
    """Test the Smoke class."""

    def test_print_smoke(self) -> None:
        """
        Test whether the "print_smoke" keyword prints the expected message.
        """

        smoke = Smoke()
        with patch("robot.api.logger.info") as mock_logger:
            smoke.print_smoke()
            mock_logger.assert_called_once_with(
                "Smoke test for Zapper platform"
            )
