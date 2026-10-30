import importlib.util
import io
import json
import urllib.error
import urllib.request
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "validate_pr_body.py"


def load_script() -> ModuleType:
    """
    Import the validation script, which is not part of a package.
    """
    spec = importlib.util.spec_from_file_location(
        "validate_pr_body", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_pr_body = load_script()
TEMPLATE = validate_pr_body.TEMPLATE_PATH.read_text(encoding="utf-8")
COMMENTS = validate_pr_body.parse_comments(TEMPLATE)
# Every template section filled in, without any template comment.
FILLED_BODY = validate_pr_body.strip_comments(TEMPLATE, COMMENTS).replace(
    "\n\n", "\n\nSome text.\n\n"
)


@pytest.fixture
def urlopen(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """
    Replace urlopen so that no request reaches the GitHub API.
    """
    mock = MagicMock()
    monkeypatch.setattr(urllib.request, "urlopen", mock)
    return mock


def run(monkeypatch: pytest.MonkeyPatch, body: str) -> int:
    """
    Run the script against the given PR body.

    Args:
        monkeypatch: fixture used to set the environment.
        body: the PR body to validate.

    Returns:
        The exit code of the script.
    """
    monkeypatch.setenv("PR_BODY", body)
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("REPO", "canonical/yarf")
    return validate_pr_body.main()


def forbidden(request: urllib.request.Request) -> None:
    """
    Reject the request like GitHub does with the read-only token of forks.

    Args:
        request: the rejected request.

    Raises:
        HTTPError: always.
    """
    raise urllib.error.HTTPError(
        request.full_url, 403, "Forbidden", MagicMock(), io.BytesIO()
    )


def test_template_sections_are_found() -> None:
    """
    Test that the template has sections to validate.
    """
    assert validate_pr_body.parse_headings(TEMPLATE)
    assert COMMENTS


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_body_without_comments_is_not_updated(
    monkeypatch: pytest.MonkeyPatch, urlopen: MagicMock, newline: str
) -> None:
    """
    Test that a body without template comments is not updated, even when
    whitespace normalization changes it (CRLF line endings, trailing spaces).
    """
    body = FILLED_BODY.replace("Some text.", "Some text. ")
    assert run(monkeypatch, body.replace("\n", newline)) == 0
    urlopen.assert_not_called()


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_leftover_comments_are_removed(
    monkeypatch: pytest.MonkeyPatch, urlopen: MagicMock, newline: str
) -> None:
    """
    Test that leftover template comments are removed from the PR body,
    including multi-line comments in bodies using CRLF line endings.
    """
    assert run(monkeypatch, TEMPLATE.replace("\n", newline)) == 0

    urlopen.assert_called_once()
    request = urlopen.call_args.args[0]
    assert request.get_method() == "PATCH"
    assert request.full_url == (
        "https://api.github.com/repos/canonical/yarf/pulls/42"
    )
    assert request.get_header("Authorization") == "Bearer token"
    new_body = json.loads(request.data)["body"]
    assert "<!--" not in new_body
    assert "\r" not in new_body
    assert validate_pr_body.parse_headings(new_body) == (
        validate_pr_body.parse_headings(TEMPLATE)
    )


def test_update_failure_is_not_fatal(
    monkeypatch: pytest.MonkeyPatch,
    urlopen: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Test that failing to update the PR body, as with the read-only token of
    pull requests from forks, does not fail the validation.
    """
    urlopen.side_effect = forbidden

    assert run(monkeypatch, TEMPLATE) == 0

    urlopen.assert_called_once()
    output = capsys.readouterr().out
    assert "Could not update the PR description (HTTP 403)" in output
    assert "All PR template sections are present." in output


def test_update_failure_does_not_hide_missing_sections(
    monkeypatch: pytest.MonkeyPatch,
    urlopen: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Test that sections are still validated when updating the PR body fails.
    """
    urlopen.side_effect = forbidden

    assert run(monkeypatch, TEMPLATE.split("## Tests")[0]) == 1

    assert "Missing '## Tests' section." in capsys.readouterr().out


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_missing_section_fails(
    monkeypatch: pytest.MonkeyPatch,
    urlopen: MagicMock,
    capsys: pytest.CaptureFixture[str],
    newline: str,
) -> None:
    """
    Test that a body missing a template section fails the validation.
    """
    body = FILLED_BODY.split("## Tests")[0].replace("\n", newline)

    assert run(monkeypatch, body) == 1

    urlopen.assert_not_called()
    assert "Missing '## Tests' section." in capsys.readouterr().out


def test_missing_body_fails(
    monkeypatch: pytest.MonkeyPatch, urlopen: MagicMock
) -> None:
    """
    Test that an empty PR body fails the validation.
    """
    monkeypatch.delenv("PR_BODY", raising=False)

    assert validate_pr_body.main() == 1

    urlopen.assert_not_called()
