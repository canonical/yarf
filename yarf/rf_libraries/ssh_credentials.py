"""
Check that test suites take SSH credentials from the command line.

A suite must pass the credentials of SSHLibrary login keywords as variables
given with Robot Framework's ``--variable`` option, so that credentials are
never stored in the suite itself.
"""

import getpass
from pathlib import Path

from owasp_logger import OWASPLogger
from robot.api.parsing import ModelVisitor, get_model, get_resource_model
from robot.parsing.model.statements import (
    Fixture,
    KeywordCall,
    LibraryImport,
)
from robot.utils import normalize
from robot.variables import search_variable

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
    Collect the names SSHLibrary is imported under and all keyword calls, with
    their arguments and line numbers, of a suite file.
    """

    def __init__(self) -> None:
        self.aliases: set[str] = set()
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def visit_LibraryImport(self, node: LibraryImport) -> None:
        """
        Record the name SSHLibrary is imported under.

        Args:
            node: The library import statement.
        """
        if node.name == SSH_LIBRARY:
            self.aliases.add(normalize(node.alias or SSH_LIBRARY))

    def visit_KeywordCall(self, node: KeywordCall) -> None:
        """
        Record a keyword call in a test or keyword body.

        Args:
            node: The keyword call statement.
        """
        self.calls.append((node.keyword, node.args, node.lineno))

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


def check_ssh_credentials(suite_dir: Path, cli_variables: list[str]) -> None:
    """
    Check that SSHLibrary login keywords in a suite take their credentials from
    the command line.

    Args:
        suite_dir: The directory containing the suite files.
        cli_variables: Variables given with ``--variable``, as
            ``NAME:value``.

    Raises:
        YARFCredentialError: If a login keyword takes a credential that is
            not a variable given on the command line.
    """
    cli_names = {
        normalize(variable.partition(":")[0], ignore="_")
        for variable in cli_variables
    }
    collectors = {}
    for path in sorted(suite_dir.rglob("*")):
        if path.suffix == ".robot":
            model = get_model(path)
        elif path.suffix == ".resource":
            model = get_resource_model(path)
        else:
            continue

        collector = _KeywordCallCollector()
        collector.visit(model)
        collectors[path.relative_to(suite_dir)] = collector

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
            "with '-- --variable NAME:value':\n  " + "\n  ".join(errors)
        )
