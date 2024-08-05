import abc
import pathlib
import importlib

SUPPORTED_PLATFORMS = {}


class PlatformMeta(abc.ABCMeta):
    """Metaclass for creating Platfrom classes."""

    def __new__(mcs, name, bases, namespace, **kwargs):
        """Create a module class and register it in SUPPORTED_PLATFORMS."""
        module_class = super().__new__(mcs, name, bases, namespace, **kwargs)
        SUPPORTED_PLATFORMS[name] = module_class

        return module_class


class PlatformBase(abc.ABC, metaclass=PlatformMeta):

    @staticmethod
    @abc.abstractmethod
    def get_pkg_path() -> str:
        """
        Retruns the library directory path
        """
        raise NotImplementedError


def import_libraries() -> None:
    """
    Importing every module inheriting from the PlatformBase abstract class
    is required to register a given method in SUPPORTED_PLATFORMS.
    We can assume every package under libraries are in effect implementations
    of a different platform, hence importing them should be enough.
    """
    module_path = pathlib.Path(__file__).resolve().parent
    not_needed = {"test"}
    for submodule in pathlib.Path(module_path).glob("*/__init__.py"):
        if submodule.parent.name in not_needed:
            continue
        importlib.import_module(
            f"yarf.robot.libraries.{submodule.parent.name}"
        )

    del SUPPORTED_PLATFORMS[PlatformBase.__name__]


import_libraries()
