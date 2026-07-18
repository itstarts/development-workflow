import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_install.py"
IGNORED_DIRS = {"__pycache__"}
IGNORED_FILES = {".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".pyd"}


def publishable_files(skill_root):
    result = [skill_root / "SKILL.md"]
    for name in ("agents", "assets", "references", "scripts"):
        directory = skill_root / name
        if not directory.is_dir():
            continue
        result.extend(
            path
            for path in directory.rglob("*")
            if path.is_file()
            and not IGNORED_DIRS.intersection(path.relative_to(directory).parts[:-1])
            and path.name not in IGNORED_FILES
            and path.suffix.lower() not in IGNORED_SUFFIXES
        )
    return sorted(result)


class VerifyInstallTests(unittest.TestCase):
    skill_name = "creating-product-requirements"

    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "verify_install.py is the missing target interface")

    def run_verify(self, home, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--codex-home", str(home), *extra],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_fixture_verify(self, root, home, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "verify_install.py"),
                "--codex-home",
                str(home),
                *extra,
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    def stage(self, home):
        source = ROOT / "skills" / self.skill_name
        target = home / "skills" / self.skill_name
        for path in publishable_files(source):
            destination = target / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        return target

    def test_identical_payload_passes_without_modifying_target(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            target = self.stage(home)
            before = {
                path.relative_to(target): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in target.rglob("*")
                if path.is_file()
            }

            result = self.run_verify(home, "--skill", self.skill_name)

            after = {
                path.relative_to(target): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in target.rglob("*")
                if path.is_file()
            }
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(before, after)
        self.assertIn(f"{self.skill_name}: identical", result.stdout)

    def test_reports_missing_extra_and_different_without_file_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            target = self.stage(home)
            (target / "agents" / "openai.yaml").unlink()
            (target / "SKILL.md").write_text("installed differs\n", encoding="utf-8")
            extra = target / "references" / "extra.md"
            extra.write_text("SECRET-CONTENT-MUST-NOT-PRINT\n", encoding="utf-8")

            result = self.run_verify(home, "--skill", self.skill_name)

        self.assertEqual(1, result.returncode)
        combined = result.stdout + result.stderr
        self.assertIn("missing: agents/openai.yaml", combined)
        self.assertIn("different: SKILL.md", combined)
        self.assertIn("extra: references/extra.md", combined)
        self.assertNotIn("SECRET-CONTENT", combined)

    def test_ignores_cache_artifacts_but_rejects_publishable_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            target = self.stage(home)
            cache = target / "scripts" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "ignored.pyc").write_bytes(b"cache")
            (target / "scripts" / ".DS_Store").write_bytes(b"cache")
            clean = self.run_verify(home, "--skill", self.skill_name)
            self.assertEqual(0, clean.returncode, clean.stdout + clean.stderr)

            link = target / "references" / "linked.md"
            link.symlink_to(target / "SKILL.md")
            linked = self.run_verify(home, "--skill", self.skill_name)

        self.assertEqual(2, linked.returncode)
        self.assertEqual("", linked.stdout)
        self.assertIn("INPUT_ERROR", linked.stderr)
        self.assertIn("non-regular: references/linked.md", linked.stderr)

    def test_path_read_and_file_type_errors_are_exit_two(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            missing = self.run_verify(home, "--skill", self.skill_name)

            target = self.stage(home)
            os.mkfifo(target / "references" / "unexpected-pipe")
            wrong_type = self.run_verify(home, "--skill", self.skill_name)

        for result in (missing, wrong_type):
            with self.subTest(stderr=result.stderr):
                self.assertEqual(2, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertIn("INPUT_ERROR", result.stderr)

    def test_malformed_registry_and_unknown_stage_fail_without_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            (root / "scripts").mkdir(parents=True)
            shutil.copy2(SCRIPT, root / "scripts" / "verify_install.py")
            (root / "evaluations").mkdir()
            registry = root / "evaluations" / "registry.json"
            registry.write_text("[]\n", encoding="utf-8")
            malformed = self.run_fixture_verify(root, root / "missing-home")

            registry.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "skills": {
                            self.skill_name: {
                                "evaluation_mode": "managed",
                                "evidence_profile": "creation-only",
                                "stage": "future-stage",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            unknown_stage = self.run_fixture_verify(
                root,
                root / "missing-home",
                "--skill",
                self.skill_name,
            )

        for result in (malformed, unknown_stage):
            with self.subTest(stderr=result.stderr):
                self.assertEqual(2, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertIn("INPUT_ERROR", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_requires_explicit_home_and_rejects_unknown_or_baseline_skill(self):
        missing_home = subprocess.run(
            [sys.executable, str(SCRIPT), "--skill", self.skill_name],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, missing_home.returncode)

        with tempfile.TemporaryDirectory() as directory:
            unknown = self.run_verify(Path(directory), "--skill", "unknown-skill")
        self.assertEqual(2, unknown.returncode)
        self.assertIn("unknown skill", unknown.stderr)


if __name__ == "__main__":
    unittest.main()
