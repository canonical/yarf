"""
Robot Framework library opening the interactive REPL.
"""

import sys

from robot.libraries.BuiltIn import BuiltIn

from .debugcmd import ReplCmd
from .styles import print_output


class RobotDebug:
    """
    Debug Library for Robot Framework.

    Attributes:
        ROBOT_LIBRARY_SCOPE: The Robot Framework library scope
        ROBOT_LIBRARY_VERSION: The upstream version this library is based on
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "4.5.0+yarf"

    def __init__(self) -> None:
        self.show_intro = True

    def Library(self, name: str, *args: str) -> None:  # noqa: N802
        """
        Import a library into the current suite.

        Args:
            name: name or path of the library
            *args: library arguments
        """
        BuiltIn().import_library(name, *args)

    def Resource(self, path: str) -> None:  # noqa: N802
        """
        Import a resource file into the current suite.

        Args:
            path: path of the resource file
        """
        BuiltIn().import_resource(path)

    def Variables(self, path: str, *args: str) -> None:  # noqa: N802
        """
        Import a variable file into the current suite.

        Args:
            path: path of the variable file
            *args: variable file arguments
        """
        BuiltIn().import_variables(path, *args)

    def debug(self) -> None:
        """
        Open an interactive shell to run any Robot Framework keywords.

        Keywords separated by two space or one tab, and Ctrl-D to exit.
        """
        # Restore the real stdout, captured by Robot Framework, for the shell
        old_stdout = sys.stdout
        sys.stdout = sys.__stdout__
        try:
            print_output(">>>>>", "Enter interactive shell")
            # None shows the default intro, "" shows nothing
            intro = None if self.show_intro else ""
            self.show_intro = False
            ReplCmd().cmdloop(intro=intro)
            print_output("<<<<<", "Exit shell.")
        finally:
            sys.stdout = old_stdout
