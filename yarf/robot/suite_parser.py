import logging
import tempfile
import shutil
from typing import Final
from pathlib import Path
from contextlib import contextmanager, suppress


_logger = logging.getLogger(__name__)


class SuiteParser:
    VARIANTS_DIR: Final = "variants"

    def __init__(self, suite_path: str) -> None:
        self.suite_path = Path(suite_path)
        self.assets = dict()
        self.variants = dict()
        self.read_suite()

    def read_suite(self) -> None:
        """
        Get all assets and robot files from the suite top level directory.
        """
        has_robot_ext = False
        for path in (p for p in self.suite_path.rglob("*") if not p.is_dir()):

            relative_path = path.relative_to(self.suite_path)
            if relative_path.parts[0] == SuiteParser.VARIANTS_DIR:
                self.variants[Path().joinpath(*relative_path.parts[1:])] = path
            else:
                if SuiteParser.VARIANTS_DIR in relative_path.parts:
                    _logger.warning(
                        f"'{SuiteParser.VARIANTS_DIR}' is a special dirname, avoid using it in asset paths."
                    )
                has_robot_ext |= path.suffix == ".robot"
                self.assets[relative_path] = path

        if not has_robot_ext:
            msg = "Expected at least one <name>.robot file."
            _logger.error(msg)
            raise ValueError(msg)

    @contextmanager
    def suite_in_temp_folder(self, variant: str):
        """
        A context manager that creates a temporary directory that contains
        the suite robot file(s) and asset(s), and exposes a path to the
        temporary directory. The temporary directory will be automatically
        destroyed when the program exits the scope under this context manager.
        """
        actual_assets = self.select_assets(variant)
        with tempfile.TemporaryDirectory() as temp_directory_path:
            for relative_path, src_path in actual_assets.items():
                dest_path = temp_directory_path / relative_path.parent
                if len(relative_path.parts) > 1:
                    dest_path.mkdir(parents=True, exist_ok=True)

                shutil.copy(src_path, dest_path, follow_symlinks=True)
                _logger.debug(
                    f"Copied '{relative_path}' from '{src_path}' to '{dest_path}'"
                )

            yield Path(temp_directory_path)

    def select_assets(self, variant: str) -> dict[Path, Path]:
        """
        Get all assets needed according to the precedence list.
        """
        actual_assets = dict()
        variants_precedence_list = self.get_variants_precedence_list(variant)
        for rel_file_path, src_file_path in self.assets.items():
            for variant_path in variants_precedence_list:
                with suppress(KeyError):
                    actual_assets[rel_file_path] = self.variants[
                        variant_path / rel_file_path
                    ]
                    break
            else:
                # go for default
                actual_assets[rel_file_path] = src_file_path

        _logger.info(
            "Selected assets:\n  {}".format(
                "\n  ".join(
                    str(p.relative_to(self.suite_path))
                    for p in actual_assets.values()
                )
            )
        )

        return actual_assets

    def get_variants_precedence_list(self, variant_str: str) -> list[Path]:
        """
        Form a list of paths according to the variant string
        and the reversed ascending sort them by specificity degree.
        """
        if variant_str == "" or variant_str is None:
            return []

        variant = Path(variant_str)
        n = len(variant.parts)
        precedence_list = []

        # Create combinations of paths that we want to look into:
        for i in range(n):
            joined_path = Path().joinpath(*variant.parts[i:])
            # Add current path
            precedence_list.append(joined_path)
            # Add parent paths
            for parent_path in joined_path.parents[:-1]:
                precedence_list.append(parent_path)

        precedence_list.sort(key=lambda x: len(x.parts))
        precedence_list.reverse()
        return precedence_list
