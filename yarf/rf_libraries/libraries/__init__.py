import abc
import importlib
import pathlib
from typing import Any

SUPPORTED_PLATFORMS: dict[str, type] = {}


class PlatformMeta(abc.ABCMeta):
    """
    Metaclass for creating Platfrom classes.
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> "PlatformMeta":
        """
        Create a module class and register it in SUPPORTED_PLATFORMS.

        Arguments:
            name: module name
            bases: parent classes
            namespace: module namespace
            **kwargs: additional keyword arguments

        Returns:
            module_class: the created module class with registered in SUPPORTED_PLATFORMS.
        """
        module_class = super().__new__(mcs, name, bases, namespace, **kwargs)
        SUPPORTED_PLATFORMS[name] = module_class

        return module_class


class PlatformBase(abc.ABC, metaclass=PlatformMeta):
    @staticmethod
    @abc.abstractmethod
    def get_pkg_path() -> str:
        """
        Returns:
            Library directory path.
        Raises:
            NotImplementedError: if the method is not implemented in the subclass.
        """
        raise NotImplementedError


def import_libraries() -> None:
    """
    Importing every module inheriting from the PlatformBase abstract class is
    required to register a given method in SUPPORTED_PLATFORMS.

    We can assume every package under libraries are in effect
    implementations of a different platform, hence importing them should
    be enough.
    """
    module_path = pathlib.Path(__file__).resolve().parent
    not_needed = {"test"}
    for submodule in pathlib.Path(module_path).glob("*/__init__.py"):
        if submodule.parent.name in not_needed:
            continue
        importlib.import_module(
            f"yarf.rf_libraries.libraries.{submodule.parent.name}"
        )

    del SUPPORTED_PLATFORMS[PlatformBase.__name__]


import_libraries()
