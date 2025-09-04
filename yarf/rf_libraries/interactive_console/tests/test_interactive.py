from unittest.mock import AsyncMock, MagicMock, Mock, patch, sentinel

import pytest

from yarf.rf_libraries.interactive_console.Interactive import Interactive


class TestInteractive:
    @pytest.mark.asyncio
    @patch(
        "yarf.rf_libraries.interactive_console.Interactive.BuiltIn.get_library_instance"
    )
    @patch("yarf.rf_libraries.interactive_console.Interactive.ROISelector")
    async def test_grab_templates(
        self, mock_ROISelector: MagicMock, mock_get_lib_instance: MagicMock
    ) -> None:
        interactive = Interactive()
        mock_get_lib_instance.return_value = sentinel.platform_video_input
        sentinel.platform_video_input.grab_screenshot = AsyncMock(
            return_value=sentinel.image
        )
        await interactive.grab_templates(sentinel.template_names)

        mock_get_lib_instance.assert_called_once_with("VideoInput")
        sentinel.platform_video_input.grab_screenshot.assert_called_once()
        mock_ROISelector.assert_called_once_with(
            sentinel.image, sentinel.template_names
        )
        mock_ROISelector.return_value.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_template_factory_no_image(self) -> None:
        interactive = Interactive()
        interactive._get_lib_instance = Mock(
            return_value=sentinel.platform_video_input
        )
        sentinel.platform_video_input.grab_screenshot = AsyncMock(
            return_value=None
        )
        with pytest.raises(ValueError):
            await interactive.grab_templates()
