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


def registered_skill_names() -> tuple[str, ...]:
    registry = json.loads(
        (ROOT / "evaluations" / "registry.json").read_text(encoding="utf-8")
    )
    return tuple(sorted(registry["skills"]))


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


def run_repository_validator(
    repository: Path, *arguments: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repository / "scripts" / "validate_repo.py"),
            *arguments,
        ],
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
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            output = result_path.parent / f"{payload['selected_case']}-output.md"
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

    def test_product_requirements_contract_uses_public_inspector_cli(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "repository"
            root.mkdir()
            (root / ".git").mkdir()
            requirements = root / "docs" / "requirements" / "order.md"
            requirements.parent.mkdir(parents=True)
            inspector = (
                ROOT
                / "skills"
                / "creating-development-specs-and-plans"
                / "scripts"
                / "inspect_product_requirements.py"
            )

            def write_prd(**overrides: str) -> None:
                fields = {
                    "document_type": "product-requirements",
                    "topic": "order-approval",
                    "scope_type": "feature",
                    "understanding_confidence": "97",
                    "understanding_user_confirmation": "approved",
                    "user_approval": "approved",
                    "independent_review": "approved",
                }
                fields.update(overrides)
                metadata = "\n".join(
                    f"{key}: {value}" for key, value in fields.items()
                )
                requirements.write_text(
                    f"---\n{metadata}\n---\n\n# Order Approval\n",
                    encoding="utf-8",
                )

            def inspect(expected_topic: str = "order-approval", expected_scope: str = "feature"):
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(inspector),
                        "--repo-root",
                        str(root),
                        "--requirements",
                        "docs/requirements/order.md",
                        "--expected-topic",
                        expected_topic,
                        "--expected-scope",
                        expected_scope,
                    ],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                return json.loads(completed.stdout)

            write_prd()
            approved = inspect()
            write_prd(user_approval="pending")
            pending = inspect()
            write_prd(independent_review="approved\nindependent_review: pending")
            unknown = inspect()
            write_prd()
            topic_mismatch = inspect(expected_topic="inventory-alert")
            scope_mismatch = inspect(expected_scope="phase")

            spec = root / "docs" / "specs" / "order.md"
            plan = root / "docs" / "plans" / "order.md"
            spec.parent.mkdir(parents=True)
            plan.parent.mkdir(parents=True)
            spec.write_text("user_approval: approved\nindependent_review: approved\n")
            plan.write_text("review_status: approved\n")
            write_prd(user_approval="pending")
            invalidated = inspect()
            implementation_gate = (
                "open"
                if invalidated["specification_gate"] == "open"
                and "user_approval: approved" in spec.read_text(encoding="utf-8")
                and "independent_review: approved" in spec.read_text(encoding="utf-8")
                and "review_status: approved" in plan.read_text(encoding="utf-8")
                else "blocked"
            )

        self.assertEqual("approved", approved["status"])
        self.assertEqual("open", approved["specification_gate"])
        self.assertEqual("not-approved", pending["status"])
        self.assertEqual("unknown", unknown["status"])
        self.assertEqual("unknown", topic_mismatch["status"])
        self.assertEqual("unknown", scope_mismatch["status"])
        self.assertEqual("blocked", invalidated["specification_gate"])
        self.assertEqual("blocked", implementation_gate)

    def test_upstream_prd_template_topic_is_accepted_by_downstream_inspector(self):
        template = (
            ROOT
            / "skills"
            / "creating-product-requirements"
            / "assets"
            / "prd-template.md"
        ).read_text(encoding="utf-8")
        document = (
            template.replace("<stable-kebab-topic>", "order-approval", 1)
            .replace("<scope-type>", "feature", 1)
            .replace("<integer-from-95-through-100>", "97", 1)
            .replace("user_approval: pending", "user_approval: approved", 1)
            .replace("independent_review: pending", "independent_review: approved", 1)
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "repository"
            root.mkdir()
            (root / ".git").mkdir()
            requirements = root / "docs" / "requirements" / "order.md"
            requirements.parent.mkdir(parents=True)
            requirements.write_text(document, encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(
                        ROOT
                        / "skills"
                        / "creating-development-specs-and-plans"
                        / "scripts"
                        / "inspect_product_requirements.py"
                    ),
                    "--repo-root",
                    str(root),
                    "--requirements",
                    str(requirements),
                    "--expected-topic",
                    "order-approval",
                    "--expected-scope",
                    "feature",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual("order-approval", payload["requirements_topic"])
        self.assertEqual("approved", payload["status"])
        self.assertEqual("open", payload["specification_gate"])

    def test_versioned_text_has_no_removed_namespace(self):
        docs = ROOT / "docs"
        unexpected = [
            path.name
            for path in docs.iterdir()
            if path.is_dir() and path.name not in {"requirements", "specs", "plans"}
        ]
        self.assertEqual([], unexpected)

    def test_repository_validator_allows_requirements_namespace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            requirements = repository / "docs" / "requirements"
            requirements.mkdir(parents=True, exist_ok=True)
            (requirements / "2026-07-15-order.md").write_text(
                "# Order requirements\n", encoding="utf-8"
            )

            result = run_repository_validator(repository)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_repository_validator_requires_evaluation_registry(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            registry = repository / "evaluations" / "registry.json"
            if registry.exists():
                registry.unlink()

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("evaluation registry is required", result.stderr)

    def test_creation_only_baseline_does_not_require_migration_red(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["creating-product-requirements"] = {
                "evaluation_mode": "managed",
                "evidence_profile": "creation-only",
                "stage": "baseline-only",
            }
            registry["skills"]["creating-development-specs-and-plans"][
                "stage"
            ] = "review-approved"
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            target = repository / "evaluations" / "creating-product-requirements"
            shutil.rmtree(target / "green")
            shutil.rmtree(repository / "skills" / "creating-product-requirements")
            authoring_green_path = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "result.json"
            )
            authoring_green = json.loads(
                authoring_green_path.read_text(encoding="utf-8")
            )
            authoring_green.update(
                {
                    "review_status": "approved",
                    "reviewer": "test-independent-reviewer",
                    "reviewed_at": "2026-07-15",
                }
            )
            authoring_green_path.write_text(
                json.dumps(authoring_green, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_evidence_only_allows_pending_review_but_strict_validation_blocks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["creating-development-specs-and-plans"][
                "stage"
            ] = "implemented"
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            green_path = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "result.json"
            )
            green = json.loads(green_path.read_text(encoding="utf-8"))
            green["review_status"] = "pending"
            green_path.write_text(
                json.dumps(green, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            strict = run_repository_validator(repository)
            evidence = run_repository_validator(
                repository,
                "--evidence-only",
                "creating-development-specs-and-plans",
            )

        self.assertEqual(1, strict.returncode)
        self.assertIn("implemented evidence is not review-approved", strict.stderr)
        self.assertEqual(0, evidence.returncode, evidence.stdout + evidence.stderr)

    def test_repository_validator_requires_versioned_case_outputs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            evaluation = (
                repository / "evaluations" / "creating-development-specs-and-plans"
            )
            (evaluation / "baseline" / "01-output.md").unlink()
            missing_baseline = run_repository_validator(repository)

            shutil.copy2(
                ROOT
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "baseline"
                / "01-output.md",
                evaluation / "baseline" / "01-output.md",
            )
            (evaluation / "green" / "01-output.md").unlink()
            missing_green = run_repository_validator(repository)

        self.assertEqual(1, missing_baseline.returncode)
        self.assertIn("baseline case 01 output is required", missing_baseline.stderr)
        self.assertEqual(1, missing_green.returncode)
        self.assertIn("green case 01 output is required", missing_green.stderr)

    def test_repository_validator_rejects_unregistered_or_invalid_baseline_cases(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            evaluation = (
                repository / "evaluations" / "creating-development-specs-and-plans"
            )
            (evaluation / "cases" / "99-unregistered.md").write_text(
                "unregistered case\n", encoding="utf-8"
            )
            extra_case = run_repository_validator(repository)

            (evaluation / "cases" / "99-unregistered.md").unlink()
            baseline_path = evaluation / "baseline" / "result.json"
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
            baseline["cases"][0]["valid"] = False
            baseline_path.write_text(
                json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            invalid_case = run_repository_validator(repository)

        self.assertEqual(1, extra_case.returncode)
        self.assertIn("case files must exactly match the rubric", extra_case.stderr)
        self.assertEqual(1, invalid_case.returncode)
        self.assertIn("baseline case 01 is invalid", invalid_case.stderr)

    def test_creation_plus_current_red_allows_cases_added_after_creation_baseline(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["creating-development-specs-and-plans"][
                "stage"
            ] = "implemented"
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = run_repository_validator(
                repository,
                "--evidence-only",
                "creating-development-specs-and-plans",
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_repository_validator_reports_malformed_audit_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            audit_path = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "baseline"
                / "pre-creation-audit.json"
            )
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit["valid_red_cases"] = 7
            audit_path.write_text(
                json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("pre-creation audit needs valid RED cases", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_repository_validator_reports_malformed_rubric_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            rubric_path = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "rubric.json"
            )
            rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
            rubric["criteria"] = 7
            rubric_path.write_text(
                json.dumps(rubric, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("rubric is malformed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_repository_validator_requires_review_approval_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            green_path = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "result.json"
            )
            green = json.loads(green_path.read_text(encoding="utf-8"))
            green.pop("reviewer")
            green.pop("reviewed_at")
            green_path.write_text(
                json.dumps(green, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("green evidence approval metadata is incomplete", result.stderr)

    def test_evidence_only_ignores_other_managed_skill_review_stage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["creating-development-specs-and-plans"][
                "stage"
            ] = "implemented"
            registry["skills"]["creating-product-requirements"][
                "stage"
            ] = "implemented"
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            green_path = (
                repository / "evaluations" / "creating-product-requirements"
                / "green"
                / "result.json"
            )
            green = json.loads(green_path.read_text(encoding="utf-8"))
            green["review_status"] = "pending"
            green.pop("reviewer", None)
            green.pop("reviewed_at", None)
            green_path.write_text(
                json.dumps(green, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(
                repository, "--evidence-only", "creating-product-requirements"
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_repository_validator_rejects_invalid_imported_registry_entry(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["generating-development-prompts"][
                "evidence_profile"
            ] = "creation-only"
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "generating-development-prompts: evaluation registry entry is invalid",
            result.stderr,
        )

    def test_repository_validator_rejects_unregistered_skill_and_orphan_evidence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            skill = repository / "skills" / "unregistered-skill"
            (skill / "agents").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: unregistered-skill\n"
                "description: Use when testing validation.\n---\n",
                encoding="utf-8",
            )
            (skill / "agents" / "openai.yaml").write_text(
                "interface: {}\n", encoding="utf-8"
            )
            (repository / "evaluations" / "orphan-evidence").mkdir()

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("unregistered-skill: active skill is not registered", result.stderr)
        self.assertIn(
            "orphan-evidence: orphan evaluation evidence is not registered",
            result.stderr,
        )

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
            "approved product requirements",
            "technical specifications",
            "reviewed plans",
            "handoff prompts",
            "bounded changes",
            "agents rules",
        ):
            self.assertIn(phrase, serialized)

    def test_all_registered_skills_are_complete_and_exposed(self):
        self.assertEqual(5, len(registered_skill_names()))
        for skill_name in registered_skill_names():
            with self.subTest(skill_name=skill_name):
                skill = ROOT / "skills" / skill_name
                self.assertTrue((skill / "SKILL.md").is_file())
                self.assertTrue((skill / "agents" / "openai.yaml").is_file())

    def test_skill_trigger_descriptions_keep_authoring_and_handoff_distinct(self):
        requirements = VALIDATOR.load_skill_frontmatter(
            ROOT / "skills" / "creating-product-requirements" / "SKILL.md"
        )["description"].casefold()
        authoring = VALIDATOR.load_skill_frontmatter(
            ROOT / "skills" / "creating-development-specs-and-plans" / "SKILL.md"
        )["description"].casefold()
        handoff = VALIDATOR.load_skill_frontmatter(
            ROOT / "skills" / "generating-development-prompts" / "SKILL.md"
        )["description"].casefold()
        bounded = VALIDATOR.load_skill_frontmatter(
            ROOT / "skills" / "implementing-bounded-changes" / "SKILL.md"
        )["description"].casefold()
        governance_path = ROOT / "skills" / "managing-agents-rules" / "SKILL.md"
        self.assertTrue(governance_path.is_file())
        governance = VALIDATOR.load_skill_frontmatter(governance_path)[
            "description"
        ].casefold()

        self.assertIn("product requirements", requirements)
        self.assertIn("product scope", requirements)
        self.assertIn("user scenarios", requirements)
        self.assertNotIn("implementation plan", requirements)
        self.assertIn("approved product requirements", authoring)
        self.assertIn("technical specification", authoring)
        self.assertIn("implementation plan", authoring)
        self.assertNotIn("new-session development prompt", authoring)
        self.assertIn("new-session development prompt", handoff)
        self.assertIn("copyable codex development task instructions", handoff)
        self.assertNotIn("approved product requirements", handoff)
        self.assertIn("explicitly approved implementation", bounded)
        self.assertIn("bug fix", bounded)
        self.assertIn("bounded change", bounded)
        self.assertNotIn("product requirements", bounded)
        self.assertNotIn("development prompt", bounded)
        self.assertIn("agents rules", governance)
        self.assertIn("substantive development", governance)
        self.assertIn("completion", governance)
        self.assertNotIn("product requirements", governance)
        self.assertNotIn("bounded change", governance)

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
        skills = [ROOT / "skills" / name for name in registered_skill_names()]
        self.assertEqual(
            [],
            [skill.name for skill in skills if not (skill / "SKILL.md").is_file()],
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            homes = [root / f"skill-{index}-home" for index in range(len(skills))]
            combined_home = root / "combined-home"
            for index, skill in enumerate(skills):
                VALIDATOR.stage_skill_payloads([skill], homes[index])
            VALIDATOR.stage_skill_payloads(skills, combined_home)

            for index, skill in enumerate(skills):
                expected = {
                    str(path.relative_to(skill)): path.read_bytes()
                    for path in VALIDATOR.production_files(skill)
                }
                independent = homes[index] / "skills" / skill.name
                combined = combined_home / "skills" / skill.name
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
            "creating-product-requirements",
            "PRD",
            "五个 skill",
            "managing-agents-rules",
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
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            result = run_repository_validator(repository)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("repository validation passed", result.stdout)

    def test_five_skill_workflow_docs_and_final_reviewer_are_current(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        reviewer = (
            ROOT / ".codex" / "agents" / "workflow-final-reviewer.toml"
        ).read_text(encoding="utf-8")
        for skill_name in registered_skill_names():
            with self.subTest(skill_name=skill_name):
                self.assertIn(skill_name, readme)
                self.assertIn(skill_name, changelog)
        self.assertIn("PRD → technical spec/plan → development prompt", readme)
        self.assertIn("approved bounded change → implementation", readme)
        self.assertIn("AGENTS rule governance", readme)
        self.assertIn("五个 skill", rules)
        self.assertIn("两个 authoring skill", reviewer)
        self.assertIn("prompt skill", reviewer)
        self.assertIn("bounded implementation skill", reviewer)
        self.assertIn("managing-agents-rules", reviewer)
        self.assertIn("五-skill plugin", reviewer)

    def test_repository_validator_dynamically_requires_public_skill_discovery(self):
        public_documents = (
            "README.md",
            "docs/install.md",
            "docs/workflow.md",
            "docs/agent-development.md",
            "CHANGELOG.md",
        )
        review_approved = next(
            name
            for name, entry in json.loads(
                (ROOT / "evaluations" / "registry.json").read_text(encoding="utf-8")
            )["skills"].items()
            if entry["stage"] == "review-approved"
        )
        for relative in public_documents:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                repository = copy_repository(Path(directory))
                document = repository / relative
                document.write_text(
                    document.read_text(encoding="utf-8").replace(
                        review_approved, "omitted-skill"
                    ),
                    encoding="utf-8",
                )

                result = run_repository_validator(repository)

                self.assertEqual(1, result.returncode)
                self.assertIn("review-approved skill is missing from", result.stderr)

            with self.subTest(relative=relative, stage="baseline-only"), tempfile.TemporaryDirectory() as directory:
                repository = copy_repository(Path(directory))
                registry_path = repository / "evaluations" / "registry.json"
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                registry["skills"][review_approved]["stage"] = "baseline-only"
                registry_path.write_text(
                    json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                shutil.rmtree(repository / "skills" / review_approved)
                document = repository / relative
                document.write_text(
                    document.read_text(encoding="utf-8").replace(
                        review_approved, "omitted-skill"
                    ),
                    encoding="utf-8",
                )

                result = run_repository_validator(repository)

                self.assertNotIn("review-approved skill is missing from", result.stderr)

    def test_repository_validator_passes_after_skill_test_cache_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
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
