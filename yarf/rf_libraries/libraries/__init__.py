"""
Platform library discovery, registration, and plugin loading for YARF.
"""

import abc
import importlib
import importlib.util
import inspect
import logging
import os
import pathlib
import pkgutil
import site
import sys
from pathlib import Path
from typing import Any

from owasp_logger import OWASPLogger

from yarf.loggers.owasp_logger import get_owasp_logger

_owasp_logger = OWASPLogger(appid=__name__, logger=get_owasp_logger())
_logger = logging.getLogger(__name__)
SUPPORTED_PLATFORMS: dict[str, type] = {}
SNAP_PLUGINS_DIR = (
    f"{os.getenv('SNAP_COMMON')}/platform_plugins"
    if "SNAP" in os.environ
    else None
)
SITE_PLUGINS_DIR = site.getsitepackages()[0]
PLATFORM_PLUGIN_PREFIX = "yarf_plugin_"
DISCOVERY_COMPLETED = False


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

        Raises:
            KeyError: if the platform is not registered.
        """
        if DISCOVERY_COMPLETED:
            if name not in SUPPORTED_PLATFORMS:
                error_msg = f"Platform {name} is not registered."
                _logger.error(error_msg)
                _owasp_logger.sys_crash(error_msg)
                raise KeyError(error_msg)

            module_class = SUPPORTED_PLATFORMS[name]
        else:
            module_class = super().__new__(
                mcs, name, bases, namespace, **kwargs
            )
            if (
                module_class.__module__.startswith(PLATFORM_PLUGIN_PREFIX)
                and SUPPORTED_PLATFORMS.get(name) is not None
            ):
                _logger.warning(
                    f"Platform {name} is being overridden by {module_class.__module__}."
                )
            SUPPORTED_PLATFORMS[name] = module_class
            _owasp_logger.sys_monitor_enabled(
                "system", f"platform:{name} discovered."
            )

        return module_class  # type: ignore[return-value]


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

    def check_connection(self) -> Any:
        """
        Check if a connection to the platform can be established.

        Returns:
            True by default
        """
        _logger.warning(
            "check_connection is not implemented for this platform."
        )
        return True


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


def import_platform_plugin(dir_path: str) -> None:
    """
    Import external libraries that are not part of YARF.

    Args:
        dir_path: The path to the directory containing external libraries.
            If not provided, it defaults to the platform plugins directory
    """
    if dir_path is None:
        return

    external_plugins_path = Path(dir_path)
    if not external_plugins_path.exists() or (
        external_plugins_path.is_dir()
        and not any(external_plugins_path.iterdir())
    ):
        _logger.info(
            f"External plugins directory '{external_plugins_path}' does not exist or it is empty. "
            "Skipping import of external libraries."
        )
        return

    sys.path.insert(0, str(external_plugins_path))

    base_class: type = PlatformBase
    for loader, module_name, is_pkg in pkgutil.iter_modules(
        [str(external_plugins_path)]
    ):
        if not is_pkg:
            continue

        if not module_name.startswith(PLATFORM_PLUGIN_PREFIX):
            continue

        external_module_path = external_plugins_path / module_name
        spec = importlib.util.spec_from_file_location(
            module_name, external_module_path / "__init__.py"
        )

        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]

        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception:
            continue

        # Find plugin names in the module and put it inside sys.modules
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue
            if issubclass(cls, base_class) and cls is not base_class:
                sys.modules[cls.__name__] = module
                break


import_libraries()
# For user installed plugins
import_platform_plugin(SITE_PLUGINS_DIR)
# For plugins installed through snap interfaces
import_platform_plugin(SNAP_PLUGINS_DIR)  # type: ignore[arg-type]
DISCOVERY_COMPLETED = True
