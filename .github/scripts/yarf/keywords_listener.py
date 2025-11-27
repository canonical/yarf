import ast
import json
import logging
import re
import token
from collections import deque
from pathlib import Path
from typing import Any

from asttokens import ASTTokens
from robot.api import get_model
from robot.libdoc import LibraryDocumentation
from robot.libdocpkg.model import LibraryDoc
from robot.parsing.model import File
from robot.parsing.model.blocks import Block
from robot.parsing.model.blocks import Keyword as KeywordNode
from robot.parsing.model.blocks import SettingSection
from robot.parsing.model.statements import KeywordCall, Statement, Tags

from yarf.rf_libraries import ROBOT_RESOURCE_PATH

_logger = logging.getLogger(__name__)
ENCODING = "utf-8"
BASE_LIB_PATH = (
    Path(__file__).parent.parent.parent.parent / "yarf/rf_libraries/libraries"
)
UNUSED_FILE_PATH = Path("keywords_coverage.json")


class KeywordsListener:
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, lib_path: str) -> None:
        self.unused_file = UNUSED_FILE_PATH
        self.classes = set()
        if self.unused_file.exists():
            with self.unused_file.open("r", encoding=ENCODING) as f:
                self.functions = json.load(f)

            for func in self.functions:
                self.classes.add(self.functions[func]["class"])

            _logger.info(f"Loaded existing {self.unused_file}.")

        else:
            self.functions = {}
            self._collect_robot_keywords(Path(ROBOT_RESOURCE_PATH))
            self._collect_library_keywords(Path(lib_path))
            self._prune()
            _logger.info(
                f"Collected {len(self.functions)} functions from resources and libraries."
            )

    def _prune(self) -> None:
        """
        Prune dependencies that are not recorded and functions that are not
        keywords.
        """
        all_keywords = list(self.functions.keys())
        for kw in all_keywords:
            # Prune dependencies that are not recorded
            for dep in self.functions[kw]["dependencies"].copy():
                dep_info = self.functions[kw]["dependencies"][dep]
                del self.functions[kw]["dependencies"][dep]
                if len(dep_kws := self._get_valid_matches(dep)) <= 0:
                    continue

                for dep_kw in dep_kws:
                    if self.functions[dep_kw]["class"] == dep_info["class"]:
                        self.functions[kw]["dependencies"][dep_kw] = dep_info
                        break

            # We are not interested in functions that
            # are not keywords and has no dependencies
            if (
                not self.functions[kw].get("is_keyword", False)
                and len(self.functions[kw]["dependencies"]) == 0
            ):
                del self.functions[kw]

    def _get_valid_matches(self, dep):
        """
        Returns the valid keyword names if we get match(es)
        """
        valid_matches = []
        for kw in self.functions.keys():
            if self._dependency_matches_keyword(dep, kw):
                valid_matches.append(kw)
        return valid_matches

    def _dependency_matches_keyword(self, dep: str, kw_name: str) -> bool:
        """
        Check if the dependency name matches the keyword name, even if the
        keyword name is embedded.
        """
        dep = dep.strip()
        kw_name = kw_name.strip()

        # non embedded --> direct match
        if "${" not in kw_name:
            return dep.lower() == kw_name.lower()

        # embedded --> regex match
        return self._regex_matches_keyword(dep, kw_name)

    def _collect_robot_keywords(self, root: Path) -> None:
        """
        Collect keywords defined in Robot Framework resource files.
        """
        for file in root.rglob("*.resource"):
            self._get_keywords_used_in_robot_file(file)

    def _get_keywords_used_in_robot_file(self, path: str):
        """
        Get all keywords in the robot/resource file path, along with their
        dependencies.
        """
        model = get_model(path)
        libs = self._get_imported_libraries(model)
        libdocs = self._load_library_docs(libs)

        for section in model.sections:
            for kw in section.body:
                if not isinstance(kw, KeywordNode):
                    continue

                if self._is_no_coverage_robot(kw.body):
                    continue

                kw_name = kw.name
                dependencies = {}
                for node in kw.body:
                    for call in self._extract_keyword_dependencies(node):
                        klass, original_keyword_name = (
                            self._resolve_keyword_class(
                                call,
                                libdocs,
                                section.body,
                                model.source.name,
                            )
                        )
                        if original_keyword_name is None:
                            continue

                        if "." in original_keyword_name:
                            original_keyword_name = (
                                original_keyword_name.split(".", 1)[1]
                            )
                        dependencies[original_keyword_name] = {"class": klass}
                self.functions[kw_name] = {
                    "is_keyword": True,
                    "source": str(model.source),
                    "type": model.source.suffix.strip("."),
                    "class": model.source.stem,
                    "dependencies": dependencies,
                }
                self.classes.add(model.source.stem)

    def _is_no_coverage_robot(self, kw_body: list[Any]) -> bool:
        for node in kw_body:
            if not isinstance(node, Tags):
                continue

            if "yarf: nocoverage" in node.values:
                return True

        return False

    def _extract_keyword_dependencies(
        self, node: Statement | Block
    ) -> list[str]:
        """
        Extract the dependencies in a keyword.
        """
        calls = []

        if isinstance(node, KeywordCall):
            calls.append(node.keyword)

        # Body
        if hasattr(node, "body"):
            for child in node.body:
                calls.extend(self._extract_keyword_dependencies(child))

        # Conditional / exception branches
        for attr in ("orelse", "excepts", "finalbody"):
            branch = getattr(node, attr, None)
            if not branch:
                continue

            for child in self._iter_nodes(branch):
                calls.extend(self._extract_keyword_dependencies(child))

        # Special handling for `Run Keyword ...`
        # Also take the Keyword it runs.
        if hasattr(node, "keyword") and node.keyword.startswith("Run Keyword"):
            calls.append(node.args[0])

        return calls

    def _iter_nodes(self, obj: Any) -> list[Any]:
        """
        Turn obj into a list for iteration.
        """
        if obj is None:
            return []
        if isinstance(obj, list):
            return obj
        return [obj]

    def _get_imported_libraries(self, model: File) -> set[str]:
        """
        Get all library name from the model (robot/resource) file.
        """
        libs = set()
        for section in model.sections:
            if not isinstance(section, SettingSection):
                continue

            for setting in section.body:
                if setting.type == "LIBRARY":
                    libs.add(setting.name)

        return libs

    def _load_library_docs(
        self, library_imports: list[str]
    ) -> dict[str, LibraryDoc]:
        """
        Get Library documentations from the list of library import names.
        """
        docs = {}

        for lib in library_imports:
            if "." in lib:
                lib_name = lib.split(".", 1)[0]
            else:
                lib_name = lib

            try:
                libdoc = LibraryDocumentation(lib_name)
                docs[lib_name] = libdoc
            except Exception:
                # library may be a file or resource; you can expand this logic
                pass

        return docs

    def _resolve_keyword_class(
        self,
        name: str,
        library_docs: dict[str, LibraryDoc],
        current_file_keywords: list[KeywordNode],
        current_file_name: str,
    ) -> tuple[str, str]:
        """
        Find and return class name of the keyword, along with the real function
        name.
        """
        # First try to find exact match
        # Current file:
        for kw in current_file_keywords:
            if kw.name == name:
                return current_file_name, name

        # namespaced: Lib.Keyword Name
        if "." in name:
            lib_prefix, kw_name = name.split(".", 1)
            libdoc = library_docs.get(lib_prefix)
            if libdoc:
                for kw in libdoc.keywords:
                    if kw.name == kw_name:
                        return libdoc.name, name

        else:
            # search through all libraries
            for _, libdoc in library_docs.items():
                for kw in libdoc.keywords:
                    if kw.name == name:
                        return libdoc.name, name

        # Cannot find keyword through exact match, try regex
        # Current file
        for kw in current_file_keywords:
            if self._regex_matches_keyword(name, kw.name):
                return current_file_name, kw.name

        if "." in name:
            lib_prefix, kw_name = name.split(".", 1)
            libdoc = library_docs.get(lib_prefix)
            if libdoc:
                for kw in libdoc.keywords:
                    if self._regex_matches_keyword(kw_name, kw.name):
                        return libdoc.name, kw.name

        else:
            # search through all libraries
            for _, libdoc in library_docs.items():
                for kw in libdoc.keywords:
                    if self._regex_matches_keyword(name, kw.name):
                        return libdoc.name, kw.name

        return None, None

    def _regex_matches_keyword(self, to_match: str, kw_name: str) -> bool:
        call_tokens = to_match.strip().split()
        template_tokens = kw_name.strip().split()

        if len(call_tokens) != len(template_tokens):
            return False

        for ct, tt in zip(call_tokens, template_tokens):
            # If token contains a placeholder anywhere
            if "${" in tt:
                # Convert this template token to regex
                token_regex = self._embedded_template_to_regex(tt)
                if not token_regex.fullmatch(ct):
                    return False
            else:
                if ct.lower() != tt.lower():
                    return False

        return True

    def _embedded_template_to_regex(self, template: str) -> re.Pattern:
        escaped = re.escape(template)
        regex = re.sub(
            r"\\\$\\\{[^}]+\\\}(?:\[[^\]]+\])?",  # matches ${var} or ${var}[0]
            r"(.+?)",
            escaped,
        )

        return re.compile("^" + regex + "$", re.IGNORECASE)

    def _collect_library_keywords(self, root: Path) -> None:
        """
        Collect keywords in all Robot Framework python libraries.
        """
        for pyfile in root.rglob("*.py"):
            if pyfile.name.startswith("test"):
                continue
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
            self._get_python_class_functions(class_node, pyfile)

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
                        self._get_python_class_functions(node, base_path)

    def _get_ast_tree(self, pyfile: Path) -> ast.Module | None:
        """
        Parse a Python file and return its AST tree.

        Returns None if there's a syntax error.
        """
        try:
            self.atok = ASTTokens(
                pyfile.read_text(encoding=ENCODING), parse=True
            )
            return self.atok.tree

        except SyntaxError:
            _logger.warning(f"Syntax error when parsing {pyfile}, skipping.")
            return None

    def _is_no_coverage_python(self, node):
        """
        Extract contiguous leading comments above a node, including comments
        above decorators.
        """
        comments = []
        # walk upward token-by-token
        prev_tok = self.atok.prev_token(node.first_token, include_extra=True)
        while prev_tok is not None:
            if prev_tok.type == token.COMMENT:
                comments.append(prev_tok.string)

            elif prev_tok.type in {
                token.NL,
                token.NEWLINE,
                token.INDENT,
                token.DEDENT,
            }:
                pass

            elif prev_tok.string.strip() == "":
                pass

            else:
                # real code
                break

            prev_tok = self.atok.prev_token(prev_tok, include_extra=True)

        for comment in reversed(comments):
            parts = comment.split(":", 1)
            if (
                len(parts) == 2
                and parts[0].endswith("yarf")
                and parts[1].strip() == "nocoverage"
            ):
                return True

        return False

    def _get_python_class_functions(
        self, node: ast.ClassDef, pyfile: Path
    ) -> None:
        """
        Get and store keywords.
        """
        for func in [
            n
            for n in node.body
            if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
        ]:
            if self._is_no_coverage_python(func):
                continue

            kw_name, is_keyword = self._get_python_function_name(func)
            if (kw_name not in self.functions) or (
                kw_name in self.functions
                and not self.functions[kw_name]["is_keyword"]
                and is_keyword
            ):
                cls_name = (
                    node.name[: len(node.name) - 4]
                    if node.name.endswith("Base")
                    else node.name
                )
                self.functions[kw_name] = {
                    "is_keyword": is_keyword,
                    "source": str(pyfile),
                    "type": pyfile.suffix.strip("."),
                    "class": cls_name,
                    "dependencies": self._extract_deps_from_python_function(
                        func, node
                    ),
                }
                self.classes.add(cls_name)

    def _extract_deps_from_python_function(
        self,
        func_node: ast.AsyncFunctionDef | ast.FunctionDef,
        cls_node: ast.ClassDef,
    ) -> dict:
        """
        Get dependency functions from a python function.
        """
        deps = {}
        for node in ast.walk(func_node):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
            ):
                continue

            if node.func.attr == "run_keyword" and node.args:
                # BuiltIn().run_keyword("Some Keyword")
                if isinstance(node.args[0], ast.Constant):
                    kw = node.args[0].value
                    deps.add(kw)
            else:
                name = node.func.attr.replace(
                    "_", " "
                ).title()  # convert python name
                dep_cls_name = None
                if (id := getattr(node.func.value, "id", None)) is not None:
                    dep_cls_name = cls_node.name if id == "self" else id

                elif getattr(node.func.value, "attr", None) is not None:
                    attr_chain = self._get_attr_chain(node.func.value)
                    assignment_node = self._find_assignment_by_chain(
                        cls_node, attr_chain
                    )
                    if isinstance(assignment_node, list):
                        dep_cls_name = ".".join(assignment_node)
                    else:
                        dep_cls_name = self._get_dependency_chain(
                            assignment_node
                        )
                deps[name.strip()] = {
                    "class": dep_cls_name[: len(dep_cls_name) - 4]
                    if dep_cls_name and dep_cls_name.endswith("Base")
                    else dep_cls_name
                }

        return deps

    def _get_dependency_chain(
        self, assign_node: ast.Assign | ast.AnnAssign | None
    ) -> str:
        """
        Given an assignment like self._screencopy = screencopy.Screencopy(...),
        return ['screencopy', 'Screencopy'].
        """
        if assign_node is None:
            return None

        value = (
            assign_node.value
            if isinstance(assign_node, ast.Assign)
            else assign_node.value
        )
        if isinstance(value, ast.Call):
            func = value.func
            chain = []
            while isinstance(func, ast.Attribute):
                chain.append(func.attr)
                func = func.value

            if isinstance(func, ast.Name):
                chain.append(func.id)

            chain.reverse()
            return ".".join(chain)
        return None

    def _find_assignment_by_chain(
        self, classdef: ast.ClassDef, chain: list[str] | None
    ) -> ast.Assign | ast.AnnAssign | list[str]:
        """
        Find an assignment to a self attribute with arbitrary depth: self.x.y.z = ...
        Returns ast.Assign or ast.AnnAssign
        """
        if chain is None:
            return None

        for func in (
            n
            for n in classdef.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            for node in ast.walk(func):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue

                targets = (
                    node.targets
                    if isinstance(node, ast.Assign)
                    else [node.target]
                )
                for t in targets:
                    if self._matches_attr_chain(t, chain):
                        return node
        return chain

    def _matches_attr_chain(self, node: Any, chain: list[str]) -> bool:
        """
        Check if an ast.Attribute or ast.Name matches a given chain.

        Example:
            node: self.x.y.z
            chain: ['self', 'x', 'y', 'z']
            gives True
        """
        current = node
        idx = len(chain) - 1  # start from the end of the chain
        while idx >= 0:
            if isinstance(current, ast.Attribute):
                if current.attr != chain[idx]:
                    return False
                current = current.value
            elif isinstance(current, ast.Name):
                if current.id != chain[idx]:
                    return False
                current = None
            else:
                return False
            idx -= 1
        return True

    def _get_attr_chain(self, node: Any) -> list[str] | None:
        """
        Given an ast.Attribute or ast.Name, return the chain as a list.

        Stops at 'self' and returns None if it doesn't start with self.
        Example:
            self.x.y.z --> ['self', 'x', 'y', 'z']
            other_var --> None
        """
        chain = []
        while True:
            if isinstance(node, ast.Attribute):
                chain.append(node.attr)
                node = node.value
            elif isinstance(node, ast.Name):
                chain.append(node.id)
                break
            else:
                return None  # unexpected type
        chain.reverse()
        return chain

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

    def _get_python_function_name(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> tuple[str, bool]:
        """
        Determine if a Python function defines a Robot keyword.

        Returns the keyword name if found, else None.
        """
        parts = func.name.replace("_", " ").split()
        parts = [p.capitalize() for p in parts]
        rf_keyword_name = " ".join(parts)
        for d in func.decorator_list:
            if isinstance(d, ast.Name) and d.id == "keyword":
                return rf_keyword_name, True

        return rf_keyword_name, False

    def start_keyword(self, data, result) -> None:
        """
        Remove the keyword from the unused list when it is used.
        """
        curr = data.name.strip()
        queue = deque([curr])
        while len(queue) > 0:
            name = queue.popleft()
            if any(name.startswith(f"{cls}.") for cls in self.classes):
                cls_name, func_name = name.split(".", 1)

            else:
                func_name = name
                cls_name = None

            exact_func_name = self._get_exact_func_name(func_name, cls_name)
            if exact_func_name is None:
                continue

            func_info = self.functions.pop(exact_func_name)
            self._prune_deps(exact_func_name, func_info["class"])
            for dep in func_info["dependencies"]:
                queue.append(dep)

    def _prune_deps(self, exact_func_name: str, cls_name: str) -> None:
        """
        Prune dependencies with exact_func_name in all functions dependencies.
        """

        for kw_name in self.functions:
            if exact_func_name not in self.functions[kw_name]["dependencies"]:
                continue

            if (
                self.functions[kw_name]["dependencies"][exact_func_name][
                    "class"
                ]
                == cls_name
            ):
                del self.functions[kw_name]["dependencies"][exact_func_name]

    def _get_exact_func_name(self, name: str, cls_name: str) -> str:
        """
        Get exact function name from given name, even the given name is
        embedded.
        """
        # Exact match
        if name in self.functions:
            # If class name provided, we also check that.
            if cls_name and self.functions[name]["class"] == cls_name:
                return name
            return name

        # Embedded keyword
        for kw in self.functions:
            if not self._regex_matches_keyword(name, kw):
                continue

            if cls_name and self.functions[name]["class"] == cls_name:
                return kw
            return kw

        return None

    def close(self) -> None:
        """
        Dump a json for unused keywords when the suite ends.
        """
        with self.unused_file.open("w", encoding=ENCODING) as f:
            json.dump(self.functions, f, indent=2, ensure_ascii=False)

        _logger.info(f"Saved unused keywords to {self.unused_file}")
