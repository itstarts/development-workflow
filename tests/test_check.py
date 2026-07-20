import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "check.py"


class CheckCliTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SOURCE.is_file(), "check.py is the missing target interface")

    def fixture(self, root, stages):
        (root / "scripts").mkdir(parents=True)
        shutil.copy2(SOURCE, root / "scripts" / "check.py")
        validator = root / "scripts" / "validate_repo.py"
        validator.write_text("import sys\nraise SystemExit(0)\n", encoding="utf-8")
        (root / "evaluations").mkdir()
        registry = {
            "schema_version": 1,
            "skills": {
                name: {
                    "evaluation_mode": "managed",
                    "evidence_profile": "creation-plus-current-red",
                    "stage": stage,
                }
                for name, stage in stages.items()
            },
        }
        (root / "evaluations" / "registry.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        smoke_test = (
            "import unittest\n\n"
            "class SmokeTest(unittest.TestCase):\n"
            "    def test_smoke(self):\n"
            "        pass\n"
        )
        (root / "tests").mkdir()
        (root / "tests" / "test_smoke.py").write_text(
            smoke_test, encoding="utf-8"
        )
        for name in stages:
            skill_tests = root / "skills" / name / "tests"
            skill_tests.mkdir(parents=True)
            (skill_tests / "test_smoke.py").write_text(
                smoke_test, encoding="utf-8"
            )
        quick = root / "quick_validate.py"
        quick.write_text("import sys\nraise SystemExit(0)\n", encoding="utf-8")
        plugin = root / "validate_plugin.py"
        plugin.write_text("import sys\nraise SystemExit(0)\n", encoding="utf-8")
        return quick, plugin

    def run_check(self, root, *args, env=None):
        return subprocess.run(
            [sys.executable, str(root / "scripts" / "check.py"), *args],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_requires_exactly_one_mode_and_rejects_unknown_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, _ = self.fixture(root, {"alpha": "implemented"})
            no_mode = self.run_check(root)
            both = self.run_check(root, "--full", "--skill", "alpha")
            unknown = self.run_check(
                root, "--skill", "missing", "--skill-validator", str(quick)
            )

        for result in (no_mode, both, unknown):
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)

    def test_targeted_mode_deduplicates_targets_and_reports_fixed_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, _ = self.fixture(
                root, {"beta": "implemented", "alpha": "review-approved"}
            )
            result = self.run_check(
                root,
                "--skill",
                "beta",
                "--skill",
                "alpha",
                "--skill",
                "beta",
                "--skill-validator",
                str(quick),
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        labels = [
            "skill-tests:alpha",
            "skill-tests:beta",
            "repository-validator:alpha",
            "repository-validator:beta",
            "skill-validator:alpha",
            "skill-validator:beta",
        ]
        positions = [result.stdout.index(label) for label in labels]
        self.assertEqual(sorted(positions), positions)
        self.assertNotIn("repo-tests", result.stdout)
        self.assertIn("--reviewed-skill alpha --require-freshness", result.stdout)
        self.assertIn("--evidence-only beta --require-freshness", result.stdout)

    def test_targeted_mode_does_not_run_unrelated_root_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, _ = self.fixture(root, {"alpha": "implemented"})
            (root / "tests" / "test_unrelated.py").write_text(
                "raise RuntimeError('targeted mode ran unrelated root tests')\n",
                encoding="utf-8",
            )
            result = self.run_check(
                root,
                "--skill",
                "alpha",
                "--skill-validator",
                str(quick),
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("repo-tests", result.stdout)

    def test_full_mode_requires_every_skill_review_approved_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, plugin = self.fixture(
                root, {"alpha": "review-approved", "beta": "implemented"}
            )
            result = self.run_check(
                root,
                "--full",
                "--skill-validator",
                str(quick),
                "--plugin-validator",
                str(plugin),
            )

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("review-approved", result.stderr)

    def test_full_mode_runs_complete_matrix_once_all_skills_are_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, plugin = self.fixture(
                root, {"beta": "review-approved", "alpha": "review-approved"}
            )
            result = self.run_check(
                root,
                "--full",
                "--skill-validator",
                str(quick),
                "--plugin-validator",
                str(plugin),
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(1, result.stdout.count("repo-tests"))
        self.assertEqual(1, result.stdout.count("repository-validator:full"))
        self.assertEqual(1, result.stdout.count("plugin-validator"))
        self.assertIn("scripts/validate_repo.py --require-freshness", result.stdout)

    def test_validator_resolution_prefers_explicit_then_codex_home_then_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            explicit, _ = self.fixture(root, {"alpha": "implemented"})
            codex_home = Path(directory) / "codex-home"
            fallback_home = Path(directory) / "home"
            relative = Path(
                "skills/.system/skill-creator/scripts/quick_validate.py"
            )
            codex_validator = codex_home / relative
            home_validator = fallback_home / ".codex" / relative
            for path, code in ((codex_validator, 0), (home_validator, 9)):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    f"import sys\nraise SystemExit({code})\n", encoding="utf-8"
                )
            explicit_result = self.run_check(
                root,
                "--skill",
                "alpha",
                "--skill-validator",
                str(explicit),
                env={**os.environ, "CODEX_HOME": str(codex_home), "HOME": str(fallback_home)},
            )
            codex_result = self.run_check(
                root,
                "--skill",
                "alpha",
                env={**os.environ, "CODEX_HOME": str(codex_home), "HOME": str(fallback_home)},
            )
            codex_validator.unlink()
            home_validator.write_text(
                "import sys\nraise SystemExit(0)\n", encoding="utf-8"
            )
            fallback_result = self.run_check(
                root,
                "--skill",
                "alpha",
                env={**os.environ, "CODEX_HOME": str(codex_home), "HOME": str(fallback_home)},
            )

        for result in (explicit_result, codex_result, fallback_result):
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_malformed_registry_fails_before_any_subprocess_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, _ = self.fixture(root, {"alpha": "implemented"})
            (root / "evaluations" / "registry.json").write_text(
                "[]\n", encoding="utf-8"
            )
            result = self.run_check(
                root, "--skill", "alpha", "--skill-validator", str(quick)
            )

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("input_error", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_symlink_validator_as_capability_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, _ = self.fixture(root, {"alpha": "implemented"})
            alias = root / "quick-link.py"
            alias.symlink_to(quick)
            result = self.run_check(
                root, "--skill", "alpha", "--skill-validator", str(alias)
            )

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("capability_error", result.stderr)

    def test_timeout_is_reported_without_retrying_or_hiding_other_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, _ = self.fixture(root, {"alpha": "implemented"})
            quick.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
            result = self.run_check(
                root,
                "--skill",
                "alpha",
                "--skill-validator",
                str(quick),
                "--timeout-seconds",
                "1",
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("[TIMEOUT] skill-validator:alpha", result.stdout)
        self.assertIn("[PASS] skill-tests:alpha", result.stdout)
        self.assertEqual(1, result.stdout.count("skill-validator:alpha"))

    def test_nonzero_check_is_reported_and_propagated_after_other_results_finish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            quick, _ = self.fixture(root, {"alpha": "implemented"})
            quick.write_text("import sys\nraise SystemExit(7)\n", encoding="utf-8")
            result = self.run_check(
                root, "--skill", "alpha", "--skill-validator", str(quick)
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("[PASS] skill-tests:alpha", result.stdout)
        self.assertIn("[FAIL] skill-validator:alpha", result.stdout)
        self.assertIn("exit=7", result.stdout)


if __name__ == "__main__":
    unittest.main()
