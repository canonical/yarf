"""
This module provides a way to generate a Robot library documentation
page from an abstract class.

The tool provided by RobotFramework, libdoc, expects a file with name
MyLibrary.py containing a class with name MyLibrary. And the class
cannot be abstract.

This script takes the abstract library class, collect every information
about it, and generate a temporary Python module, with proper file name
and class name, and with a simple implementation of the abstract methods.

libdoc is finally run on this temporary class, making it possible to
generate the library in an automatic way.
"""

import ast
import importlib.util
import inspect
import sys
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from robot import libdoc


def load_module(module_name, file_path):
    """Load module from path and module name."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise Exception
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if spec.loader is None:
        raise Exception
    spec.loader.exec_module(module)
    return module


def extract_imports(file_path):
    """
    Extract all the necessary imports from the abstract
    module. The mock implementation will have to import
    the same modules to satisfy the rest of the codebase.
    """
    with open(file_path, "r") as file:
        node = ast.parse(file.read(), filename=file_path)

    imports = []
    for item in node.body:
        if isinstance(item, (ast.Import, ast.ImportFrom)):
            imports.append(ast.unparse(item))

    return "\n".join(imports) + "\n"


def create_mock_class(
    module_path,
    module_name,
    abstract_class,
    concrete_class_name,
):
    """
    Create a mock class with the right name, in CamelCase,
    including a simple implementation of every abstract method,
    and type hints in case of a keyword.
    """

    class MockClass(abstract_class):
        pass

    setattr(MockClass, __name__, concrete_class_name)
    for method_name in abstract_class.__abstractmethods__:
        setattr(MockClass, method_name, lambda *args, **kwargs: None)

    class_name = concrete_class_name
    class_source = extract_imports(module_path)
    class_source += f"from {module_name} import {abstract_class.__name__}\n"
    class_source += f"class {class_name}({abstract_class.__name__}):\n"

    for method_name in abstract_class.__abstractmethods__:
        method = getattr(abstract_class, method_name)
        if method.__name__.startswith("_"):
            # Don't care about type hinting for internal methods
            class_source += f"    def {method_name}(self, *args, **kwargs):\n"
        else:
            class_source += (
                f"    def {method_name}{str(inspect.signature(method))}:\n"
            )

        class_source += f"        pass\n\n"

    return class_source


def generate_libdoc_for_libraries(module_path: Path, outfile: Path):
    """
    Take a Robot abstract module library path and generate via
    libdoc a documentation file.
    """

    # Get class names
    module_name = module_path.stem
    abstract_class_name = "".join(
        ele.title() for ele in module_name.split("_")
    )
    concrete_class_name = abstract_class_name.replace("Base", "")

    # Load the module from YARF source code
    module = load_module(module_name, module_path)
    abstract_class = getattr(module, abstract_class_name)

    # Create a mock class overriding abstract methods
    source = create_mock_class(
        module_path,
        module_name,
        abstract_class,
        concrete_class_name,
    )

    # Write the file on a temporary directory so that it can be
    # loaded by libdoc
    with TemporaryDirectory() as tempdir:
        copyfile(module_path, str(Path(tempdir) / module_path.name))
        with open(
            Path(tempdir) / f"{concrete_class_name}.py", "w"
        ) as source_file:
            source_file.write(source)

        rc = libdoc.libdoc(
            source_file.name,
            str(outfile),
            quiet=True,
        )
        if rc != 0:
            raise ValueError()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("library", type=str)
    parser.add_argument("outfile", type=str)

    args = parser.parse_args()
    generate_libdoc_for_libraries(Path(args.library), Path(args.outfile))
