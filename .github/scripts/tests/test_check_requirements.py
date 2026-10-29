"""
.github/scripts/check_requirements.py: checking the tracked requirements tree.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
import check_requirements as checker  # noqa: E402

VALID_REQUIREMENTS = """# Requirements: Console status

## Context
Operators need to see the state of the console connection.

## User Stories
### US-01: View console status (Priority: P1)
As an operator, I want to view the console state, so that I can diagnose the connection.
- **Given** the console is connected, **When** I request its status, **Then** its state is shown.

## Functional Requirements
- **FR-001**: When the console is connected, the system MUST report its state.

## Success Criteria
- **SC-001**: An operator can view console status within 2 seconds.
- **SC-002**: At least 90% of status requests return the current console state.
"""


class CheckRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary_directory.name)
        subprocess.run(["git", "init", "--quiet"], cwd=self.repo, check=True)
        subprocess.run(
            [
                "git",
                "config",
                "user.email",
                "requirements-test@example.invalid",
            ],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Requirements Test"],
            cwd=self.repo,
            check=True,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write(self, relative_path: str, content: str = "") -> Path:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def track(self, *relative_paths: str) -> None:
        subprocess.run(
            ["git", "add", "--", *relative_paths], cwd=self.repo, check=True
        )

    def add_valid_requirement(self) -> Path:
        self.write("requirements/AGENTS.md", "Requirements format\n")
        path = self.write(
            "requirements/001-console-status/requirements.md",
            VALID_REQUIREMENTS,
        )
        self.track("requirements")
        return path

    def test_valid_tracked_requirement_tree_passes(self):
        self.add_valid_requirement()

        self.assertEqual([], checker.check_repository(self.repo))

    def test_requirements_policy_file_must_be_tracked(self):
        self.add_valid_requirement()
        subprocess.run(
            ["git", "rm", "--cached", "--quiet", "requirements/AGENTS.md"],
            cwd=self.repo,
            check=True,
        )

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any(
                "required policy file is missing from the Git index" in error
                for error in errors
            )
        )

    def test_requirements_policy_file_must_be_regular_in_the_index(self):
        self.add_valid_requirement()
        policy = self.repo / "requirements/AGENTS.md"
        policy.unlink()
        policy.symlink_to("../not-a-policy")
        self.track("requirements/AGENTS.md")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any(
                "required policy file must be a regular file" in error
                for error in errors
            )
        )

    def test_untracked_specs_and_ancillary_files_are_not_checked(self):
        self.add_valid_requirement()
        self.write("specs/999-local-draft/spec.md", "local draft")
        self.write("requirements/001-console-status/plan.md", "local note")

        self.assertEqual([], checker.check_repository(self.repo))

    def test_unstaged_requirement_edit_does_not_change_validated_index_content(
        self,
    ):
        path = self.add_valid_requirement()
        path.write_text("# malformed working-tree edit\n", encoding="utf-8")

        self.assertEqual([], checker.check_repository(self.repo))

    def test_requirement_must_be_a_regular_file_in_the_index(self):
        path = self.add_valid_requirement()
        path.unlink()
        path.symlink_to("../AGENTS.md")
        self.track("requirements/001-console-status/requirements.md")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any(
                "must be a regular file in the Git index" in error
                for error in errors
            )
        )

    def test_tracked_specs_are_forbidden(self):
        self.add_valid_requirement()
        self.write("specs/999-old-feature/spec.md", "generated spec")
        self.track("specs")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any(
                "tracked generated Spec Kit file is forbidden" in error
                for error in errors
            )
        )

    def test_specify_workflow_run_state_is_ignored_but_definition_is_tracked(
        self,
    ):
        repository_root = Path(__file__).resolve().parents[3]
        self.write(".gitignore", (repository_root / ".gitignore").read_text())
        generated_paths = (
            ".specify/workflows/runs/feature/inputs.json",
            ".specify/workflows/runs/feature/state.json",
            ".specify/workflows/runs/feature/log.jsonl",
            ".specify/workflows/runs/feature/workflow.yml",
        )
        for path in generated_paths:
            self.write(path, "generated workflow state")
        definition = ".specify/workflows/speckit/workflow.yml"
        self.write(definition, "workflow definition")

        ignored = subprocess.run(
            ["git", "check-ignore", "--", *generated_paths],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(list(generated_paths), ignored.stdout.splitlines())

        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )
        tracked_paths = tracked.stdout.splitlines()
        self.assertIn(definition, tracked_paths)
        self.assertTrue(
            all(path not in tracked_paths for path in generated_paths)
        )

    def test_tracked_ancillary_requirements_file_is_forbidden(self):
        self.add_valid_requirement()
        self.write("requirements/001-console-status/plan.md", "not a contract")
        self.track("requirements/001-console-status/plan.md")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any(
                "tracked ancillary requirements file is forbidden" in error
                for error in errors
            )
        )

    def test_feature_ids_must_be_unique(self):
        self.add_valid_requirement()
        self.write(
            "requirements/0001-second-contract/requirements.md",
            VALID_REQUIREMENTS,
        )
        self.track("requirements/0001-second-contract/requirements.md")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any(
                "duplicate requirements feature ID 001" in error
                for error in errors
            )
        )

    def test_malformed_tracked_requirement_document_fails(self):
        self.write(
            "requirements/001-console-status/requirements.md",
            "# Feature Specification: [FEATURE NAME]\n",
        )
        self.track("requirements/001-console-status/requirements.md")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any("missing required heading" in error for error in errors)
        )
        self.assertTrue(
            any("measurable success criterion" in error for error in errors)
        )

    def test_malformed_story_heading_fails_alongside_a_valid_story(self):
        invalid = VALID_REQUIREMENTS.replace(
            "\n## Functional Requirements",
            "\n### US-02: Disconnect console\n\n## Functional Requirements",
        )
        self.write("requirements/001-console-status/requirements.md", invalid)
        self.track("requirements")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any("malformed user story heading" in error for error in errors)
        )

    def test_non_ears_functional_requirement_fails(self):
        invalid = VALID_REQUIREMENTS.replace(
            "When the console is connected, the system MUST report its state.",
            "The system should report its state.",
        )
        self.write("requirements/001-console-status/requirements.md", invalid)
        self.track("requirements/001-console-status/requirements.md")

        errors = checker.check_repository(self.repo)

        self.assertTrue(any("numbered EARS form" in error for error in errors))

    def test_malformed_fr_and_sc_entries_fail_alongside_valid_entries(self):
        invalid = VALID_REQUIREMENTS.replace(
            "\n## Success Criteria",
            "\n- FR-002: The system should disconnect eventually.\n\n## Success Criteria",
        ).replace(
            "- **SC-002**: At least 90% of status requests return the current console state.",
            "- **SC-002**: At least 90% of status requests return the current console state.\n"
            "- SC-003: Status should appear quickly.",
        )
        self.write("requirements/001-console-status/requirements.md", invalid)
        self.track("requirements")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any("functional requirement must use" in error for error in errors)
        )
        self.assertTrue(
            any("success criterion must use" in error for error in errors)
        )

    def test_success_criteria_accept_hardware_and_count_units(self):
        self.add_valid_requirement()
        measurements = (
            "500 mV",
            "45 °C",
            "10 frames",
            "1 retry",
            "2-second",
            "-20 °C",
        )

        for measurement in measurements:
            with self.subTest(measurement=measurement):
                document = VALID_REQUIREMENTS.replace(
                    "within 2 seconds", f"within {measurement}"
                )
                self.write(
                    "requirements/001-console-status/requirements.md", document
                )
                self.track("requirements/001-console-status/requirements.md")

                self.assertEqual([], checker.check_repository(self.repo))

    def test_success_criteria_do_not_treat_identifiers_as_measurements(self):
        invalid = VALID_REQUIREMENTS.replace(
            "At least 90% of status requests return the current console state.",
            "All requirements including FR-001 are met.",
        )
        self.write("requirements/001-console-status/requirements.md", invalid)
        self.track("requirements")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any("SC-002 needs a concrete numeric" in error for error in errors)
        )

    def test_soft_wrapped_requirements_entries_pass(self):
        self.add_valid_requirement()
        wrapped = (
            VALID_REQUIREMENTS.replace(
                "As an operator, I want to view the console state, so that I can diagnose the connection.",
                "As an operator, I want to view the console\n  state, so that I can diagnose the connection.",
            )
            .replace(
                "- **Given** the console is connected, **When** I request its status, **Then** its state is shown.",
                "- **Given** the console is connected, **When** I request its status,\n  **Then** its state is shown.",
            )
            .replace(
                "When the console is connected, the system MUST report its state.",
                "When the console is connected,\n  the system MUST report its state.",
            )
            .replace(
                "An operator can view console status within 2 seconds.",
                "An operator can view console status within\n  2 seconds.",
            )
        )
        self.write("requirements/001-console-status/requirements.md", wrapped)
        self.track("requirements")

        self.assertEqual([], checker.check_repository(self.repo))

    def test_markdown_links_are_not_placeholder_markers(self):
        self.add_valid_requirement()
        linked = VALID_REQUIREMENTS.replace(
            "Operators need to see the state of the console connection.",
            "Operators read the [Address guide](https://example.invalid/address).",
        ).replace(
            "An operator can view console status within 2 seconds.",
            "The [status page](https://example.invalid/status) loads within 2 seconds.",
        )
        self.write("requirements/001-console-status/requirements.md", linked)
        self.track("requirements")

        self.assertEqual([], checker.check_repository(self.repo))

    def test_unresolved_placeholder_marker_fails(self):
        self.add_valid_requirement()
        invalid = VALID_REQUIREMENTS.replace(
            "Operators need to see the state of the console connection.",
            "[ADD a user need]",
        )
        self.write("requirements/001-console-status/requirements.md", invalid)
        self.track("requirements")

        errors = checker.check_repository(self.repo)

        self.assertTrue(
            any(
                "unresolved clarification markers" in error for error in errors
            )
        )

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        output, error = io.StringIO(), io.StringIO()
        with (
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(error),
        ):
            result = checker.main(["--repo", str(self.repo), *argv])
        return result, output.getvalue(), error.getvalue()

    def test_cli_reports_a_compliant_tree(self):
        self.add_valid_requirement()

        result, output, _ = self.run_main()

        self.assertEqual(0, result)
        self.assertIn(
            "1 tracked feature contract(s) follow requirements/AGENTS.md",
            output,
        )

    def test_cli_reports_each_problem(self):
        self.add_valid_requirement()
        self.write("specs/999-old-feature/spec.md", "generated spec")
        self.track("specs")

        result, _, error = self.run_main()

        self.assertEqual(1, result)
        self.assertIn(
            "requirements/ must follow requirements/AGENTS.md:", error
        )
        self.assertIn(
            "  tracked generated Spec Kit file is forbidden: specs/999-old-feature/spec.md",
            error,
        )

    def test_cli_refuses_a_directory_below_the_repository_root(self):
        self.add_valid_requirement()

        result = checker.main(["--repo", str(self.repo / "requirements")])

        self.assertEqual(2, result)

    def test_cli_reports_a_git_failure(self):
        def refuse(command, **kwargs):
            raise subprocess.CalledProcessError(
                128,
                command,
                stderr=b"fatal: detected dubious ownership in repository\n",
            )

        with mock.patch.object(checker.subprocess, "run", refuse):
            result, _, error = self.run_main()

        self.assertEqual(2, result)
        self.assertIn("dubious ownership", error)


if __name__ == "__main__":
    unittest.main()
