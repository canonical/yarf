"""
Check that test suites take SSH credentials from the command line.

A suite must pass the credentials of SSHLibrary login keywords as variables
given with Robot Framework's ``--variable`` or ``--variablefile`` options, so
that credentials are never stored in the suite itself. Only the suite's
``.robot`` files and the resource files they import are checked.
"""

import getpass
from pathlib import Path

from owasp_logger import OWASPLogger
from robot.api.parsing import ModelVisitor, get_model, get_resource_model
from robot.errors import DataError
from robot.parsing.model.statements import (
    Fixture,
    KeywordCall,
    LibraryImport,
    ResourceImport,
)
from robot.utils import normalize, split_args_from_name_or_path
from robot.variables import Variables, contains_variable, search_variable

from yarf.errors.yarf_errors import YARFCredentialError
from yarf.loggers.owasp_logger import get_owasp_logger

_owasp_logger = OWASPLogger(appid=__name__, logger=get_owasp_logger())

SSH_LIBRARY = "SSHLibrary"
CREDENTIAL_PARAMS = ("username", "password", "keyfile")
# Parameters of the SSHLibrary 3.8 login keywords, in signature order.
LOGIN_KEYWORD_PARAMS = {
    "login": (
        "username",
        "password",
        "allow_agent",
        "look_for_keys",
        "delay",
        "proxy_cmd",
        "read_config",
        "jumphost_index_or_alias",
        "keep_alive_interval",
    ),
    "loginwithpublickey": (
        "username",
        "keyfile",
        "password",
        "allow_agent",
        "look_for_keys",
        "delay",
        "proxy_cmd",
        "jumphost_index_or_alias",
        "read_config",
        "keep_alive_interval",
    ),
}


class _KeywordCallCollector(ModelVisitor):
    """
    Collect the names SSHLibrary is imported under, the imported resource files
    and all keyword calls, with their arguments and line numbers, of a suite
    file.
    """

    def __init__(self) -> None:
        self.aliases: set[str] = set()
        self.resources: list[str] = []
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def visit_LibraryImport(self, node: LibraryImport) -> None:
        """
        Record the name SSHLibrary is imported under.

        Args:
            node: The library import statement.
        """
        if node.name == SSH_LIBRARY:
            self.aliases.add(normalize(node.alias or SSH_LIBRARY))

    def visit_ResourceImport(self, node: ResourceImport) -> None:
        """
        Record the path of an imported resource file.

        Args:
            node: The resource import statement.
        """
        self.resources.append(node.name)

    def visit_KeywordCall(self, node: KeywordCall) -> None:
        """
        Record a keyword call in a test or keyword body, and the resource file
        of an ``Import Resource`` call.

        Args:
            node: The keyword call statement.
        """
        self.calls.append((node.keyword, node.args, node.lineno))
        name = node.keyword.rpartition(".")[2]
        if normalize(name, ignore="_") == "importresource" and node.args:
            self.resources.append(node.args[0])

    def visit_Fixture(self, node: Fixture) -> None:
        """
        Record a keyword call in a setup or teardown.

        Args:
            node: The setup or teardown statement.
        """
        self.calls.append((node.name, node.args, node.lineno))


def _login_params(keyword: str, aliases: set[str]) -> tuple[str, ...]:
    """
    Get the parameters of an SSHLibrary login keyword.

    Args:
        keyword: The name of the called keyword.
        aliases: Normalized names under which SSHLibrary is imported.

    Returns:
        The keyword parameters, or an empty tuple if the call is not an
        SSHLibrary login keyword.
    """
    prefix, _, name = keyword.rpartition(".")
    if prefix:
        if normalize(prefix) not in aliases | {normalize(SSH_LIBRARY)}:
            return ()
    elif not aliases:
        return ()

    return LOGIN_KEYWORD_PARAMS.get(normalize(name, ignore="_"), ())


def _credential_args(
    params: tuple[str, ...], args: tuple[str, ...]
) -> dict[str, str]:
    """
    Map the arguments of a login keyword call to its credential parameters.

    Args:
        params: The keyword parameters, in signature order.
        args: The arguments of the keyword call.

    Returns:
        The credential parameters given in the call and their arguments.
    """
    credentials = {}
    for index, arg in enumerate(args):
        name, sep, value = arg.partition("=")
        if not (sep and name in params):
            if index >= len(params):
                break
            name, value = params[index], arg

        if name in CREDENTIAL_PARAMS:
            credentials[name] = value

    return credentials


def _is_cli_variable(arg: str, cli_names: set[str]) -> bool:
    """
    Check whether an argument is only a variable given on the command line.

    Args:
        arg: The argument of the keyword call.
        cli_names: Normalized names of the command line variables.

    Returns:
        True if the argument is a command line variable, False otherwise.
    """
    match = search_variable(arg)
    return (
        match.is_variable()
        and match.identifier == "$"
        and not match.items
        and normalize(match.base, ignore="_") in cli_names
    )


def _cli_variable_names(
    cli_variables: list[str], cli_variable_files: list[str]
) -> set[str]:
    """
    Get the names of the variables given on the command line.

    Args:
        cli_variables: Variables given with ``--variable``, as
            ``NAME:value``.
        cli_variable_files: Variable files given with ``--variablefile``, as
            ``path`` or ``path:arg1:arg2``.

    Returns:
        The normalized variable names.
    """
    names = [variable.partition(":")[0] for variable in cli_variables]
    for variable_file in cli_variable_files:
        path, args = split_args_from_name_or_path(variable_file)
        try:
            names.extend(
                name for name, _ in Variables().set_from_file(path, args)
            )
        except DataError:
            # Robot reports the unreadable file when running the suite.
            continue

    return {normalize(name, ignore="_") for name in names}


def _collect_suite(suite_dir: Path) -> dict[Path, _KeywordCallCollector]:
    """
    Collect the keyword calls of the ``.robot`` files of a suite and of the
    resource files of the suite they import.

    Resource files outside the suite, such as platform resources, are not
    collected. If an import path has variables other than ``${CURDIR}`` and
    ``${/}``, all ``.resource`` files of the suite are collected.

    Args:
        suite_dir: The directory containing the suite files.

    Returns:
        The collectors of the suite files, by path relative to the suite
        directory.
    """
    suite_dir = suite_dir.resolve()
    pending = list(suite_dir.rglob("*.robot"))
    collectors: dict[Path, _KeywordCallCollector] = {}
    has_unresolved_import = False
    while pending:
        path = pending.pop()
        if path in collectors:
            continue

        parse = get_model if path.suffix == ".robot" else get_resource_model
        collector = _KeywordCallCollector()
        collector.visit(parse(path, curdir=str(path.parent)))
        collectors[path] = collector
        for name in collector.resources:
            name = name.replace("${/}", "/")
            resource = (path.parent / name).resolve()
            if contains_variable(name):
                if not has_unresolved_import:
                    has_unresolved_import = True
                    pending.extend(suite_dir.rglob("*.resource"))
            elif resource.is_file() and resource.is_relative_to(suite_dir):
                pending.append(resource)

    return {
        path.relative_to(suite_dir): collectors[path]
        for path in sorted(collectors)
    }


def check_ssh_credentials(
    suite_dir: Path,
    cli_variables: list[str],
    cli_variable_files: list[str],
) -> None:
    """
    Check that SSHLibrary login keywords in a suite take their credentials from
    the command line.

    Args:
        suite_dir: The directory containing the suite files.
        cli_variables: Variables given with ``--variable``, as
            ``NAME:value``.
        cli_variable_files: Variable files given with ``--variablefile``, as
            ``path`` or ``path:arg1:arg2``.

    Raises:
        YARFCredentialError: If a login keyword takes a credential that is
            not a variable given on the command line.
    """
    cli_names = _cli_variable_names(cli_variables, cli_variable_files)
    collectors = _collect_suite(suite_dir)

    aliases = set().union(*(c.aliases for c in collectors.values()))
    fields = set()
    errors = []
    for source, collector in collectors.items():
        for keyword, args, lineno in collector.calls:
            params = _login_params(keyword, aliases)
            for name, arg in _credential_args(params, args).items():
                if not _is_cli_variable(arg, cli_names):
                    fields.add(name)
                    errors.append(
                        f"{source}:{lineno}: '{keyword}' argument '{name}'"
                    )

    if errors:
        _owasp_logger.input_validation_fail(sorted(fields), getpass.getuser())
        raise YARFCredentialError(
            "SSH credentials must be variables given on the command line "
            "with '-- --variable NAME:value' or '-- --variablefile PATH':\n  "
            + "\n  ".join(errors)
        )
