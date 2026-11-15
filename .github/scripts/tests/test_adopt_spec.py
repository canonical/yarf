"""
.github/scripts/adopt_spec.py: copying a Spec Kit draft into requirements/.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
import adopt_spec as adopter  # noqa: E402


class AdoptSpecTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write(self, relative_path: str, content: str = "") -> Path:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_adopter_rejects_malformed_feature_input(self):
        self.write("specs/007-console-status/not-a-spec.md", "draft")

        with self.assertRaisesRegex(adopter.AdoptError, "regular spec.md"):
            adopter.adopt_spec(self.repo, "specs/007-console-status")

    def test_adopter_rejects_feature_outside_specs(self):
        (self.repo / "specs").mkdir()
        self.write("outside/007-console-status/spec.md", "draft")

        with self.assertRaisesRegex(
            adopter.AdoptError, "direct, non-symlink child"
        ):
            adopter.adopt_spec(self.repo, "outside/007-console-status")

    def test_adoption_cli_reports_human_rewrite_requirement(self):
        self.write("specs/007-console-status/spec.md", "generated draft")
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = adopter.main(
                ["--repo", str(self.repo), "specs/007-console-status"]
            )

        self.assertEqual(0, result)
        self.assertIn(
            "This is not a requirements conversion", output.getvalue()
        )
        self.assertIn(
            "git add requirements/007-console-status/requirements.md",
            output.getvalue(),
        )
        self.assertIn("make check-requirements", output.getvalue())
        self.assertTrue(
            (self.repo / "specs/007-console-status/spec.md").is_file()
        )

    def test_adopter_resolves_numeric_conflict_without_overwriting(self):
        source = self.write(
            "specs/007-console-status/spec.md", "# Unedited generated draft\n"
        )
        original = self.write(
            "requirements/007-existing-feature/requirements.md", "existing"
        )

        destination = adopter.adopt_spec(self.repo, "specs/007-console-status")

        self.assertEqual(
            Path("requirements/008-console-status/requirements.md"),
            destination.relative_to(self.repo),
        )
        self.assertEqual("existing", original.read_text(encoding="utf-8"))
        self.assertEqual(
            "# Unedited generated draft\n",
            destination.read_text(encoding="utf-8"),
        )
        self.assertTrue(
            source.is_file(),
            "adoption must preserve the local generated working file",
        )

    def test_adoption_cli_reports_a_draft_that_cannot_be_copied(self):
        (self.repo / "specs").mkdir()
        error = io.StringIO()

        with contextlib.redirect_stderr(error):
            result = adopter.main(
                ["--repo", str(self.repo), "specs/007-console-status"]
            )

        self.assertEqual(1, result)
        self.assertIn(
            "adopt-spec: feature directory does not exist", error.getvalue()
        )


if __name__ == "__main__":
    unittest.main()
