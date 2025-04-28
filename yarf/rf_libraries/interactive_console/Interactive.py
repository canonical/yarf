"""
This module provides Robot Framework keywords exclusive to interactive mode.
"""

from typing import Any

from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn

from yarf.rf_libraries.interactive_console.tools.roi_selector import (
    ROISelector,
)


class Interactive:
    """
    A class for the user to interact with the console and perform various
    tasks. The keywords under this class is exclusive to interactive mode.

    Attributes:
        ROBOT_LIBRARY_SCOPE: Scope of the library.
        ROBOT_LISTENER_API_VERSION: API version for Robot Framework listeners.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        self.ROBOT_LIBRARY_LISTENER = self

    def _get_lib_instance(self, lib_name: str) -> Any:
        """
        Helper function to get an instance of a library imported in Robot
        Framework.

        Args:
            lib_name: The name of the library to get an instance of.

        Returns:
            An instance of the specified library.
        """
        return BuiltIn().get_library_instance(lib_name)

    @keyword
    async def grab_templates(self, *names: str) -> None:
        """
        Grabs a screenshot and allows the user to crop and save templates.

        Args:
            *names: Names of the templates to be cropped, skip this variable if there is no template names

        Raises:
            ValueError: If the screenshot could not be grabbed.
        """
        platform_video_input = self._get_lib_instance("PlatformVideoInput")
        if (image := await platform_video_input.grab_screenshot()) is None:
            raise ValueError("Failed to grab screenshot.")

        roi_selector = ROISelector(image, *names)
        roi_selector.start()
