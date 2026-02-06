from unittest.mock import ANY, Mock, patch

from yarf.rf_libraries.libraries.image.utils import log_image


class TestRfImageUtils:
    @patch("yarf.rf_libraries.libraries.image.utils.to_image")
    @patch("yarf.rf_libraries.libraries.image.utils.to_base64")
    @patch("yarf.rf_libraries.libraries.image.utils.logger")
    def test_log_image(self, mock_logger, mock_base_64, mock_to_image):
        """
        Test whether the function converts the images to base64 and add them to
        the HTML Robot log.
        """

        image = Mock()
        mock_to_image.return_value = image
        log_image(image, "Debug message")

        mock_base_64.assert_called_once_with(image)
        mock_logger.info.assert_called_once_with(ANY, html=True)
        assert mock_logger.info.call_args.args[0].startswith("Debug message")
