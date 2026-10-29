#!/usr/bin/env python3
"""
Copy a Spec Kit draft into requirements/ under the next free feature number.

Spec Kit writes a feature's working file as specs/NNN-slug/spec.md and
numbers it from specs/, which is empty in a fresh checkout, so its
number can already belong to a feature under requirements/. This copies
the draft to requirements/MMM-slug/requirements.md, where MMM is the
draft's number when it is free and the next free number otherwise. It
never overwrites a file and leaves the specs/ working files in place.
The rewrite into the format of requirements/AGENTS.md and the `git add`
are left to the person or agent delivering the feature.

This is the host side of `make adopt-spec`. It uses only the standard
library.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

FEATURE_DIRECTORY = re.compile(
    r"^(?P<number>[0-9]{3,})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)
EXISTING_FEATURE_DIRECTORY = re.compile(r"^(?P<number>[0-9]+)-")


class AdoptError(Exception):
    """
    The draft cannot be copied, with the reason in plain words.
    """


def feature_source(
    repo_root: Path, feature_directory: str
) -> tuple[Path, str, int]:
    """
    Resolve and validate a direct child of the local specs working directory.
    """
    raw_path = Path(feature_directory)
    candidate = raw_path if raw_path.is_absolute() else repo_root / raw_path
    specs_root = repo_root / "specs"
    if specs_root.is_symlink():
        raise AdoptError(
            "specs must be a normal local directory, not a symlink"
        )
    try:
        specs_resolved = specs_root.resolve(strict=True)
        source = candidate.resolve(strict=True)
    except OSError as error:
        raise AdoptError(
            f"feature directory does not exist: {candidate}"
        ) from error

    if not specs_resolved.is_dir():
        raise AdoptError(
            f"feature directory must be under the specs directory: {candidate}"
        )
    if (
        candidate.is_symlink()
        or source.parent != specs_resolved
        or not source.is_dir()
    ):
        raise AdoptError(
            "feature directory must be a direct, non-symlink child of specs/"
        )

    match = FEATURE_DIRECTORY.fullmatch(source.name)
    if match is None:
        raise AdoptError(
            "feature directory name must use NNN-lowercase-kebab-case"
        )

    spec_path = source / "spec.md"
    if spec_path.is_symlink() or not spec_path.is_file():
        raise AdoptError(
            f"feature directory must contain a regular spec.md file: {spec_path}"
        )
    number = int(match.group("number"))
    if number < 1:
        raise AdoptError("feature number must be positive")
    return spec_path, match.group("slug"), number


def used_feature_numbers(requirements_root: Path) -> set[int]:
    """
    Return numeric identifiers used by existing requirement entries.
    """
    if requirements_root.is_symlink():
        raise AdoptError(
            "requirements must be a normal directory, not a symlink"
        )
    if requirements_root.exists() and not requirements_root.is_dir():
        raise AdoptError("requirements exists but is not a directory")

    numbers: set[int] = set()
    if requirements_root.exists():
        for entry in requirements_root.iterdir():
            match = EXISTING_FEATURE_DIRECTORY.match(entry.name)
            if match:
                numbers.add(int(match.group("number")))
    return numbers


def adopt_spec(repo_root: Path, feature_directory: str) -> Path:
    """
    Copy a draft spec to a unique requirement path without overwriting files.
    """
    repo_root = repo_root.resolve(strict=True)
    if not repo_root.is_dir():
        raise AdoptError(f"repository root is not a directory: {repo_root}")

    source, slug, requested_number = feature_source(
        repo_root, feature_directory
    )
    requirements_root = repo_root / "requirements"
    used_numbers = used_feature_numbers(requirements_root)
    number = requested_number
    if number in used_numbers:
        number = max(used_numbers | {requested_number}) + 1

    while True:
        directory_name = f"{number:03d}-{slug}"
        destination_directory = requirements_root / directory_name
        destination = destination_directory / "requirements.md"
        if (
            number not in used_numbers
            and not destination_directory.exists()
            and not destination_directory.is_symlink()
        ):
            break
        number += 1

    requirements_root.mkdir(exist_ok=True)
    if requirements_root.is_symlink():
        raise AdoptError(
            "requirements must be a normal directory, not a symlink"
        )
    destination_directory.mkdir()
    try:
        with (
            source.open("rb") as source_file,
            destination.open("xb") as destination_file,
        ):
            destination_file.write(source_file.read())
    except OSError:
        try:
            destination.unlink(missing_ok=True)
            destination_directory.rmdir()
        except OSError:
            pass
        raise
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "feature_directory",
        help="a direct specs/NNN-feature-name directory containing spec.md",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (defaults to the repository containing this script)",
    )
    args = parser.parse_args(argv)

    try:
        destination = adopt_spec(args.repo, args.feature_directory)
    except (OSError, AdoptError) as error:
        print(f"adopt-spec: {error}", file=sys.stderr)
        return 1

    rel = destination.relative_to(args.repo.resolve()).as_posix()
    print(
        f"Copied the unedited Spec Kit draft to {rel}. The specs/ files remain local."
    )
    print(
        "This is not a requirements conversion. Rewrite and review it in the format"
    )
    print("requirements/AGENTS.md defines, then run:")
    print(f"  git add {rel}")
    print("  make check-requirements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
