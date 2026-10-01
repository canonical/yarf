"""
Access to the libraries and resources imported in Robot Framework.
"""

from copy import deepcopy
from typing import Any, TypeAlias

from robot.libdocpkg.model import LibraryDoc
from robot.libdocpkg.robotbuilder import (
    KeywordDocBuilder,
    LibraryDocBuilder,
    ResourceDocBuilder,
    TypeDocBuilder,
)
from robot.libraries.BuiltIn import BuiltIn
from robot.running import ResourceFile
from robot.running.testlibraries import TestLibrary

Library: TypeAlias = TestLibrary | ResourceFile


def get_libraries() -> list[TestLibrary]:
    """
    Get the imported libraries.

    Returns:
        the imported libraries
    """
    return [
        lib
        for lib in BuiltIn()._namespace._kw_store.libraries.values()
        if lib.name != "Reserved"
    ]


def get_resources() -> list[ResourceFile]:
    """
    Get the imported resources.

    Returns:
        the imported resources
    """
    return list(BuiltIn()._namespace._kw_store.resources._items)


def get_libs() -> list[Library]:
    """
    Get the imported libraries and resources.

    Returns:
        the imported libraries and resources, sorted by name
    """
    libs: list[Library] = [*get_libraries(), *get_resources()]
    return sorted(libs, key=lambda lib: lib.name)


def match_libs(name: str = "") -> list[Library]:
    """
    Find libraries and resources by prefix of their name.

    Args:
        name: case-insensitive name prefix

    Returns:
        the matching libraries and resources
    """
    return [
        lib for lib in get_libs() if lib.name.lower().startswith(name.lower())
    ]


class ImportedResourceDocBuilder(ResourceDocBuilder):
    """
    Build the documentation of an imported resource.
    """

    def build(self, resource: ResourceFile) -> LibraryDoc:  # type: ignore[override]
        """
        Build the documentation.

        Args:
            resource: the imported resource

        Returns:
            the resource documentation
        """
        libdoc = LibraryDoc(
            name=resource.name,
            doc=self._get_doc(resource, resource.name),
            type="RESOURCE",
            scope="GLOBAL",
            doc_format=self.doc_format or "ROBOT",
        )
        libdoc.keywords = KeywordDocBuilder(resource=True).build_keywords(
            deepcopy(resource)
        )
        return libdoc


class ImportedLibraryDocBuilder(LibraryDocBuilder):
    """
    Build the documentation of an imported library.
    """

    def build(self, lib: Any) -> LibraryDoc:
        """
        Build the documentation.

        Args:
            lib: the imported library

        Returns:
            the library documentation
        """
        libdoc = LibraryDoc(
            doc=self._get_doc(lib),
            version=lib.version,
            scope=lib.scope.name,
            doc_format=self.doc_format or lib.doc_format or "ROBOT",
            source=lib.source,
            lineno=lib.lineno,
            name=lib.name,
        )
        libdoc.inits = self._get_initializers(lib)
        libdoc.keywords = KeywordDocBuilder().build_keywords(lib)
        libdoc.type_docs = TypeDocBuilder().build(
            libdoc.inits + libdoc.keywords, lib.converters, libdoc.doc_format
        )
        return libdoc
