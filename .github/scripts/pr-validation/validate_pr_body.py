"""
Check that every section of the PR template is present in the PR body.

The PR body is read from the ``PR_BODY`` environment variable. Comments coming
from the template and left behind by the author are removed from the pull
request, which requires ``GITHUB_TOKEN``, ``REPO`` and ``PR_NUMBER`` to be set
as well.
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
FENCE = re.compile(r"\s*(?P<fence>`{3,}|~{3,})")
BLANK_LINES = re.compile(r"\n{3,}")


def parse_comments(text: str) -> list[str]:
    """
    List the HTML comments of a document.

    Args:
        text: The markdown document to parse.

    Returns:
        The comments, as written.
    """
    return COMMENT.findall(text)


def strip_comments(text: str, comments: list[str]) -> str:
    """
    Remove specific HTML comments and the gaps they leave behind.

    Args:
        text: The markdown document to clean up.
        comments: The comments to remove, as written.

    Returns:
        The document without the given comments.
    """
    for comment in comments:
        text = text.replace(comment, "")
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


def parse_headings(text: str) -> list[str]:
    """
    List the markdown headings of a document, ignoring fenced code blocks.

    Args:
        text: The markdown document to parse.

    Returns:
        The headings, as written.
    """
    headings = []
    fence = ""
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            marker = match.group("fence")
            if not fence:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = ""
        elif not fence and HEADING.match(line):
            headings.append(line.strip())
    return headings


def main() -> int:
    """
    Report the template sections missing from the PR body.

    Returns:
        0 if every template section is present, 1 otherwise.
    """
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    body = os.environ.get("PR_BODY") or ""
    cleaned_body = strip_comments(body, parse_comments(template))
    if cleaned_body.strip() != body.strip():
        print("Removing the template comments left in the PR description.")
        update_pr_body(cleaned_body)

    template_headings = parse_headings(template)
    body_headings = set(parse_headings(cleaned_body))

    missing = [
        heading
        for heading in template_headings
        if heading not in body_headings
    ]
    if missing:
        for heading in missing:
            print(f"Missing '{heading}' section.")
        print(
            "Please keep every section of the pull request template "
            "(.github/pull_request_template.md)."
        )
        return 1

    print("All PR template sections are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
