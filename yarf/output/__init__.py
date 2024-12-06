import abc
import importlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Callable

from robot.api import TestSuite

OUTPUT_FORMATS: dict[str, "OutputConverterBase"] = {}

_logger = logging.getLogger(__name__)


def output_converter(func: Callable) -> Callable:
    """
    Wrapper around the function(s) which executes the robot suites with the
    output converter which pre-check the suite and generate the ouput according
    to the specified format.

    Arguments:
        func: The function to be wrapped

    Returns:
        A wrapper function that performs additional checks
        and formatting before running the test suite.
    """

    def wrapper(*args: Any, **kwargs: dict[Any, Any]) -> Any:
        """
        The function that wraps the target robot suite executing function
        around. Prior to the target function calling, this function will select
        the specified output format class and check the suite against the
        requirements of the specified format.

        After the target function is called, this function will
        generate and export the output according to the
        specified format.

        Arguments:
            *args: Positional arguments to be passed to the target function.
            **kwargs: Keyword arguments to be passed to the target function.

        Returns:
            The result of the target function.

        Raises:
            ValueError: If the output format is not supported.
        """
        if not ("output_format" in kwargs and kwargs["output_format"]):
            return func(*args, **kwargs)

        try:
            output_format = kwargs["output_format"]
            converter: OutputConverterBase = OUTPUT_FORMATS[output_format]()

        except KeyError:
            raise ValueError(
                f"Unsupported output format: {kwargs['output_format']}"
            )

        suite = kwargs["suite"]
        outdir = kwargs["outdir"]

        converter.check_suite(suite)
        result = func(*args, **kwargs)
        formatted_output = converter.get_output(outdir)

        with open(outdir / "submission.json", "w") as f:
            json.dump(formatted_output, f, indent=4)

        _logger.info(
            f"Output for '{output_format}' exported to {outdir}/submission.json."
        )

        return result

    return wrapper


class OutputConverterMeta(abc.ABCMeta):
    """
    Metaclass for creating Output Format classes.
    """

    def __new__(mcs, name: Any, bases: Any, namespace: Any, **kwargs):
        """
        Create a module class and register it in OUTPUT_FORMATS.

        Arguments:
            name: module name
            bases: parent classes
            namespace: module namespace
            **kwargs: additional keyword arguments

        Returns:
            Module class registered in OUTPUT_FORMATS
        """
        module_class = super().__new__(mcs, name, bases, namespace, **kwargs)
        OUTPUT_FORMATS[name] = module_class
        return module_class


# pylint: disable=R0903
class OutputConverterBase(abc.ABC, metaclass=OutputConverterMeta):
    """
    Abstract base class defining common interface for different output
    converter methods.
    """

    @abc.abstractmethod
    def check_suite(self, suite: TestSuite) -> None:
        """
        This method should implement the procedure to check if the test suite
        has all the required information for the output format.

        Arguments:
            suite: an initialized executable TestSuite
        """

    @abc.abstractmethod
    def get_output(self, outdir: Path, *args, **kwargs) -> Any:
        """
        This method should implement the procedure to get the desired output
        format.

        Arguments:
            outdir: Path to the output directory
            *args: additional arguments
            **kwargs: additional keyword arguments

        Returns:
            Anything that is appropriate to the specific output format
        """

    @staticmethod
    def get_yarf_snap_info() -> dict[str, str]:
        """
        Get the YARF snap infomation including version, revision, channel and
        date.

        Raises:
            RuntimeError: When the subprocess failed to run
            ValueError: When match installed YARF information cannot match with YARF snap info

        Returns:
            The YARF snap information in a dict
        """
        try:
            # Run `snap info` command
            result = subprocess.run(
                ["snap", "info", "yarf"],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError("Subprocess execution failed.") from e

        # Get the installed snap info
        installed_yarf_info = {}
        channels = {}
        for line in output.splitlines():
            if line.strip().startswith("name:"):
                parts = line.split()
                installed_yarf_info["name"] = parts[1]

            elif line.strip().startswith("latest/"):
                parts = line.split()
                channel = parts[0].rstrip(":")
                version = parts[1]
                date = parts[2] if len(parts) > 2 else "Unknown"
                revision = parts[3] if len(parts) > 3 else "Unknown"
                channels[channel] = {
                    "channel": channel,
                    "version": version,
                    "revision": revision.strip("()"),
                    "date": date,
                }

            elif line.strip().startswith("installed:"):
                parts = line.split()
                installed_yarf_info["version"] = parts[1]
                installed_yarf_info["revision"] = parts[2].strip("()")

            elif line.strip().startswith("tracking:"):
                parts = line.split()
                installed_yarf_info["channel"] = parts[1]

        for channel, info in channels.items():
            if (
                info["channel"] == installed_yarf_info["channel"]
                and info["revision"] == installed_yarf_info["revision"]
                and info["version"] == installed_yarf_info["version"]
            ):
                return channels[channel] | installed_yarf_info

        raise ValueError(
            "Cannot match installed YARF information with YARF snap info."
        )


def import_supported_formats():
    module_path = Path(__file__).resolve().parent
    for module in Path(module_path).glob("*.py"):
        importlib.import_module(f"yarf.output.{module.stem}")

    del OUTPUT_FORMATS[OutputConverterBase.__name__]


import_supported_formats()
