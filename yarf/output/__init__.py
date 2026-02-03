import abc
import importlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

from owasp_logger import OWASPLogger
from robot.api import TestSuite

from yarf.loggers.owasp_logger import get_owasp_logger

_owasp_logger = OWASPLogger(appid=__name__, logger=get_owasp_logger())
_logger = logging.getLogger(__name__)

OUTPUT_FORMATS: dict[str, "OutputConverterMeta"] = {}


def get_outdir_path(outdir: Optional[str] = None) -> Path:
    """
    Get corresponding output directory base on outdir and the environment.

    Arguments:
        outdir: Output directory provided by the user

    Returns:
        Path: The output directory based on the provided `outdir` and the environment
    """
    if outdir is not None:
        yarf_outdir = Path(outdir)

    else:
        yarf_outdir = (
            Path(
                os.environ["SNAP_USER_COMMON"]
                if "SNAP" in os.environ
                else tempfile.gettempdir()
            )
            / "yarf-outdir"
        )

    # Delete selected files if exists
    for file in [
        "output.xml",
        "report.html",
        "log.html",
        "rfdebug_history.log",
    ]:
        (yarf_outdir / file).unlink(missing_ok=True)

    return yarf_outdir


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

    def wrapper(*args: Any, **kwargs: Any) -> Any:
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
        if (output_format := kwargs.get("output_format")) is None:
            return func(*args, **kwargs)

        try:
            converter: OutputConverterBase = OUTPUT_FORMATS[output_format]()

        except KeyError:
            error_msg = f"Unsupported output format: {kwargs['output_format']}"
            _owasp_logger.sys_crash(error_msg)
            raise ValueError(error_msg)

        suite = kwargs["suite"]
        outdir = kwargs["outdir"]

        converter.check_test_plan(suite)
        result = func(*args, **kwargs)
        formatted_output = converter.get_output(outdir)

        with open(outdir / f"{output_format}_output.json", "w") as f:
            json.dump(formatted_output, f, indent=4)

        _logger.info(
            f"Output for '{output_format}' exported to {outdir}/{output_format}_output.json."
        )

        return result

    return wrapper


class OutputConverterMeta(abc.ABCMeta):
    """
    Metaclass for creating Output Format classes.
    """

    def __new__(
        mcs, name: Any, bases: Any, namespace: Any, **kwargs
    ) -> "OutputConverterMeta":
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
    def check_test_plan(self, suite: TestSuite) -> None:
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
    def get_yarf_snap_info() -> dict[str, str] | None:
        """
        Get the YARF snap infomation including version, revision, channel and
        date.

        Raises:
            ValueError: When match installed YARF information cannot match with YARF snap info

        Returns:
            The YARF snap information in a dict
        """
        if "SNAP" not in os.environ:
            return None

        try:
            yarf_snap_info = {
                "name": os.environ["SNAP_NAME"],
                "version": os.environ["SNAP_VERSION"],
                "revision": os.environ["SNAP_REVISION"],
            }
        except KeyError as exc:
            raise ValueError("Cannot get installed YARF information.") from exc

        return yarf_snap_info  # type: ignore[return-value]


def import_supported_formats() -> None:
    module_path = Path(__file__).resolve().parent
    for module in Path(module_path).glob("*.py"):
        importlib.import_module(f"yarf.output.{module.stem}")

    del OUTPUT_FORMATS[OutputConverterBase.__name__]


import_supported_formats()
