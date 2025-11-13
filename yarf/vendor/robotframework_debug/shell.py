import sys
import tempfile
from pathlib import Path

from robot import run_cli

TEST_SUITE = b"""
*** Settings ***
Library    RobotDebug   repl=${True}

*** Test Cases ***
Robot Framework Debug REPL
    Debug
"""


def shell():
    """A standalone robotframework shell."""

    default_no_logs = [
        "-l",
        "None",
        "-x",
        "None",
        "-o",
        "None",
        "-L",
        "None",
        "-r",
        "None",
        "--quiet",
    ]

    with tempfile.NamedTemporaryFile(
        prefix="robot-debug-", suffix=".robot", delete=False
    ) as test_file:
        test_file.write(TEST_SUITE)
        test_file.flush()

        if len(sys.argv) > 1:
            args = sys.argv[1:] + [test_file.name]
        else:
            args = [*default_no_logs, test_file.name]

        try:
            sys.exit(run_cli(args))
        finally:
            test_file.close()
            # pybot will raise PermissionError on Windows NT or later
            # if NamedTemporaryFile called with `delete=True`,
            # deleting test file seperated will be OK.
            file_path = Path(test_file.name)
            if file_path.exists():
                file_path.unlink()


if __name__ == "__main__":
    # Usage: python -m RobotDebug.shell
    shell()
