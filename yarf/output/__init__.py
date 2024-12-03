import abc
import importlib
from pathlib import Path
from typing import Any

OUTPUT_FORMATS: dict[str, "OutputConverterBase"] = {}


def get_converted_output(format: str, outdir: Path) -> dict[str, int | object]:
    """
    Get converted output or raise error if not format is not supported.

    Arguments:
        format: output format to process
        outdir: output directory for storing the converted output

    Returns:
        Converted output in the specified format. If the output format is not supported,
        it raises a ValueError.

    Raises:
        ValueError: if the output format is not supported
    """
    try:
        output_format_module = OUTPUT_FORMATS[format]
        return output_format_module.get_output(outdir)
    except KeyError:
        raise ValueError(f"Unsupported output format: {format}")


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
    def get_output(self, outdir: Path, *args, **kwargs):
        """
        This method should implement the procedure to get the desired output
        format.

        Arguments:
            outdir: Path to the output directory
            *args: additional arguments
            **kwargs: additional keyword arguments
        """


module_path = Path(__file__).resolve().parent
for module in Path(module_path).glob("*.py"):
    importlib.import_module(f"yarf.output.{module.stem}")

del OUTPUT_FORMATS[OutputConverterBase.__name__]
