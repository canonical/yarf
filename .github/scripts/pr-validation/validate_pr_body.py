"""
Check that every section of the PR template is present in the PR body.

The PR body is read from the ``PR_BODY`` environment variable. Template
comments left behind by the author are removed from the pull request, which
requires ``GITHUB_TOKEN``, ``REPO`` and ``PR_NUMBER`` to be set as well.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parents[2] / "pull_request_template.md"
HEADING = re.compile(r"\s*#{1,6}\s+.*?\s*$")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
BLANK_LINES = re.compile(r"\n{3,}")


def strip_comments(text: str) -> str:
    """
    Remove the HTML comments of a document and the gaps they leave behind.

    Args:
        text: The markdown document to clean up.

    Returns:
        The document without HTML comments.
    """
    text = COMMENT.sub("", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return BLANK_LINES.sub("\n\n", text).strip() + "\n"


def update_pr_body(body: str) -> None:
    """
    Replace the body of the pull request being validated.

    Args:
        body: The new pull request body.
    """
    request = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['REPO']}"
        f"/pulls/{os.environ['PR_NUMBER']}",
        method="PATCH",
        data=json.dumps({"body": body}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request):
        pass


def parse_sections(text: str) -> dict[str, list[str]]:
    """
    Map each markdown heading of a document to the lines below it.

    Args:
        text: The markdown document to parse.

    Returns:
        A mapping of heading, as written, to the lines that follow it.
    """
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if HEADING.match(line):
            current = []
            sections[line.strip()] = current
        elif current is not None:
            current.append(line)
    return sections


def main() -> int:
    """
    Report the template sections missing from or left empty in the PR body.

    Returns:
        0 if every template section is filled in, 1 otherwise.
    """
    body = os.environ.get("PR_BODY") or ""
    # The template is made of headings followed by HTML comments, so a section
    # only counts as filled in once the comments are gone.
    cleaned_body = strip_comments(body)
    if cleaned_body.strip() != body.strip():
        print("Removing the template comments left in the PR description.")
        update_pr_body(cleaned_body)

    template_sections = parse_sections(
        strip_comments(TEMPLATE_PATH.read_text(encoding="utf-8"))
    )
    body_sections = parse_sections(cleaned_body)

    errors = []
    for heading in template_sections:
        if heading not in body_sections:
            errors.append(f"Missing '{heading}' section.")
        elif not "".join(body_sections[heading]).strip():
            errors.append(f"Section '{heading}' is empty.")

    if errors:
        print("\n".join(errors))
        print(
            "Please fill in the pull request template "
            "(.github/pull_request_template.md)."
        )
        return 1

    print("All PR template sections are present and filled in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
