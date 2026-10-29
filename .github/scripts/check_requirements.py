#!/usr/bin/env python3
"""
Fail when the tracked requirements tree breaks requirements/AGENTS.md.

Spec Kit writes a feature's working file as specs/NNN-slug/spec.md, with its
plan, task list, and checklists beside it. `.gitignore` keeps all of that
untracked, and the draft is rewritten into requirements/NNN-slug/requirements.md
before it is committed (requirements/AGENTS.md).

This check reports what the ignore rule cannot prevent: a file added with
`git add -f`, anything tracked under specs/, an ancillary file or a malformed
feature directory under requirements/, a duplicate feature number, and a
requirements.md that does not follow the documented sections, user stories,
EARS requirements, and measurable success criteria. It reads the Git index, so
a Spec Kit run or an unstaged edit in the working tree does not change the
result.

This is the host side of `make check-requirements`, which the requirements
workflow also runs. It uses only the standard library.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

FEATURE_DIRECTORY = re.compile(
    r"^(?P<number>[0-9]{3,})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)
STORY_CANDIDATE = re.compile(r"^### US-")
STORY_HEADING = re.compile(
    r"^### US-(?P<number>[0-9]{2,}): .+ \(Priority: P[1-5]\)$"
)
USER_STORY = re.compile(r"^As .+, I want .+, so that .+$")
ACCEPTANCE_SCENARIO = re.compile(
    r"^- \*\*Given\*\* .+, \*\*When\*\* .+, \*\*Then\*\* .+$"
)
FR_CANDIDATE = re.compile(r"^\s*-\s+(?:\*\*)?FR-")
FR_LINE = re.compile(
    r"^- \*\*FR-(?P<number>[0-9]{3})\*\*: "
    r"(?:The system MUST(?: NOT)? .+|"
    r"When .+, the system MUST(?: NOT)? .+|"
    r"While .+, the system MUST(?: NOT)? .+|"
    r"Where .+, the system MUST(?: NOT)? .+|"
    r"If .+, then the system MUST(?: NOT)? .+)\.?$"
)
SC_CANDIDATE = re.compile(r"^\s*-\s+(?:\*\*)?SC-")
SC_LINE = re.compile(r"^- \*\*SC-(?P<number>[0-9]{3})\*\*: (?P<text>.+)$")
MEASUREMENT = re.compile(
    r"(?<![A-Za-z0-9-])-?[0-9]+(?:\.[0-9]+)?(?:\s*|-)(?:%|(?:[^\W\d_]+|[°µμ][^\W\d_]+)(?:[-/][^\W\d_]+)*)",
    re.IGNORECASE,
)
REQUIRED_HEADINGS = (
    "# Requirements:",
    "## Context",
    "## User Stories",
    "## Functional Requirements",
    "## Success Criteria",
)


class GitError(Exception):
    """
    Git could not read the repository or its index.
    """


def run_git(repo_root: Path, *args: str) -> bytes:
    """
    Return the output of a git command, raising GitError when it fails.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except OSError as error:
        raise GitError(str(error)) from error
    except subprocess.CalledProcessError as error:
        details = error.stderr.decode(errors="replace").strip()
        raise GitError(
            details or f"git {' '.join(args)} failed in {repo_root}"
        ) from error
    return result.stdout


def logical_lines(text: str) -> list[str]:
    """
    Join Markdown soft wraps without crossing headings, lists, or blanks.
    """
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            lines.append("")
            continue
        if line.startswith("#") or line.startswith("- "):
            lines.append(line)
            continue
        if lines and lines[-1] and not lines[-1].startswith("#"):
            lines[-1] = f"{lines[-1]} {line.lstrip()}"
        else:
            lines.append(line)
    return lines


def tracked_index_entries(
    repo_root: Path,
) -> dict[str, tuple[str, str] | None]:
    """
    Return stage-0 index paths with their modes and object IDs.

    A path with a conflict or a duplicate entry maps to None.
    """
    entries: dict[str, tuple[str, str] | None] = {}
    for record in run_git(repo_root, "ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", maxsplit=1)
        mode, object_id, stage = metadata.split()
        decoded_path = path.decode("utf-8", errors="surrogateescape")
        if decoded_path in entries or stage != b"0":
            entries[decoded_path] = None
        else:
            entries[decoded_path] = (
                mode.decode("ascii"),
                object_id.decode("ascii"),
            )
    return entries


def check_document(repo_root: Path, path: str, object_id: str) -> list[str]:
    """
    Problems in the sections, stories, EARS requirements, and criteria of one
    document.
    """
    problems: list[str] = []
    try:
        text = run_git(repo_root, "cat-file", "blob", object_id).decode(
            "utf-8"
        )
    except (GitError, UnicodeError) as error:
        return [
            f"{path}: cannot read UTF-8 requirements document from the Git index: {error}"
        ]

    lines = logical_lines(text)
    for heading in REQUIRED_HEADINGS:
        present = (
            bool(lines and re.fullmatch(r"# Requirements: .+", lines[0]))
            if heading == "# Requirements:"
            else heading in lines
        )
        if not present:
            problems.append(f"{path}: missing required heading {heading!r}")

    if not lines or not re.fullmatch(r"# Requirements: .+", lines[0]):
        problems.append(
            f"{path}: first line must be '# Requirements: <feature name>'"
        )

    section_positions = [
        next(
            (index for index, line in enumerate(lines) if line == heading), -1
        )
        for heading in (
            "## Context",
            "## User Stories",
            "## Functional Requirements",
            "## Success Criteria",
        )
    ]
    present_positions = [
        position for position in section_positions if position >= 0
    ]
    if present_positions != sorted(present_positions):
        problems.append(
            f"{path}: required sections must follow the documented order"
        )

    user_story_start = next(
        (
            index
            for index, line in enumerate(lines)
            if line == "## User Stories"
        ),
        -1,
    )
    user_story_end = next(
        (
            index
            for index in range(user_story_start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    story_section = lines[user_story_start + 1 : user_story_end]
    story_positions = []
    for index, line in enumerate(story_section):
        if STORY_CANDIDATE.match(line) is None:
            continue
        story_match = STORY_HEADING.fullmatch(line)
        if story_match is None:
            problems.append(
                f"{path}: malformed user story heading {line!r}; expected "
                "'### US-NN: <title> (Priority: PN)'"
            )
            continue
        story_positions.append((user_story_start + 1 + index, story_match))
    if not story_positions:
        problems.append(
            f"{path}: add at least one '### US-NN: ... (Priority: PN)' user story"
        )
    story_numbers: set[str] = set()
    for story_index, story_match in story_positions:
        assert story_match is not None
        number = story_match.group("number")
        if number in story_numbers:
            problems.append(f"{path}: duplicate US-{number}")
        story_numbers.add(number)
        end = next(
            (
                index
                for index in range(story_index + 1, len(lines))
                if lines[index].startswith("## ")
                or lines[index].startswith("### ")
            ),
            len(lines),
        )
        story_body = lines[story_index + 1 : end]
        if not any(USER_STORY.fullmatch(line) for line in story_body):
            problems.append(
                f"{path}: US-{number} needs an 'As ..., I want ..., so that ...' statement"
            )
        if not any(ACCEPTANCE_SCENARIO.fullmatch(line) for line in story_body):
            problems.append(
                f"{path}: US-{number} needs a Given/When/Then acceptance scenario"
            )

    functional_start = next(
        (
            index
            for index, line in enumerate(lines)
            if line == "## Functional Requirements"
        ),
        -1,
    )
    success_start = next(
        (
            index
            for index, line in enumerate(lines)
            if line == "## Success Criteria"
        ),
        len(lines),
    )
    fr_lines = [
        line
        for line in lines[max(functional_start + 1, 0) : success_start]
        if FR_CANDIDATE.match(line)
    ]
    fr_numbers: set[str] = set()
    for line in fr_lines:
        match = FR_LINE.fullmatch(line)
        if match is None:
            problems.append(
                f"{path}: functional requirement must use a numbered EARS form, got {line!r}"
            )
            continue
        number = match.group("number")
        if number in fr_numbers:
            problems.append(f"{path}: duplicate FR-{number}")
        fr_numbers.add(number)
    if not fr_lines:
        problems.append(
            f"{path}: add at least one EARS functional requirement (FR-NNN)"
        )

    success_end = next(
        (
            index
            for index in range(success_start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    sc_lines = [
        line
        for line in lines[success_start + 1 : success_end]
        if SC_CANDIDATE.match(line)
    ]
    sc_numbers: set[str] = set()
    for line in sc_lines:
        match = SC_LINE.fullmatch(line)
        if match is None:
            problems.append(
                f"{path}: success criterion must use '- **SC-NNN**: ...', got {line!r}"
            )
            continue
        number = match.group("number")
        if number in sc_numbers:
            problems.append(f"{path}: duplicate SC-{number}")
        sc_numbers.add(number)
        criterion = match.group("text")
        if MEASUREMENT.search(criterion) is None:
            problems.append(
                f"{path}: SC-{number} needs a concrete numeric measure and unit or percentage"
            )
    if not sc_lines:
        problems.append(
            f"{path}: add at least one measurable success criterion (SC-NNN)"
        )

    if re.search(
        r"\[(?:NEEDS CLARIFICATION(?::[^\]]*)?|FEATURE NAME|DATE|"
        r"PLACEHOLDER(?:[^\]]*)?|ASSUMPTION(?:[^\]]*)?|ADD(?:\s+[^\]]*)?)\](?!\()",
        text,
        re.IGNORECASE,
    ):
        problems.append(
            f"{path}: replace Spec Kit placeholders and unresolved clarification markers"
        )
    return problems


def check_repository(repo_root: Path) -> list[str]:
    """
    Problems among the files Git tracks.

    An empty list means it is compliant.
    """
    index_entries = tracked_index_entries(repo_root)
    paths = set(index_entries)
    problems: list[str] = []
    policy_path = "requirements/AGENTS.md"
    policy_entry = index_entries.get(policy_path)
    if policy_entry is None:
        problems.append(
            f"{policy_path}: required policy file is missing from the Git index"
        )
    elif policy_entry[0] not in ("100644", "100755"):
        problems.append(
            f"{policy_path}: required policy file must be a regular file in the Git index"
        )

    requirement_paths = {
        path
        for path in paths
        if path == "requirements" or path.startswith("requirements/")
    }
    for path in paths:
        if path == "specs" or path.startswith("specs/"):
            problems.append(
                f"tracked generated Spec Kit file is forbidden: {path}"
            )

    feature_directories: set[str] = set()
    for path in sorted(requirement_paths):
        if path == policy_path:
            continue
        parts = path.split("/")
        if len(parts) != 3 or parts[0] != "requirements":
            problems.append(
                f"tracked ancillary requirements file is forbidden: {path} "
                "(only requirements/<NNN-slug>/requirements.md is allowed)"
            )
            continue
        directory, filename = parts[1], parts[2]
        if FEATURE_DIRECTORY.fullmatch(directory) is None:
            problems.append(f"invalid requirements feature directory: {path}")
            continue
        feature_directories.add(directory)
        if filename != "requirements.md":
            problems.append(
                f"tracked ancillary requirements file is forbidden: {path} "
                "(only requirements.md is allowed in a feature directory)"
            )

    feature_ids: dict[int, str] = {}
    for directory in sorted(feature_directories):
        feature_id = int(directory.split("-", maxsplit=1)[0])
        if feature_id == 0:
            problems.append(
                f"requirements feature ID must be positive: {directory}"
            )
        if feature_id in feature_ids:
            problems.append(
                f"duplicate requirements feature ID {feature_id:03d}: "
                f"{feature_ids[feature_id]} and {directory}"
            )
        feature_ids[feature_id] = directory

        relative_path = f"requirements/{directory}/requirements.md"
        if relative_path not in requirement_paths:
            problems.append(
                f"requirements feature directory is missing {relative_path}"
            )
            continue
        index_entry = index_entries.get(relative_path)
        if index_entry is None:
            problems.append(
                f"{relative_path}: requirement must have a stage-0 Git index entry"
            )
            continue
        mode, object_id = index_entry
        if mode not in ("100644", "100755"):
            problems.append(
                f"{relative_path}: tracked requirement must be a regular file in the Git index"
            )
            continue
        problems.extend(check_document(repo_root, relative_path, object_id))

    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (defaults to the repository containing this script)",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo.resolve()

    try:
        top_level = (
            run_git(repo_root, "rev-parse", "--show-toplevel").decode().strip()
        )
        if Path(top_level).resolve() != repo_root:
            raise GitError(f"{repo_root} is not a Git repository root")
        problems = check_repository(repo_root)
        count = sum(
            path.startswith("requirements/")
            and path.endswith("/requirements.md")
            for path in tracked_index_entries(repo_root)
        )
    except GitError as error:
        print(f"git could not read the repository: {error}", file=sys.stderr)
        return 2
    if problems:
        print(
            "requirements/ must follow requirements/AGENTS.md:",
            file=sys.stderr,
        )
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(
        f"requirements/: {count} tracked feature contract(s) follow requirements/AGENTS.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
