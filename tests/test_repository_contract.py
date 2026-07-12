import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_required_repository_surfaces_exist(self):
        required = [
            ROOT / "AGENTS.md",
            ROOT / "skills" / "AGENTS.md",
            ROOT / "tests" / "AGENTS.md",
            ROOT / "evaluations" / "AGENTS.md",
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / ".codex" / "agents" / "skill-reviewer.toml",
            ROOT / ".codex" / "agents" / "final-reviewer.toml",
            ROOT / ".codex" / "agents" / "workflow-final-reviewer.toml",
            ROOT / "scripts" / "validate_repo.py",
            ROOT / "README.md",
            ROOT / "CHANGELOG.md",
            ROOT / "requirements-dev.txt",
        ]
        self.assertEqual([], [str(path.relative_to(ROOT)) for path in required if not path.is_file()])

    def test_plugin_manifest_owns_the_skills_directory(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual("development-workflow", manifest["name"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertEqual("0.1.0", manifest["version"])
        self.assertIn("existing specifications and plans", manifest["description"])
        self.assertIn(
            "companion authoring skill is planned",
            manifest["interface"]["longDescription"],
        )

    def test_existing_skill_is_complete_and_planned_skill_is_not_exposed(self):
        existing = ROOT / "skills" / "generating-development-prompts"
        planned = ROOT / "skills" / "creating-development-specs-and-plans"
        self.assertTrue((existing / "SKILL.md").is_file())
        self.assertTrue((existing / "agents" / "openai.yaml").is_file())
        self.assertFalse(planned.exists())

    def test_skill_final_reviewer_contract_and_workflow_role_do_not_conflict(self):
        skill_asset = (
            ROOT
            / "skills"
            / "generating-development-prompts"
            / "assets"
            / "final-reviewer.toml"
        )
        project_role = ROOT / ".codex" / "agents" / "final-reviewer.toml"
        workflow_role = ROOT / ".codex" / "agents" / "workflow-final-reviewer.toml"
        self.assertEqual(skill_asset.read_bytes(), project_role.read_bytes())
        self.assertTrue(workflow_role.is_file())

    def test_agent_rules_record_tdd_and_self_containment_gates(self):
        root_rules = (ROOT / "AGENTS.md").read_text()
        skill_rules = (ROOT / "skills" / "AGENTS.md").read_text()
        for phrase in [
            "RED→GREEN→REFACTOR",
            "不得在 `skills/` 下创建其目录或 `SKILL.md`",
            "不得依赖 `~/.codex/plugins/cache/`",
            "不得创建或操作用户可见 Codex task/thread",
        ]:
            self.assertIn(phrase, root_rules)
        for phrase in [
            "无目标 skill 代理的本地原始输出",
            "能够通过 GitHub 多路径安装方式单独安装",
            "官方 `quick_validate.py`",
        ]:
            self.assertIn(phrase, skill_rules)
        evidence_rules_path = ROOT / "evaluations" / "AGENTS.md"
        self.assertTrue(evidence_rules_path.is_file())
        evidence_rules = evidence_rules_path.read_text()
        self.assertIn("脱敏后的固定场景、判据和选中证据必须版本化", evidence_rules)
        self.assertIn("真实 task/thread 标识符", evidence_rules)

    def test_repository_validator_passes_current_tree(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_repo.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("repository validation passed", result.stdout)

    def test_repository_validator_passes_after_skill_test_cache_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory) / "repository"
            shutil.copytree(
                ROOT,
                repository,
                ignore=shutil.ignore_patterns(
                    ".git",
                    ".venv",
                    "__pycache__",
                    "work",
                ),
            )
            scripts = (
                repository
                / "skills"
                / "generating-development-prompts"
                / "scripts"
            )
            cache = scripts / "__pycache__"
            cache.mkdir()
            (cache / "discover_context.cpython-test.pyc").write_bytes(b"\x00\xffcache")
            (scripts / "stale.pyc").write_bytes(b"\x00\xffcache")
            (scripts / "optimized.pyo").write_bytes(b"\x00\xffcache")
            (scripts / "native.pyd").write_bytes(b"\x00\xffcache")
            (scripts / ".DS_Store").write_bytes(b"\x00\xffcache")

            result = subprocess.run(
                [sys.executable, str(repository / "scripts" / "validate_repo.py")],
                cwd=repository,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("repository validation passed", result.stdout)

    def test_repository_validator_checks_files_below_cache_named_ancestor(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory) / "__pycache__" / "repository"
            shutil.copytree(
                ROOT,
                repository,
                ignore=shutil.ignore_patterns(
                    ".git",
                    ".venv",
                    "__pycache__",
                    "work",
                ),
            )
            invalid_script = (
                repository
                / "skills"
                / "generating-development-prompts"
                / "scripts"
                / "invalid.py"
            )
            invalid_script.write_text("# TODO: invalid production file\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(repository / "scripts" / "validate_repo.py")],
                cwd=repository,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("placeholder text remains", result.stderr)

    def test_validation_runtime_is_reproducible(self):
        requirements_path = ROOT / "requirements-dev.txt"
        self.assertTrue(requirements_path.is_file())
        requirements = requirements_path.read_text()
        readme = (ROOT / "README.md").read_text()
        rules = (ROOT / "AGENTS.md").read_text()
        self.assertEqual("PyYAML==6.0.3\n", requirements)
        for text in (readme, rules):
            self.assertIn(".venv/bin/python", text)
        self.assertIn("Python 3.9", readme)
        self.assertIn("Python 3.14", readme)


if __name__ == "__main__":
    unittest.main()
