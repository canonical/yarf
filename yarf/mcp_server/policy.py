"""
Guardrails restricting what an LLM may execute through the MCP server.

The LLM only gets GUI-level control: the keywords of the platform libraries
and resources, plus a few harmless BuiltIn keywords. Anything able to run code
or touch the host (``Evaluate``, ``Run Process``, ``Import Library``, ...) is
refused, including through Robot Framework's variable syntax.
"""

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from robot.errors import VariableError
from robot.utils import normalize
from robot.variables.search import VariableMatches

from yarf.errors.yarf_errors import KeywordNotAllowedError

BUILTIN_OWNER = "BuiltIn"
DEFAULT_ALLOWED_BUILTIN_KEYWORDS = frozenset(
    normalize(name, ignore=" _")
    for name in (
        "Log",
        "Should Be Equal",
        "Should Be Equal As Strings",
        "Should Contain",
        "Should Not Contain",
        "Sleep",
    )
)
# Plain names only: `${{python}}`, `${obj.attr}` and `${1+1}` evaluate code.
SAFE_VARIABLE_NAME = re.compile(r"[A-Za-z0-9_ ]+")
SAFE_VARIABLE_IDENTIFIERS = frozenset("$@&")


def validate_argument(text: str) -> None:
    """
    Check that a keyword name or argument cannot execute code or read the host
    environment through Robot Framework variable syntax.

    Args:
        text: keyword name or argument, in Robot Framework syntax

    Raises:
        KeywordNotAllowedError: if the text uses a forbidden variable syntax
    """
    try:
        matches = list(VariableMatches(text))
    except VariableError as e:
        raise KeywordNotAllowedError(f"Malformed variable syntax: {e}")

    for match in matches:
        if (
            match.identifier not in SAFE_VARIABLE_IDENTIFIERS
            or not SAFE_VARIABLE_NAME.fullmatch(match.base)
        ):
            raise KeywordNotAllowedError(
                f"Variable syntax '{match.name}' is not allowed, only plain "
                "variables such as ${NAME} are."
            )
        for item in match.items:
            validate_argument(item)


@dataclass(frozen=True)
class KeywordPolicy:
    """
    Decide which keywords an LLM may run.

    Attributes:
        allowed_owners: names of the libraries and resources whose keywords
            are allowed, typically the platform ones
        allowed_builtin: normalized names of the allowed BuiltIn keywords
    """

    allowed_owners: frozenset[str]
    allowed_builtin: frozenset[str] = DEFAULT_ALLOWED_BUILTIN_KEYWORDS

    def is_allowed(self, owner: Optional[str], keyword: str) -> bool:
        """
        Tell if a keyword is allowed.

        Args:
            owner: name of the library or resource defining the keyword
            keyword: name of the keyword

        Returns:
            True if the keyword may be run by the LLM
        """
        if owner == BUILTIN_OWNER:
            return normalize(keyword, ignore=" _") in self.allowed_builtin

        return owner in self.allowed_owners

    def check(
        self, owner: Optional[str], keyword: str, arguments: Iterable[str]
    ) -> None:
        """
        Check a keyword call.

        Args:
            owner: name of the library or resource defining the keyword
            keyword: name of the keyword
            arguments: arguments of the call, in Robot Framework syntax

        Raises:
            KeywordNotAllowedError: if the keyword or its arguments are not
                allowed
        """
        if not self.is_allowed(owner, keyword):
            raise KeywordNotAllowedError(
                f"Keyword '{keyword}' of '{owner}' is not allowed. Use "
                "`search_keywords` to see the keywords you can run."
            )

        for text in (keyword, *arguments):
            validate_argument(text)
