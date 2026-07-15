import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("repository_validator_contract", ROOT / "scripts" / "validate_repo.py")
def copy_repository(destination: Path) -> Path:
    repository = destination / "repository"
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
    return repository


def run_repository_validator(repository: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repository / "scripts" / "validate_repo.py")],
        cwd=repository,
        text=True,
        capture_output=True,
        check=False,
    )


class RepositoryContractTests(unittest.TestCase):
    def test_evaluation_evidence_uses_minimal_results(self):
        evaluation = ROOT / "evaluations" / "creating-development-specs-and-plans"
        self.assertFalse((evaluation / "rubric.sha256").exists())
        self.assertFalse((evaluation / "rubric-history.json").exists())
        self.assertEqual([], list(evaluation.rglob("attempt-audit-*.json")))
        for relative in (
            "baseline/pre-creation-audit.json",
            "baseline/result.json",
            "migration-red/result.json",
            "green/result.json",
        ):
            payload = json.loads((evaluation / relative).read_text(encoding="utf-8"))
            self.assertNotRegex(repr(payload), r"sha256|digest|manifest")

    def test_repository_validator_requires_precreation_audit_and_migration_baseline_roles(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            evaluation = repository / "evaluations" / "creating-development-specs-and-plans"
            audit = evaluation / "baseline" / "pre-creation-audit.json"
            audit.unlink()
            missing = run_repository_validator(repository)

            shutil.copy2(
                ROOT / "evaluations" / "creating-development-specs-and-plans" / "baseline" / "pre-creation-audit.json",
                audit,
            )
            baseline = evaluation / "baseline" / "result.json"
            payload = json.loads(baseline.read_text(encoding="utf-8"))
            payload["evidence_role"] = "pre-creation-audit"
            baseline.write_text(json.dumps(payload), encoding="utf-8")
            wrong_baseline = run_repository_validator(repository)

            payload["evidence_role"] = "migration-baseline"
            baseline.write_text(json.dumps(payload), encoding="utf-8")
            payload["failures_observed"] = False
            baseline.write_text(json.dumps(payload), encoding="utf-8")
            missing_failures = run_repository_validator(repository)

        self.assertEqual(1, missing.returncode)
        self.assertIn("pre-creation audit result is required", missing.stderr)
        self.assertEqual(1, wrong_baseline.returncode)
        self.assertIn("baseline evidence_role must be migration-baseline", wrong_baseline.stderr)
        self.assertEqual(1, missing_failures.returncode)
        self.assertIn("migration baseline must record failures", missing_failures.stderr)

    def test_repository_validator_requires_valid_precreation_red(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            audit = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "baseline"
                / "pre-creation-audit.json"
            )
            payload = json.loads(audit.read_text(encoding="utf-8"))
            payload["valid_red_cases"] = []
            audit.write_text(json.dumps(payload), encoding="utf-8")

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("pre-creation audit needs valid RED cases", result.stderr)

    def test_repository_validator_requires_selected_current_skill_red_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            result_path = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "migration-red"
                / "result.json"
            )
            output = result_path.parent / "04-output.md"
            output.unlink()

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("migration-red selected case evidence is incomplete", result.stderr)

    def test_cross_skill_contract_uses_public_discovery_cli(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            spec = root / "docs" / "specs" / "2026-07-15-order-design.md"
            plan = root / "docs" / "plans" / "2026-07-15-order.md"
            spec.parent.mkdir(parents=True)
            plan.parent.mkdir(parents=True)
            spec.write_text("# Order Design\n", encoding="utf-8")
            plan.write_text(
                "---\nreview_status: approved\nreviewer: reviewer\n"
                "reviewed_at: 2026-07-15\n---\n# Order Plan\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "skills" / "generating-development-prompts" / "scripts" / "discover_context.py"),
                    "--request",
                    "order",
                    "--cwd",
                    str(root),
                    "--spec",
                    str(spec),
                    "--plan",
                    str(plan),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(str(spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertEqual(str(plan.resolve()), payload["documents"]["plan"]["path"])
        self.assertEqual("approved", payload["documents"]["plan"]["review"]["status"])

    def test_versioned_text_has_no_removed_namespace(self):
        docs = ROOT / "docs"
        unexpected = [
            path.name
            for path in docs.iterdir()
            if path.is_dir() and path.name not in {"specs", "plans"}
        ]
        self.assertEqual([], unexpected)

    def test_repository_validator_rejects_unsupported_planning_namespace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            unsupported = repository / "docs" / "legacy-planning" / "specs"
            unsupported.mkdir(parents=True)
            (unsupported / "legacy.md").write_text("# Legacy\n", encoding="utf-8")

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("unsupported docs namespace", result.stderr)

    def test_downstream_production_is_unchanged(self):
        skill = ROOT / "skills" / "generating-development-prompts"
        for path in VALIDATOR.production_files(skill):
            relative = path.relative_to(ROOT)
            committed = subprocess.run(
                ["git", "show", f"HEAD:{relative}"],
                cwd=ROOT,
                capture_output=True,
                check=False,
            )
            with self.subTest(path=relative):
                self.assertEqual(0, committed.returncode, committed.stderr.decode())
                self.assertEqual(committed.stdout, path.read_bytes())

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
        serialized = json.dumps(manifest, ensure_ascii=False).casefold()
        for phrase in (
            "approved specifications",
            "reviewed plans",
            "handoff prompts",
        ):
            self.assertIn(phrase, serialized)

    def test_both_skills_are_complete_and_exposed(self):
        for skill_name in (
            "creating-development-specs-and-plans",
            "generating-development-prompts",
        ):
            with self.subTest(skill_name=skill_name):
                skill = ROOT / "skills" / skill_name
                self.assertTrue((skill / "SKILL.md").is_file())
                self.assertTrue((skill / "agents" / "openai.yaml").is_file())

    def test_skill_trigger_descriptions_keep_authoring_and_handoff_distinct(self):
        authoring = VALIDATOR.load_skill_frontmatter(
            ROOT / "skills" / "creating-development-specs-and-plans" / "SKILL.md"
        )["description"].casefold()
        handoff = VALIDATOR.load_skill_frontmatter(
            ROOT / "skills" / "generating-development-prompts" / "SKILL.md"
        )["description"].casefold()

        self.assertIn("clarify development requirements", authoring)
        self.assertIn("implementation plan", authoring)
        self.assertNotIn("new-session development prompt", authoring)
        self.assertIn("new-session development prompt", handoff)
        self.assertIn("copyable codex development task instructions", handoff)
        self.assertNotIn("clarify development requirements", handoff)

    def test_authoring_plan_template_preserves_handoff_review_states(self):
        template = (
            ROOT
            / "skills"
            / "creating-development-specs-and-plans"
            / "assets"
            / "plan-template.md"
        ).read_text(encoding="utf-8")

        def review_status(content: str) -> str:
            with tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                spec = root / "docs" / "specs" / "2026-07-15-order-design.md"
                plan = root / "docs" / "plans" / "2026-07-15-order.md"
                spec.parent.mkdir(parents=True)
                plan.parent.mkdir(parents=True)
                spec.write_text("# Order Design\n", encoding="utf-8")
                plan.write_text(content, encoding="utf-8")
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(
                            ROOT
                            / "skills"
                            / "generating-development-prompts"
                            / "scripts"
                            / "discover_context.py"
                        ),
                        "--cwd",
                        str(root),
                        "--topic",
                        "order",
                        "--spec",
                        str(spec),
                        "--plan",
                        str(plan),
                    ],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                )
            self.assertEqual(0, completed.returncode, completed.stderr)
            return json.loads(completed.stdout)["documents"]["plan"]["review"][
                "status"
            ]

        self.assertEqual("not-approved", review_status(template))
        self.assertEqual(
            "approved",
            review_status(
                template.replace("review_status: pending", "review_status: approved", 1)
            ),
        )

    def test_repository_validator_requires_red_baseline_before_exposing_new_skill(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            baseline = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "baseline"
                / "result.json"
            )
            baseline.unlink()

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("baseline result is required", result.stderr)

    def test_repository_validator_accepts_valid_migration_baseline(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))

            result = run_repository_validator(repository)

        self.assertNotIn("baseline result is required", result.stderr)
        self.assertNotIn("migration baseline runs must be valid", result.stderr)

    def test_repository_validator_rejects_malformed_baseline_result(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            baseline = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "baseline"
                / "result.json"
            )
            baseline.write_text("not-json\n", encoding="utf-8")

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("baseline result is malformed", result.stderr)

    def test_repository_validator_rejects_invalid_migration_baseline_runs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            baseline = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "baseline"
                / "result.json"
            )
            payload = json.loads(baseline.read_text(encoding="utf-8"))
            payload["all_runs_valid"] = False
            baseline.write_text(json.dumps(payload), encoding="utf-8")

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("migration baseline runs must be valid", result.stderr)

    def test_repository_validator_requires_passing_green_evidence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            green = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "result.json"
            )
            green.parent.mkdir(parents=True, exist_ok=True)
            green.write_text(
                json.dumps({"schema_version": 1, "all_required_passed": False}),
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("green result must record all_required_passed true", result.stderr)

    def test_repository_validator_rejects_incomplete_green_evidence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            green = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "result.json"
            )
            payload = json.loads(green.read_text(encoding="utf-8"))
            payload["all_runs_valid"] = False
            payload["cases"] = []
            payload.pop("review_status", None)
            green.write_text(json.dumps(payload), encoding="utf-8")

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        for expected in (
            "green runs must all be valid",
            "green cases must exactly match the rubric",
            "green evidence must have approved independent review",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, result.stderr)

    def test_repository_validator_rejects_sensitive_evaluation_evidence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            green = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "result.json"
            )
            green.parent.mkdir(parents=True, exist_ok=True)
            green.write_text(
                json.dumps({"schema_version": 1, "all_required_passed": True}),
                encoding="utf-8",
            )
            (green.parent / "leaked-output.md").write_text(
                "machine path: /Users/example/private\n", encoding="utf-8"
            )

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("evaluation evidence contains sensitive or machine-local text", result.stderr)

    def test_repository_validator_allows_task_level_review_text(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            evidence = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "ordinary-output.md"
            )
            evidence.write_text(
                "The plan requires a task-level independent review.\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_repository_validator_allows_sensitive_data_terms_without_values(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            evidence = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "ordinary-security-text.md"
            )
            evidence.write_text(
                "The design does not store credentials, task_id values, or thread_id values.\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_skill_payloads_stage_independently_and_together(self):
        skills = [
            ROOT / "skills" / "creating-development-specs-and-plans",
            ROOT / "skills" / "generating-development-prompts",
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            homes = [root / "authoring-home", root / "handoff-home", root / "combined-home"]
            VALIDATOR.stage_skill_payloads([skills[0]], homes[0])
            VALIDATOR.stage_skill_payloads([skills[1]], homes[1])
            VALIDATOR.stage_skill_payloads(skills, homes[2])

            for index, skill in enumerate(skills):
                expected = {
                    str(path.relative_to(skill)): path.read_bytes()
                    for path in VALIDATOR.production_files(skill)
                }
                independent = homes[index] / "skills" / skill.name
                combined = homes[2] / "skills" / skill.name
                for staged in (independent, combined):
                    actual = {
                        str(path.relative_to(staged)): path.read_bytes()
                        for path in staged.rglob("*")
                        if path.is_file()
                    }
                    self.assertEqual(expected, actual)

    def test_skill_staging_refuses_existing_destination_without_overwrite(self):
        skill = ROOT / "skills" / "creating-development-specs-and-plans"
        with tempfile.TemporaryDirectory() as temporary_directory:
            home = Path(temporary_directory) / "codex-home"
            destination = home / "skills" / skill.name
            destination.mkdir(parents=True)
            sentinel = destination / "owned.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                VALIDATOR.stage_skill_payloads([skill], home)

            self.assertEqual({"owned.txt"}, {path.name for path in destination.iterdir()})
            self.assertEqual("preserve\n", sentinel.read_text(encoding="utf-8"))

    def test_handoff_skill_does_not_bundle_a_final_reviewer(self):
        skill_asset = (
            ROOT
            / "skills"
            / "generating-development-prompts"
            / "assets"
            / "final-reviewer.toml"
        )
        project_role = ROOT / ".codex" / "agents" / "final-reviewer.toml"
        workflow_role = ROOT / ".codex" / "agents" / "workflow-final-reviewer.toml"
        self.assertFalse(skill_asset.exists())
        self.assertTrue(project_role.is_file())
        self.assertTrue(workflow_role.is_file())

    def test_agent_rules_record_tdd_and_self_containment_gates(self):
        root_rules = (ROOT / "AGENTS.md").read_text()
        skill_rules = (ROOT / "skills" / "AGENTS.md").read_text()
        for phrase in [
            "RED→GREEN→REFACTOR",
            "仍须保留 RED 证据、GREEN 前向结果、仓库验证和独立评审门",
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
