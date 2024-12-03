import abc
import importlib
import subprocess
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
        output_format_module: OutputConverterBase = OUTPUT_FORMATS[format]()
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

    @staticmethod
    def get_yarf_snap_info():
        try:
            # Run `snap info` command
            result = subprocess.run(
                ["snap", "info", "yarf"],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout

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

        except subprocess.CalledProcessError as e:
            raise ProcessLookupError(f"Error fetching snap info: {e}")


module_path = Path(__file__).resolve().parent
for module in Path(module_path).glob("*.py"):
    importlib.import_module(f"yarf.output.{module.stem}")

del OUTPUT_FORMATS[OutputConverterBase.__name__]
