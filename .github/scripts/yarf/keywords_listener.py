import ast
import json
import logging
import re
from pathlib import Path

from yarf.rf_libraries import ROBOT_RESOURCE_PATH

_logger = logging.getLogger(__name__)
ENCODING = "utf-8"
BASE_LIB_PATH = (
    Path(__file__).parent.parent.parent.parent / "yarf/rf_libraries/libraries"
)


class KeywordsListener:
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, lib_path: str) -> None:
        self.unused_file = Path("unused_keywords.json")
        if self.unused_file.exists():
            with self.unused_file.open("r", encoding=ENCODING) as f:
                self.keywords = json.load(f)

            _logger.info(
                f"Loaded existing unused keywords from {self.unused_file}"
            )

        else:
            self.keywords = {}
            self._collect_robot_keywords(Path(ROBOT_RESOURCE_PATH))
            self._collect_library_keywords(Path(lib_path))
            _logger.info(
                f"Collected {len(self.keywords)} keywords from resources and libraries."
            )

    def _collect_robot_keywords(self, root: Path) -> None:
        """
        Collect keywords defined in Robot Framework resource files.
        """
        pattern = re.compile(r"\*{3}\s*Keywords\s*\*{3}", re.I)
        for file in root.rglob("*.resource"):
            self._extract_robot_keywords(file, pattern)

    def _extract_robot_keywords(self, file: Path, pattern) -> None:
        """
        Extract robot keywords from robot / resource files.
        """
        text = file.read_text(encoding=ENCODING)
        sections = pattern.split(text)

        if len(sections) < 2:
            _logger.debug(f"No *** Keywords *** section found in {file}")
            return

        # Process each *** Keywords *** section found
        for sec in sections[1:]:
            for line in sec.splitlines():
                line = line.rstrip()
                if not line or line.startswith((" ", "\t")):
                    continue

                if line.startswith("***"):
                    _logger.debug(f"End of Keywords section in {file}")
                    break

                if (kw := line.strip()) not in self.keywords:
                    self.keywords[kw] = {
                        "source": str(file),
                        "type": file.suffix.strip("."),
                    }

    def _collect_library_keywords(self, root: Path) -> None:
        """
        Collect keywords in all Robot Framework python libraries.
        """
        for pyfile in root.rglob("*.py"):
            self._extract_python_library_keywords(pyfile)

    def _extract_python_library_keywords(self, pyfile: Path) -> None:
        """
        Extracts Python keywords from classes AND their base classes.
        """
        if (tree := self._get_ast_tree(pyfile)) is None:
            return

        local_classes = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }

        # Process each class in this file
        for class_name, class_node in local_classes.items():
            # Get keywords defined directly inside the class
            self._get_python_class_keywords(class_node, pyfile, class_name)

            # Process inherited keywords
            for base in class_node.bases:
                if not (
                    isinstance(base, ast.Name) and base.id.endswith("Base")
                ):
                    continue

                base_class_name = base.id
                if (
                    base_path := self._find_python_class_file(
                        base_class_name, BASE_LIB_PATH
                    )
                ) is None:
                    continue

                if (base_tree := self._get_ast_tree(base_path)) is None:
                    continue

                for node in ast.walk(base_tree):
                    if (
                        isinstance(node, ast.ClassDef)
                        and node.name == base_class_name
                    ):
                        self._get_python_class_keywords(
                            node, pyfile, class_name
                        )

    def _get_ast_tree(self, pyfile: Path) -> ast.Module | None:
        """
        Parse a Python file and return its AST tree.

        Returns None if there's a syntax error.
        """
        try:
            return ast.parse(pyfile.read_text(encoding=ENCODING))

        except SyntaxError:
            _logger.warning(f"Syntax error when parsing {pyfile}, skipping.")
            return None

    def _get_python_class_keywords(
        self, node: ast.ClassDef, pyfile: Path, class_name: str
    ) -> None:
        """
        Get and store keywords.
        """
        for func in [
            n
            for n in node.body
            if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
        ]:
            kw_name = self._get_python_keyword_name(func)
            if kw_name and kw_name not in self.keywords:
                self.keywords[kw_name] = {
                    "source": str(pyfile),
                    "type": pyfile.suffix.strip("."),
                    "class": class_name,
                }

    def _find_python_class_file(
        self, class_name: str, search_root: Path
    ) -> Path | None:
        """
        Find the .py file where the parent class is defined.
        """
        for py in search_root.rglob("*.py"):
            if (tree := self._get_ast_tree(py)) is None:
                continue

            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    return py
        return None

    def _get_python_keyword_name(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> str | None:
        """
        Determine if a Python function defines a Robot keyword.

        Returns the keyword name if found, else None.
        """
        for d in func.decorator_list:
            if isinstance(d, ast.Name) and d.id == "keyword":
                parts = func.name.replace("_", " ").split()
                parts = [p.capitalize() for p in parts]
                return " ".join(parts)
        return None

    def start_keyword(self, data, result) -> None:
        """
        Remove the keyword from the unused list when it is used.
        """
        name = data.name.strip()
        if name in self.keywords:
            del self.keywords[name]

    def close(self) -> None:
        """
        Dump a json for unused keywords when the suite ends.
        """
        with self.unused_file.open("w", encoding=ENCODING) as f:
            json.dump(self.keywords, f, indent=2, ensure_ascii=False)

        _logger.info(f"Saved unused keywords to {self.unused_file}")
