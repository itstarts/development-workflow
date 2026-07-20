import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILL = "creating-product-requirements"
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_repo_under_test", ROOT / "scripts" / "validate_repo.py"
)
assert VALIDATOR_SPEC is not None and VALIDATOR_SPEC.loader is not None
VALIDATE_REPO = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATE_REPO)


def copy_repository(destination):
    target = destination / "repository"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", "work", ".DS_Store", "*.pyc", "*.pyo"
        ),
    )
    return target


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(root, *args):
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME="Workflow Tests",
        GIT_AUTHOR_EMAIL="workflow-tests@example.invalid",
        GIT_COMMITTER_NAME="Workflow Tests",
        GIT_COMMITTER_EMAIL="workflow-tests@example.invalid",
    )
    return subprocess.run(
        ["git", *args], cwd=root, env=env, text=True, capture_output=True, check=True
    )


def normalize_target_evidence(root):
    registry_path = root / "evaluations" / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["skills"][SKILL]["stage"] = "review-approved"
    write_json(registry_path, registry)

    evaluation = root / "evaluations" / SKILL
    red_path = evaluation / "migration-red" / "result.json"
    red = json.loads(red_path.read_text(encoding="utf-8"))
    selected = red["selected_case"]

    rubric = json.loads((evaluation / "rubric.json").read_text(encoding="utf-8"))
    expected = {}
    for criterion in rubric["criteria"]:
        for case_id in criterion["applies_to"]:
            expected.setdefault(case_id, []).append(criterion["id"])

    green_path = evaluation / "green" / "result.json"
    green = json.loads(green_path.read_text(encoding="utf-8"))
    green.update(
        evidence_role="green",
        target_skill_loaded=True,
        all_runs_valid=True,
        all_required_passed=True,
        review_status="approved",
        reviewer="independent-skill-reviewer",
        reviewed_at="2026-07-18",
        fresh_cases=[selected],
    )
    green["cases"] = [
        {"id": case_id, "valid": True, "passed_criteria": criteria}
        for case_id, criteria in sorted(expected.items())
    ]
    write_json(green_path, green)
    for case_id in expected:
        output = evaluation / "green" / f"{case_id}-output.md"
        if not output.exists():
            output.write_text(f"Synthetic fixture output for case {case_id}.\n", encoding="utf-8")
    return selected


def refresh_dirty_bundle(root, selected, marker):
    evaluation = root / "evaluations" / SKILL
    red_result_path = evaluation / "migration-red" / "result.json"
    red = json.loads(red_result_path.read_text(encoding="utf-8"))
    red["warnings"] = [marker]
    write_json(red_result_path, red)
    red_output = evaluation / "migration-red" / f"{selected}-output.md"
    red_output.write_text(
        red_output.read_text(encoding="utf-8") + f"\n{marker}\n", encoding="utf-8"
    )
    green_path = evaluation / "green" / "result.json"
    green = json.loads(green_path.read_text(encoding="utf-8"))
    green["reviewed_at"] = "2026-07-19"
    write_json(green_path, green)
    green_output = evaluation / "green" / f"{selected}-output.md"
    green_output.write_text(
        green_output.read_text(encoding="utf-8") + f"\n{marker}\n",
        encoding="utf-8",
    )


def run_validator(root, *args):
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "validate_repo.py"), *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


class EvidenceFreshnessTests(unittest.TestCase):
    def test_new_uncommitted_creation_only_bundle_is_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = (
                "skills/new-router/SKILL.md",
                "skills/new-router/references/policy.md",
                "evaluations/new-router/rubric.json",
                "evaluations/new-router/cases/01.md",
                "evaluations/new-router/baseline/pre-creation-audit.json",
                "evaluations/new-router/baseline/result.json",
                "evaluations/new-router/baseline/01-output.md",
                "evaluations/new-router/green/result.json",
                "evaluations/new-router/green/01-output.md",
                "evaluations/registry.json",
            )
            for relative in files:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture\n", encoding="utf-8")
            errors = []
            messages = []
            with mock.patch.object(VALIDATE_REPO, "ROOT", root), mock.patch.object(
                VALIDATE_REPO, "last_production_commit", return_value=None
            ):
                VALIDATE_REPO.validate_creation_only_freshness(
                    "new-router", set(files), errors, messages
                )

        self.assertEqual([], errors)
        self.assertEqual(["new-router: freshness worktree-creation-current"], messages)

    def test_new_uncommitted_creation_only_bundle_rejects_missing_green_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "skills/new-router/SKILL.md",
                "evaluations/new-router/rubric.json",
                "evaluations/new-router/cases/01.md",
                "evaluations/new-router/baseline/pre-creation-audit.json",
                "evaluations/new-router/baseline/result.json",
                "evaluations/new-router/baseline/01-output.md",
                "evaluations/new-router/green/result.json",
                "evaluations/registry.json",
            }
            for relative in files:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture\n", encoding="utf-8")
            missing = root / "evaluations/new-router/green/01-output.md"
            missing.parent.mkdir(parents=True, exist_ok=True)
            missing.write_text("fixture\n", encoding="utf-8")
            errors = []
            messages = []
            with mock.patch.object(VALIDATE_REPO, "ROOT", root), mock.patch.object(
                VALIDATE_REPO, "last_production_commit", return_value=None
            ):
                VALIDATE_REPO.validate_creation_only_freshness(
                    "new-router", files, errors, messages
                )

        self.assertEqual([], messages)
        self.assertTrue(any("green/01-output.md" in error for error in errors), errors)

    def test_non_git_copy_is_structurally_checkable_but_strict_freshness_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            normalize_target_evidence(root)

            structural = run_validator(root, "--reviewed-skill", SKILL)
            strict = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(0, structural.returncode, structural.stdout + structural.stderr)
        self.assertEqual(1, strict.returncode)
        self.assertIn("unverified-non-git", strict.stderr)

    def test_clean_single_commit_evidence_chain_is_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"{SKILL}: freshness clean-current", result.stdout)

    def test_dirty_production_without_complete_evidence_bundle_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")
            skill = root / "skills" / SKILL / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\n", encoding="utf-8")

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("worktree evidence bundle", result.stderr)
        self.assertIn("green-result-review", result.stderr)

    def test_clean_prefix_with_dirty_production_green_and_result_is_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            production = root / "skills" / SKILL / "SKILL.md"
            production.write_text(
                production.read_text(encoding="utf-8") + "\nproduction refresh\n",
                encoding="utf-8",
            )
            evaluation = root / "evaluations" / SKILL
            green_output = evaluation / "green" / f"{selected}-output.md"
            green_output.write_text(
                green_output.read_text(encoding="utf-8") + "\ngreen refresh\n",
                encoding="utf-8",
            )
            green_result = evaluation / "green" / "result.json"
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["reviewed_at"] = "2026-07-19"
            write_json(green_result, green)

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"{SKILL}: freshness worktree-current", result.stdout)

    def test_implemented_skill_accepts_clean_prefix_with_dirty_green_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            registry_path = root / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"][SKILL]["stage"] = "implemented"
            write_json(registry_path, registry)
            evaluation = root / "evaluations" / SKILL
            green_output = evaluation / "green" / f"{selected}-output.md"
            green_output.write_text(
                green_output.read_text(encoding="utf-8") + "\ngreen refresh\n",
                encoding="utf-8",
            )
            green_result = evaluation / "green" / "result.json"
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["review_status"] = "pending"
            green.pop("reviewer")
            green.pop("reviewed_at")
            write_json(green_result, green)

            result = run_validator(
                root, "--evidence-only", SKILL, "--require-freshness"
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"{SKILL}: freshness worktree-current", result.stdout)

    def test_dirty_review_result_after_committed_green_is_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            green_result = (
                root / "evaluations" / SKILL / "green" / "result.json"
            )
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["reviewed_at"] = "2026-07-19"
            write_json(green_result, green)

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"{SKILL}: freshness worktree-current", result.stdout)

    def test_partial_dirty_red_pair_reports_the_missing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            evaluation = root / "evaluations" / SKILL
            red_result = evaluation / "migration-red" / "result.json"
            red = json.loads(red_result.read_text(encoding="utf-8"))
            red["warnings"] = ["partial red refresh"]
            write_json(red_result, red)
            production = root / "skills" / SKILL / "SKILL.md"
            production.write_text(
                production.read_text(encoding="utf-8") + "\nproduction refresh\n",
                encoding="utf-8",
            )
            green_output = evaluation / "green" / f"{selected}-output.md"
            green_output.write_text(
                green_output.read_text(encoding="utf-8") + "\ngreen refresh\n",
                encoding="utf-8",
            )
            green_result = evaluation / "green" / "result.json"
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["reviewed_at"] = "2026-07-19"
            write_json(green_result, green)

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("current-red-output", result.stderr)
        self.assertNotIn("current-red-result", result.stderr)

    def test_partial_dirty_green_group_reports_each_missing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            evaluation = root / "evaluations" / SKILL
            green_result = evaluation / "green" / "result.json"
            green = json.loads(green_result.read_text(encoding="utf-8"))
            second = next(
                case["id"] for case in green["cases"] if case["id"] != selected
            )
            green["fresh_cases"] = [selected, second]
            write_json(green_result, green)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            green_output = evaluation / "green" / f"{selected}-output.md"
            green_output.write_text(
                green_output.read_text(encoding="utf-8") + "\ngreen refresh\n",
                encoding="utf-8",
            )
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["reviewed_at"] = "2026-07-19"
            write_json(green_result, green)

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(1, result.returncode)
        self.assertIn(f"green-output:{second}-output.md", result.stderr)
        self.assertNotIn(f"green-output:{selected}-output.md", result.stderr)

    def test_dirty_green_without_dirty_result_is_not_a_contiguous_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            green_output = (
                root
                / "evaluations"
                / SKILL
                / "green"
                / f"{selected}-output.md"
            )
            green_output.write_text(
                green_output.read_text(encoding="utf-8") + "\ngreen refresh\n",
                encoding="utf-8",
            )

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("green-result-review", result.stderr)

    def test_dirty_result_does_not_hide_a_stale_clean_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            production = root / "skills" / SKILL / "SKILL.md"
            production.write_text(
                production.read_text(encoding="utf-8") + "\nstale production\n",
                encoding="utf-8",
            )
            git(root, "add", str(production.relative_to(root)))
            git(root, "commit", "-qm", "production after green")

            green_result = (
                root / "evaluations" / SKILL / "green" / "result.json"
            )
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["reviewed_at"] = "2026-07-19"
            write_json(green_result, green)

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("production<=green-output", result.stderr)

    def test_complete_dirty_bundle_is_current_for_reviewed_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            evaluation = root / "evaluations" / SKILL
            skill_path = root / "skills" / SKILL / "SKILL.md"
            skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            red_result_path = evaluation / "migration-red" / "result.json"
            red = json.loads(red_result_path.read_text(encoding="utf-8"))
            red["warnings"] = ["fixture refresh"]
            write_json(red_result_path, red)
            red_output = evaluation / "migration-red" / f"{selected}-output.md"
            red_output.write_text(red_output.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            green_path = evaluation / "green" / "result.json"
            green = json.loads(green_path.read_text(encoding="utf-8"))
            green["reviewed_at"] = "2026-07-19"
            write_json(green_path, green)
            green_output = evaluation / "green" / f"{selected}-output.md"
            green_output.write_text(green_output.read_text(encoding="utf-8") + "\n", encoding="utf-8")

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"{SKILL}: freshness worktree-current", result.stdout)

    def test_dirty_delete_rename_and_untracked_production_use_the_same_bundle(self):
        for mutation in ("delete", "rename", "untracked"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = copy_repository(Path(directory))
                selected = normalize_target_evidence(root)
                git(root, "init", "-q")
                git(root, "add", ".")
                git(root, "commit", "-qm", "fixture baseline")

                reference = root / "skills" / SKILL / "references" / "review-and-handoff.md"
                if mutation == "delete":
                    reference.unlink()
                elif mutation == "rename":
                    reference.rename(reference.with_name("renamed-review-and-handoff.md"))
                else:
                    (reference.parent / "new-contract.md").write_text(
                        "new publishable contract\n", encoding="utf-8"
                    )
                refresh_dirty_bundle(root, selected, f"fixture-{mutation}")

                result = run_validator(
                    root, "--reviewed-skill", SKILL, "--require-freshness"
                )

                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertIn(f"{SKILL}: freshness worktree-current", result.stdout)

    def test_clean_multi_commit_ancestry_chain_is_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            evaluation = root / "evaluations" / SKILL
            rubric = evaluation / "rubric.json"
            case = next((evaluation / "cases").glob(f"{selected}-*.md"))
            rubric.write_text(rubric.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            case.write_text(case.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            git(root, "add", str(rubric.relative_to(root)), str(case.relative_to(root)))
            git(root, "commit", "-qm", "criterion")

            red_result = evaluation / "migration-red" / "result.json"
            red = json.loads(red_result.read_text(encoding="utf-8"))
            red["warnings"] = ["multi-commit-red"]
            write_json(red_result, red)
            red_output = evaluation / "migration-red" / f"{selected}-output.md"
            red_output.write_text(
                red_output.read_text(encoding="utf-8") + "\nred\n", encoding="utf-8"
            )
            git(root, "add", str(red_result.relative_to(root)), str(red_output.relative_to(root)))
            git(root, "commit", "-qm", "current red")

            production = root / "skills" / SKILL / "SKILL.md"
            production.write_text(
                production.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )
            git(root, "add", str(production.relative_to(root)))
            git(root, "commit", "-qm", "production")

            green_output = evaluation / "green" / f"{selected}-output.md"
            green_output.write_text(
                green_output.read_text(encoding="utf-8") + "\ngreen\n", encoding="utf-8"
            )
            git(root, "add", str(green_output.relative_to(root)))
            git(root, "commit", "-qm", "green output")

            green_result = evaluation / "green" / "result.json"
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["reviewed_at"] = "2026-07-19"
            write_json(green_result, green)
            git(root, "add", str(green_result.relative_to(root)))
            git(root, "commit", "-qm", "review result")

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"{SKILL}: freshness clean-current", result.stdout)

    def test_merge_sibling_red_and_production_commits_are_incomparable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")

            evaluation = root / "evaluations" / SKILL
            rubric = evaluation / "rubric.json"
            rubric.write_text(rubric.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            git(root, "add", str(rubric.relative_to(root)))
            git(root, "commit", "-qm", "criterion")
            git(root, "branch", "red-branch")
            git(root, "checkout", "-q", "-b", "production-branch")

            production = root / "skills" / SKILL / "SKILL.md"
            production.write_text(
                production.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )
            git(root, "add", str(production.relative_to(root)))
            git(root, "commit", "-qm", "production sibling")

            git(root, "checkout", "-q", "red-branch")
            red_result = evaluation / "migration-red" / "result.json"
            red = json.loads(red_result.read_text(encoding="utf-8"))
            red["warnings"] = ["sibling-red"]
            write_json(red_result, red)
            red_output = evaluation / "migration-red" / f"{selected}-output.md"
            red_output.write_text(
                red_output.read_text(encoding="utf-8") + "\nred\n", encoding="utf-8"
            )
            git(root, "add", str(red_result.relative_to(root)), str(red_output.relative_to(root)))
            git(root, "commit", "-qm", "red sibling")

            git(root, "checkout", "-q", "production-branch")
            git(root, "merge", "--no-ff", "-qm", "merge siblings", "red-branch")
            green_output = evaluation / "green" / f"{selected}-output.md"
            green_output.write_text(
                green_output.read_text(encoding="utf-8") + "\ngreen\n", encoding="utf-8"
            )
            git(root, "add", str(green_output.relative_to(root)))
            git(root, "commit", "-qm", "green output")
            green_result = evaluation / "green" / "result.json"
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["reviewed_at"] = "2026-07-19"
            write_json(green_result, green)
            git(root, "add", str(green_result.relative_to(root)))
            git(root, "commit", "-qm", "review result")

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("current-red<=production", result.stderr)

    def test_merge_preserves_topic_review_commit_when_result_matches_first_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            selected = normalize_target_evidence(root)
            approved_result = (
                root
                / "evaluations"
                / SKILL
                / "green"
                / "result.json"
            ).read_text(encoding="utf-8")
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")
            base_branch = git(root, "branch", "--show-current").stdout.strip()
            git(root, "checkout", "-q", "-b", "topic")

            evaluation = root / "evaluations" / SKILL
            green_output = evaluation / "green" / f"{selected}-output.md"
            green_output.write_text(
                green_output.read_text(encoding="utf-8") + "\ngreen refresh\n",
                encoding="utf-8",
            )
            green_result = evaluation / "green" / "result.json"
            green = json.loads(green_result.read_text(encoding="utf-8"))
            green["review_status"] = "pending"
            green.pop("reviewer")
            green.pop("reviewed_at")
            write_json(green_result, green)
            git(root, "add", str(green_output.relative_to(root)), str(green_result.relative_to(root)))
            git(root, "commit", "-qm", "green refresh")

            green_result.write_text(approved_result, encoding="utf-8")
            git(root, "add", str(green_result.relative_to(root)))
            git(root, "commit", "-qm", "review approval")
            git(root, "checkout", "-q", base_branch)
            git(root, "merge", "--no-ff", "-qm", "merge topic", "topic")

            result = run_validator(
                root, "--reviewed-skill", SKILL, "--require-freshness"
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"{SKILL}: freshness clean-current", result.stdout)

    def test_creation_only_profile_requires_upgrade_after_production_change(self):
        target = "routing-development-workflows"
        with tempfile.TemporaryDirectory() as directory:
            root = copy_repository(Path(directory))
            git(root, "init", "-q")
            git(root, "add", ".")
            git(root, "commit", "-qm", "fixture baseline")
            production = root / "skills" / target / "SKILL.md"
            production.write_text(
                production.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )

            result = run_validator(
                root, "--reviewed-skill", target, "--require-freshness"
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("upgrade to a current-red profile", result.stderr)

    def test_stage_target_flags_are_mutually_exclusive(self):
        result = run_validator(
            ROOT,
            "--evidence-only",
            SKILL,
            "--reviewed-skill",
            SKILL,
            "--require-freshness",
        )
        self.assertEqual(2, result.returncode)


if __name__ == "__main__":
    unittest.main()
