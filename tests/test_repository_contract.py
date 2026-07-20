import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CANONICAL_REQUIREMENTS_FIELDS = (
    "requirements_path",
    "requirements_topic",
    "requirements_scope",
    "understanding_confidence",
    "understanding_user_confirmation",
    "requirements_user_approval",
    "requirements_independent_review",
    "specification_gate",
)
CANONICAL_FOURTEEN_FIELDS = (
    "requirements_path",
    "requirements_topic",
    "requirements_scope",
    "requirements_understanding_confidence",
    "requirements_understanding_confirmation",
    "requirements_user_approval",
    "requirements_independent_review",
    "specification_gate",
    "spec_path",
    "spec_user_approval",
    "spec_independent_review",
    "plan_path",
    "plan_review_status",
    "implementation_gate",
)


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


def configure_evidence_only_target(repository: Path, skill_name: str) -> None:
    registry_path = repository / "evaluations" / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["skills"][skill_name]["stage"] = "implemented"
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    green_path = repository / "evaluations" / skill_name / "green" / "result.json"
    green = json.loads(green_path.read_text(encoding="utf-8"))
    green["review_status"] = "pending"
    green.pop("reviewer", None)
    green.pop("reviewed_at", None)
    green_path.write_text(
        json.dumps(green, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def chinese_handoff_schema(relative_path: str) -> list[tuple[str, tuple[str, ...]]]:
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    blocks = re.findall(r"```text\n(.*?)\n```", text, re.DOTALL)
    assert len(blocks) >= 2
    schema = []
    known_values = {
        "产品", "阶段", "功能", "未确定", "未知", "待确认", "已确认",
        "待批准", "已批准", "待评审", "已通过", "未开放", "已开放",
        "尚未创建", "未开始", "未通过",
    }
    for line in blocks[1].splitlines():
        label, raw_values = line.split("：", 1)
        raw_values = raw_values.strip()
        if raw_values.startswith("<") and raw_values.endswith(">"):
            raw_values = raw_values[1:-1]
        values = []
        for value in raw_values.split("|"):
            normalized = value.strip().strip("<>")
            values.append(normalized if normalized in known_values else "<dynamic>")
        schema.append((label, tuple(values)))
    return schema


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
            .replace("<产品-阶段-或-功能>", "功能", 1)
            .replace("<95-100-整数>", "97", 1)
            .replace(
                "用户批准: 待批准",
                "用户批准: 已批准\n批准日期: 2026-07-19",
                1,
            )
            .replace(
                "独立评审: 待评审",
                "独立评审: 已通过\n"
                "独立评审角色: product-analyst\n"
                "独立评审日期: 2026-07-19",
                1,
            )
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
            configure_evidence_only_target(
                repository, "creating-development-specs-and-plans"
            )
            requirements = repository / "docs" / "requirements"
            requirements.mkdir(parents=True, exist_ok=True)
            (requirements / "2026-07-15-order.md").write_text(
                "# Order requirements\n", encoding="utf-8"
            )

            result = run_repository_validator(
                repository,
                "--evidence-only",
                "creating-development-specs-and-plans",
            )

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
            rubric_path = target / "rubric.json"
            rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
            for criterion in rubric["criteria"]:
                criterion["applies_to"] = [
                    case_id
                    for case_id in criterion["applies_to"]
                    if case_id
                    not in {
                        "09", "10", "11", "12", "13", "14", "15", "16",
                        "17", "18", "19", "20",
                    }
                ]
            rubric["criteria"] = [
                criterion
                for criterion in rubric["criteria"]
                if criterion["applies_to"]
            ]
            rubric_path.write_text(
                json.dumps(rubric, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            for case_name in (
                "09-approved-auto-spec-transition.md",
                "10-chinese-handoff-status.md",
                "11-ordinary-compact.md",
                "12-independent-question-batch.md",
                "13-dependent-question.md",
                "14-progressive-reference-loading.md",
                "15-progress-only-full.md",
                "16-content-only-deliverable.md",
                "17-localized-prd-approval-writeback.md",
                "18-legacy-english-prd-rereview.md",
                "19-localized-prd-write-reconciliation.md",
                "20-routed-standard-prd-handoff.md",
            ):
                (target / "cases" / case_name).unlink()
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

            registry["skills"]["generating-development-prompts"][
                "stage"
            ] = "review-approved"
            prompt_green_path = (
                repository
                / "evaluations"
                / "generating-development-prompts"
                / "green"
                / "result.json"
            )
            prompt_green = json.loads(prompt_green_path.read_text(encoding="utf-8"))
            prompt_green.update(
                {
                    "review_status": "approved",
                    "reviewer": "test-independent-reviewer",
                    "reviewed_at": "2026-07-15",
                }
            )
            prompt_green_path.write_text(
                json.dumps(prompt_green, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            for skill_name, entry in registry["skills"].items():
                if skill_name == "creating-product-requirements" or entry["stage"] == "baseline-only":
                    continue
                entry["stage"] = "review-approved"
                green_path = repository / "evaluations" / skill_name / "green" / "result.json"
                green = json.loads(green_path.read_text(encoding="utf-8"))
                green.update(
                    review_status="approved",
                    reviewer="test-independent-reviewer",
                    reviewed_at="2026-07-15",
                )
                green_path.write_text(
                    json.dumps(green, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_evidence_only_allows_pending_review_but_strict_validation_blocks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            configure_evidence_only_target(
                repository, "creating-development-specs-and-plans"
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
            configure_evidence_only_target(
                repository, "creating-development-specs-and-plans"
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
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["creating-development-specs-and-plans"][
                "stage"
            ] = "review-approved"
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
            green.update(
                {
                    "review_status": "approved",
                    "reviewer": "test-independent-reviewer",
                    "reviewed_at": "2026-07-15",
                }
            )
            green.pop("reviewer")
            green_path.write_text(
                json.dumps(green, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(
                repository,
                "--reviewed-skill",
                "creating-development-specs-and-plans",
            )

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

    def test_imported_current_red_profile_supports_evidence_and_review_gates(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["generating-development-prompts"] = {
                "evaluation_mode": "imported",
                "evidence_profile": "imported-plus-current-red",
                "stage": "implemented",
            }
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            evaluation = repository / "evaluations" / "generating-development-prompts"
            if evaluation.exists():
                shutil.rmtree(evaluation)
            (evaluation / "cases").mkdir(parents=True)
            (evaluation / "migration-red").mkdir()
            (evaluation / "green").mkdir()
            (evaluation / "rubric.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "criteria": [
                            {
                                "id": "routing",
                                "applies_to": ["01"],
                                "pass": "Routes.",
                                "fail": "Does not route.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (evaluation / "cases" / "01-routing.md").write_text(
                "route\n", encoding="utf-8"
            )
            (evaluation / "migration-red" / "01-output.md").write_text(
                "red\n", encoding="utf-8"
            )
            (evaluation / "migration-red" / "result.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "evidence_role": "current-skill-red",
                        "selected_case": "01",
                        "valid": True,
                        "red_observed": True,
                        "failed_criteria": ["routing"],
                    }
                ),
                encoding="utf-8",
            )
            (evaluation / "green" / "01-output.md").write_text(
                "green\n", encoding="utf-8"
            )
            (evaluation / "green" / "result.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "evidence_role": "green",
                        "target_skill_loaded": True,
                        "all_runs_valid": True,
                        "all_required_passed": True,
                        "fresh_cases": ["01"],
                        "review_status": "pending",
                        "cases": [
                            {
                                "id": "01",
                                "valid": True,
                                "passed_criteria": ["routing"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            evidence = run_repository_validator(
                repository, "--evidence-only", "generating-development-prompts"
            )
            strict = run_repository_validator(repository)

        self.assertEqual(0, evidence.returncode, evidence.stdout + evidence.stderr)
        self.assertEqual(1, strict.returncode)
        self.assertIn("implemented evidence is not review-approved", strict.stderr)

    def test_repository_validator_rejects_green_when_target_skill_was_not_loaded(self):
        for target_skill_loaded in (False, None):
            with self.subTest(target_skill_loaded=target_skill_loaded):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    repository = copy_repository(Path(temporary_directory))
                    result_path = (
                        repository
                        / "evaluations"
                        / "generating-development-prompts"
                        / "green"
                        / "result.json"
                    )
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    if target_skill_loaded is None:
                        result.pop("target_skill_loaded", None)
                    else:
                        result["target_skill_loaded"] = target_skill_loaded
                    result_path.write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )

                    validation = run_repository_validator(
                        repository,
                        "--evidence-only",
                        "generating-development-prompts",
                    )

                self.assertEqual(1, validation.returncode)
                self.assertIn(
                    "generating-development-prompts: green target skill must be loaded",
                    validation.stderr,
                )

    def test_imported_current_red_profile_rejects_missing_selected_red_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["generating-development-prompts"] = {
                "evaluation_mode": "imported",
                "evidence_profile": "imported-plus-current-red",
                "stage": "implemented",
            }
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            evaluation = repository / "evaluations" / "generating-development-prompts"
            if evaluation.exists():
                shutil.rmtree(evaluation)
            (evaluation / "cases").mkdir(parents=True)
            (evaluation / "migration-red").mkdir()
            (evaluation / "green").mkdir()
            (evaluation / "rubric.json").write_text(
                json.dumps(
                    {"criteria": [{"id": "routing", "applies_to": ["01"]}]}
                ),
                encoding="utf-8",
            )
            (evaluation / "cases" / "01-routing.md").write_text("route\n", encoding="utf-8")
            (evaluation / "migration-red" / "result.json").write_text(
                json.dumps(
                    {
                        "evidence_role": "current-skill-red",
                        "selected_case": "01",
                        "valid": True,
                        "red_observed": True,
                        "failed_criteria": ["routing"],
                    }
                ),
                encoding="utf-8",
            )

            result = run_repository_validator(
                repository, "--evidence-only", "generating-development-prompts"
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("migration-red selected case evidence is incomplete", result.stderr)

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

    def test_required_repository_surfaces_exist(self):
        required = [
            ROOT / "AGENTS.md",
            ROOT / "skills" / "AGENTS.md",
            ROOT / "tests" / "AGENTS.md",
            ROOT / "evaluations" / "AGENTS.md",
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / ".agents" / "plugins" / "marketplace.json",
            ROOT / ".codex" / "agents" / "skill-reviewer.toml",
            ROOT / ".codex" / "agents" / "final-reviewer.toml",
            ROOT / ".codex" / "agents" / "workflow-final-reviewer.toml",
            ROOT / "scripts" / "validate_repo.py",
            ROOT / "README.md",
            ROOT / "docs" / "release-notes.md",
            ROOT / "CHANGELOG.md",
            ROOT / "requirements-dev.txt",
        ]
        self.assertEqual([], [str(path.relative_to(ROOT)) for path in required if not path.is_file()])

    def test_plugin_manifest_owns_the_skills_directory(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual("development-workflow", manifest["name"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertRegex(manifest["version"], r"^[0-9]+\.[0-9]+\.[0-9]+$")
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
        self.assertIn("automatically continue", serialized)
        self.assertIn("session routing", serialized)
        default_prompts = manifest["interface"]["defaultPrompt"]
        self.assertIsInstance(default_prompts, list)
        self.assertGreaterEqual(len(default_prompts), 1)
        self.assertLessEqual(len(default_prompts), 3)
        self.assertTrue(all(isinstance(prompt, str) for prompt in default_prompts))
        self.assertTrue(all(len(prompt) <= 128 for prompt in default_prompts))

    def test_plugin_marketplace_exposes_the_root_plugin_from_git(self):
        manifest = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("development-workflow", marketplace["name"])
        self.assertEqual(
            "Development Workflow (dw)",
            marketplace["interface"]["displayName"],
        )
        self.assertEqual(1, len(marketplace["plugins"]))

        entry = marketplace["plugins"][0]
        self.assertEqual("development-workflow", entry["name"])
        self.assertEqual(
            {
                "source": "url",
                "url": "https://github.com/itstarts/development-workflow.git",
                "ref": f"v{manifest['version']}",
            },
            entry["source"],
        )
        self.assertEqual(
            {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            entry["policy"],
        )
        self.assertEqual("Productivity", entry["category"])

    def test_repository_validator_rejects_invalid_plugin_marketplace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            marketplace = repository / ".agents" / "plugins" / "marketplace.json"
            marketplace.parent.mkdir(parents=True, exist_ok=True)
            marketplace.write_text(
                '{"name":"wrong-marketplace","plugins":[]}\n',
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("invalid plugin marketplace", result.stderr)

    def test_repository_validator_rejects_marketplace_ref_not_matching_version(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            marketplace_path = repository / ".agents" / "plugins" / "marketplace.json"
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            marketplace["plugins"][0]["source"]["ref"] = "main"
            marketplace_path.write_text(
                json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_repository_validator(repository)

        self.assertEqual(1, result.returncode)
        self.assertIn("manifest version tag", result.stderr)

    def test_public_docs_include_marketplace_install_path(self):
        manifest = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        release_tag = f"v{manifest['version']}"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        install = (ROOT / "docs" / "install.md").read_text(encoding="utf-8")
        text = readme + install
        self.assertIn(
            f"codex plugin marketplace add itstarts/development-workflow --ref {release_tag}",
            text,
        )
        self.assertIn(
            "codex plugin add development-workflow@development-workflow",
            text,
        )
        self.assertIn(
            "只固定 marketplace catalog 的快照，不能覆盖 entry 自己的 plugin Git ref",
            text,
        )
        self.assertIn(
            "catalog 和 plugin entry 均固定到同一个已验证 tag",
            text,
        )
        self.assertIn(
            "verify_install.py` 只验证 `skill-installer` 写入的 skill 目录",
            text,
        )
        self.assertIn(
            "plugins/cache/<marketplace-name>/<plugin-name>/<version-or-local>",
            text,
        )
        self.assertIn(
            "不能用远端 `main` 的安装结果替代当前候选证据",
            text,
        )

    def test_release_notes_policy_and_release_metadata_are_current(self):
        manifest = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        version = manifest["version"]
        policy_path = ROOT / "docs" / "release-notes.md"
        self.assertTrue(policy_path.is_file())
        policy = policy_path.read_text(encoding="utf-8")
        rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        agent_development = (ROOT / "docs" / "agent-development.md").read_text(
            encoding="utf-8"
        )
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

        self.assertIn("第一节必须是 `## 本版内容`", policy)
        self.assertIn("不直接复制 commit 列表", policy)
        self.assertIn("/tree/vCURRENT", policy)
        self.assertIn("/compare/vPREVIOUS...vCURRENT", policy)
        self.assertIn("```markdown\n## 本版内容", policy)
        self.assertIn("docs/release-notes.md", rules)
        release_audit_contract = rules + agent_development
        for phrase in (
            "没有已审计的不可变 tag",
            "已审计 tag 仍为当前 HEAD 的祖先",
            "该 tag 之后新增的可达 commit/blob",
            "增量扫描异常时恢复完整历史扫描",
            "git merge-base --is-ancestor <baseline-tag> HEAD",
        ):
            with self.subTest(release_audit_contract=phrase):
                self.assertIn(phrase, release_audit_contract)
        for phrase in (
            "已审计不可变 tag",
            "当前树及该 tag 之后新增的可达 commit/blob",
            "增量扫描异常时恢复完整历史扫描",
        ):
            with self.subTest(security_release_audit_contract=phrase):
                self.assertIn(phrase, security)
        self.assertNotIn("公开发布前应同时扫描当前树和完整 Git 历史", security)
        self.assertRegex(
            changelog,
            rf"(?m)^## {re.escape(version)} - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$",
        )
        self.assertNotIn(f"## {version} - Unreleased", changelog)
        self.assertIn(f"`v{version}`", security)
        self.assertIn("`main`", security)
        self.assertIn("六个 skill", security)
        self.assertNotIn("尚未发布 tag", security)
        self.assertNotIn("三个 skill", security)

    def test_public_workflow_defines_exact_automatic_handoff_mapping(self):
        workflow = (ROOT / "docs" / "workflow.md").read_text(encoding="utf-8")
        mapping = (
            ("requirements_path", "requirements_path"),
            ("requirements_topic", "requirements_topic"),
            ("requirements_scope", "requirements_scope"),
            ("understanding_confidence", "requirements_understanding_confidence"),
            (
                "understanding_user_confirmation",
                "requirements_understanding_confirmation",
            ),
            ("requirements_user_approval", "requirements_user_approval"),
            ("requirements_independent_review", "requirements_independent_review"),
            ("specification_gate", "specification_gate"),
        )
        for upstream, downstream in mapping:
            with self.subTest(upstream=upstream):
                self.assertIn(f"| `{upstream}` | `{downstream}` |", workflow)
        self.assertIn("进入下游前复验失败", workflow)
        self.assertIn("不构造十四字段", workflow)
        self.assertIn("进入下游后复验失败", workflow)
        self.assertIn("仍输出完整十四字段", workflow)

    def test_public_workflow_routes_verified_fourteen_fields_with_manual_compatibility(self):
        workflow = (ROOT / "docs" / "workflow.md").read_text(encoding="utf-8")
        self.assertIn("重新验证并冻结十四字段快照", workflow)
        for route in ("current-session", "new-session", "blocked"):
            self.assertIn(f"`{route}`", workflow)
        self.assertIn("自动路由回复仍以同一中文十四字段视图结尾", workflow)
        self.assertIn("手动提示词请求", workflow)
        self.assertIn("不伪造 requirements 或双门状态", workflow)
        self.assertIn("等待用户显式实施批准", workflow)
        self.assertIn("英文 canonical", workflow)
        self.assertIn("旧英文八字段和十四字段输入", workflow)
        self.assertIn("映射失败", workflow)
        self.assertIn("不附加状态块", workflow)
        self.assertIn("`render_prompt.py` stdout", workflow)
        self.assertIn("状态块位于动态代码框之外", workflow)

    def test_three_skills_share_renderer_mapping_without_prompt_duplication(self):
        requirements = chinese_handoff_schema(
            "skills/creating-product-requirements/references/review-and-handoff.md"
        )
        specs = chinese_handoff_schema(
            "skills/creating-development-specs-and-plans/references/review-and-handoff.md"
        )
        self.assertEqual(requirements, specs[:8])
        policy = (
            ROOT
            / "skills"
            / "generating-development-prompts"
            / "references"
            / "session-routing-policy.md"
        ).read_text(encoding="utf-8")
        self.assertIn("sole presentation validator", policy)
        self.assertNotIn("需求文档：<", policy)
        renderers = [
            (
                ROOT / "skills" / skill / "scripts" / "render_handoff.py"
            ).read_bytes()
            for skill in (
                "creating-product-requirements",
                "creating-development-specs-and-plans",
                "generating-development-prompts",
            )
        ]
        self.assertEqual(renderers[0], renderers[1])
        self.assertEqual(renderers[1], renderers[2])

    def test_versioned_prd_handoff_is_unique_ordered_chinese_final_suffix(self):
        output = (
            ROOT / "evaluations" / "creating-product-requirements" / "green" / "10-output.md"
        ).read_text(encoding="utf-8")
        expected = [
            "需求文档：/workspace/fixture/docs/requirements/2026-07-15-order-approval.md",
            "需求主题：order-approval",
            "需求范围：功能",
            "需求理解置信度：97",
            "需求理解确认：已确认",
            "需求文档用户批准：已批准",
            "需求文档独立评审：已通过",
            "技术规格门禁：已开放",
        ]
        self.assertEqual(expected, output.rstrip().splitlines()[-8:])
        for line in expected:
            label = line.split("：", 1)[0]
            with self.subTest(label=label):
                self.assertEqual(1, len(re.findall(rf"(?m)^{re.escape(label)}：", output)))
        for field in CANONICAL_REQUIREMENTS_FIELDS:
            with self.subTest(hidden_field=field):
                self.assertEqual(0, len(re.findall(rf"(?m)^{field}:", output)))

    def test_versioned_fourteen_field_handoff_is_unique_ordered_final_suffix(self):
        output = (
            ROOT
            / "evaluations"
            / "creating-development-specs-and-plans"
            / "green"
            / "12-output.md"
        ).read_text(encoding="utf-8")
        expected = [
            "需求文档：/workspace/fixture/docs/requirements/2026-07-12-order-approval.md",
            "需求主题：order-approval",
            "需求范围：功能",
            "需求理解置信度：97",
            "需求理解确认：已确认",
            "需求文档用户批准：已批准",
            "需求文档独立评审：已通过",
            "技术规格门禁：已开放",
            "技术规格：/workspace/fixture/docs/specs/2026-07-12-order-approval-design.md",
            "技术规格用户批准：已批准",
            "技术规格独立评审：已通过",
            "实施计划：/workspace/fixture/docs/plans/2026-07-12-order-approval.md",
            "计划评审状态：已通过",
            "实施门禁：已开放",
        ]
        self.assertEqual(expected, output.rstrip().splitlines()[-14:])
        for line in expected:
            label = line.split("：", 1)[0]
            with self.subTest(label=label):
                self.assertEqual(1, len(re.findall(rf"(?m)^{re.escape(label)}：", output)))
        for field in CANONICAL_FOURTEEN_FIELDS:
            with self.subTest(hidden_field=field):
                self.assertEqual(0, len(re.findall(rf"(?m)^{field}:", output)))

    def test_versioned_prompt_routing_handoffs_use_unique_field_labels(self):
        labels = (
            "需求文档", "需求主题", "需求范围", "需求理解置信度", "需求理解确认",
            "需求文档用户批准", "需求文档独立评审", "技术规格门禁", "技术规格",
            "技术规格用户批准", "技术规格独立评审", "实施计划", "计划评审状态", "实施门禁",
        )
        green = ROOT / "evaluations" / "generating-development-prompts" / "green"
        for case_id in ("01", "02", "03", "04"):
            output = (green / f"{case_id}-output.md").read_text(encoding="utf-8")
            suffix = output.rstrip().splitlines()[-14:]
            with self.subTest(case_id=case_id, contract="suffix-order"):
                self.assertEqual(list(labels), [line.split("：", 1)[0] for line in suffix])
            for label in labels:
                with self.subTest(case_id=case_id, label=label):
                    self.assertEqual(
                        1,
                        len(re.findall(rf"(?m)^{re.escape(label)}：", output)),
                    )
            for field in CANONICAL_FOURTEEN_FIELDS:
                with self.subTest(case_id=case_id, hidden_field=field):
                    self.assertEqual(0, len(re.findall(rf"(?m)^{field}:", output)))

    def test_prd_changelog_reports_all_current_green_scenarios(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("19 个 GREEN 场景", changelog)

    def test_authoring_templates_use_chinese_titles_and_sections(self):
        expected = {
            "skills/creating-product-requirements/assets/prd-template.md": (
                "# <产品需求名称>",
                "## 产品问题",
                "## 验收标准",
            ),
            "skills/creating-development-specs-and-plans/assets/spec-template.md": (
                "# <功能名称>技术规格",
                "## 当前证据",
                "## 测试与文档",
            ),
            "skills/creating-development-specs-and-plans/assets/plan-template.md": (
                "# <功能名称>实施计划",
                "## 全局约束",
                "## 最终验证",
            ),
        }
        for relative, headings in expected.items():
            content = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                for heading in headings:
                    self.assertIn(heading, content)

    def test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate(self):
        template = (
            ROOT
            / "skills"
            / "creating-product-requirements"
            / "assets"
            / "prd-template.md"
        ).read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", template, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertEqual(
            [
                "文档类型",
                "主题",
                "范围类型",
                "理解置信度",
                "需求理解确认",
                "用户批准",
                "独立评审",
            ],
            [line.split(":", 1)[0] for line in match.group(1).splitlines()],
        )
        for legacy_key in (
            "document_type",
            "topic",
            "scope_type",
            "understanding_confidence",
            "understanding_user_confirmation",
            "user_approval",
            "independent_review",
        ):
            with self.subTest(legacy_key=legacy_key):
                self.assertNotRegex(match.group(1), rf"(?m)^{legacy_key}:")

        handoff = (
            ROOT
            / "skills"
            / "creating-product-requirements"
            / "references"
            / "review-and-handoff.md"
        ).read_text(encoding="utf-8")
        canonical = re.search(r"```text\n(.*?)\n```", handoff, re.DOTALL)
        self.assertIsNotNone(canonical)
        self.assertEqual(
            list(CANONICAL_REQUIREMENTS_FIELDS),
            [line.split(":", 1)[0] for line in canonical.group(1).splitlines()],
        )

        localized_templates = {
            "skills/creating-development-specs-and-plans/assets/spec-template.md": [
                "文档类型", "主题", "需求文档", "需求主题", "需求范围",
                "需求理解置信度", "需求理解确认", "需求文档用户批准",
                "需求文档独立评审", "技术规格门禁", "技术规格用户批准",
                "技术规格独立评审",
            ],
            "skills/creating-development-specs-and-plans/assets/plan-template.md": [
                "文档类型", "主题", "技术规格", "技术规格用户批准", "评审模式", "计划评审状态",
            ],
        }
        for relative, expected_keys in localized_templates.items():
            content = (ROOT / relative).read_text(encoding="utf-8")
            localized = re.match(r"\A---\n(.*?)\n---\n", content, re.DOTALL)
            self.assertIsNotNone(localized)
            with self.subTest(relative=relative):
                self.assertEqual(
                    expected_keys,
                    [line.split(":", 1)[0] for line in localized.group(1).splitlines()],
                )

        workflow_handoff = (
            ROOT
            / "skills"
            / "creating-development-specs-and-plans"
            / "references"
            / "review-and-handoff.md"
        ).read_text(encoding="utf-8")
        workflow_canonical = re.search(
            r"```text\n(.*?)\n```", workflow_handoff, re.DOTALL
        )
        self.assertIsNotNone(workflow_canonical)
        self.assertEqual(
            list(CANONICAL_FOURTEEN_FIELDS),
            [
                line.split(":", 1)[0]
                for line in workflow_canonical.group(1).splitlines()
            ],
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            spec = root / "spec.md"
            plan = root / "plan.md"
            spec.write_text("# Localized metadata spec\n", encoding="utf-8")

            def discovered_review(plan_text: str) -> dict:
                plan.write_text(plan_text, encoding="utf-8")
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
                        "localized-metadata",
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
                return json.loads(completed.stdout)["documents"]["plan"]["review"]

            chinese = discovered_review(
                "---\n"
                "文档类型: 实施计划\n"
                "主题: localized-metadata\n"
                "技术规格: docs/specs/localized-metadata-design.md\n"
                "技术规格用户批准: 已批准\n"
                "计划评审状态: 已通过\n"
                "计划评审角色: skill-reviewer\n"
                "计划评审日期: 2026-07-19\n"
                "---\n# Plan\n"
            )
            self.assertEqual(
                {
                    "status": "approved",
                    "reviewer": "skill-reviewer",
                    "reviewed_at": "2026-07-19",
                    "implementation_gate": "open",
                },
                chinese,
            )
            self.assertEqual(
                "unknown",
                discovered_review("计划评审状态: 已通过\n\n# Plan\n")["status"],
            )

        public_workflow = (ROOT / "docs" / "workflow.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "chinese-current",
            "english-legacy",
            "英文 canonical",
            "不批量迁移",
            "legacy header 只接受 ASCII 英文字段",
        ):
            with self.subTest(public_contract=required):
                self.assertIn(required, public_workflow)

    def test_renderer_stdout_breaking_migration_is_publicly_documented(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("renderer stdout", changelog)
        self.assertIn("breaking contract change", changelog)
        self.assertIn("提取唯一 Markdown 代码框内容", changelog)
        self.assertIn(
            "首个公开版本发布为 `v0.1.0`",
            changelog,
        )
        self.assertIn("用户可见 handoff/status-block 回复后缀", changelog)
        self.assertIn("英文 canonical", changelog)
        self.assertIn("旧英文输入", changelog)
        self.assertIn("状态块不进入 prompt renderer stdout", changelog)

    def test_project_reviewer_roles_have_explicit_retention_assessment(self):
        guide = (ROOT / "docs" / "agent-development.md").read_text(encoding="utf-8")
        for role in ("skill-reviewer", "final-reviewer", "workflow-final-reviewer"):
            with self.subTest(role=role):
                self.assertIn(f"| `{role}` |", guide)
        for column in ("稳定可用性", "职责", "输入", "输出", "边界", "批准条件", "结论"):
            self.assertIn(column, guide)
        self.assertGreaterEqual(guide.count("保留"), 3)
        self.assertIn("部分职责重叠", guide)
        self.assertIn("项目专属证据范围", guide)
        self.assertGreaterEqual(guide.count("不改变任何外部状态"), 3)

    def test_all_registered_skills_are_complete_and_exposed(self):
        self.assertEqual(6, len(registered_skill_names()))
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
        routing_path = ROOT / "skills" / "routing-development-workflows" / "SKILL.md"
        self.assertTrue(routing_path.is_file())
        routing = VALIDATOR.load_skill_frontmatter(routing_path)[
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
        self.assertIn("development request", routing)
        self.assertIn("fast", routing)
        self.assertIn("standard", routing)
        self.assertIn("full", routing)
        self.assertNotIn("create a product requirements document", routing)
        self.assertIn("bug fix", bounded)
        self.assertIn("bounded change", bounded)
        self.assertNotIn("product requirements", bounded)
        self.assertNotIn("development prompt", bounded)
        self.assertIn("agents rules", governance)
        self.assertIn("substantive development", governance)
        self.assertIn("completion", governance)
        self.assertNotIn("product requirements", governance)
        self.assertNotIn("bounded change", governance)

    def test_legacy_authoring_plan_preserves_handoff_review_states(self):
        template = (
            "---\n"
            "document_type: implementation-plan\n"
            "topic: order\n"
            "spec_path: docs/specs/2026-07-15-order-design.md\n"
            "spec_user_approval: approved\n"
            "review_status: pending\n"
            "---\n\n"
            "# Order plan\n"
        )

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

    def test_authoring_and_prompt_skills_share_risk_batched_review_contract(self):
        authoring = (
            ROOT
            / "skills"
            / "creating-development-specs-and-plans"
            / "references"
            / "document-contracts.md"
        ).read_text(encoding="utf-8").casefold()
        prompt = (
            ROOT
            / "skills"
            / "generating-development-prompts"
            / "assets"
            / "development-prompt.md"
        ).read_text(encoding="utf-8").casefold()

        self.assertIn("task count", authoring)
        self.assertIn("latest complete diff", authoring)
        self.assertNotIn("task-level independent review gate", authoring)
        self.assertIn("不得仅因任务数量", prompt)
        self.assertIn("最新完整 diff", prompt)
        self.assertNotIn("独立评审未通过不得进入下一项", prompt)

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
            registry_path = repository / "evaluations" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["skills"]["creating-development-specs-and-plans"][
                "stage"
            ] = "review-approved"
            registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
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

            result = run_repository_validator(
                repository,
                "--reviewed-skill",
                "creating-development-specs-and-plans",
            )

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

    def test_public_security_policy_names_the_synthetic_fixture_root(self):
        policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8").casefold()
        self.assertIn("/workspace/fixture", policy)
        self.assertIn("合成", policy)
        self.assertIn("不是真实", policy)

    def test_repository_validator_allows_the_synthetic_fixture_root(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            configure_evidence_only_target(
                repository, "creating-development-specs-and-plans"
            )
            evidence = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "synthetic-root-output.md"
            )
            evidence.write_text(
                "fixture repository: /workspace/fixture/docs/specs/example.md\n",
                encoding="utf-8",
            )

            result = run_repository_validator(
                repository,
                "--evidence-only",
                "creating-development-specs-and-plans",
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_repository_validator_rejects_cross_platform_machine_local_evaluation_paths(self):
        machine_local_paths = (
            ("macos-private-temp", "/private/var/folders/aa/bb/T/dw-eval/fixture/output.md"),
            ("macos-var-temp", "/var/folders/aa/bb/T/dw-eval/fixture/output.md"),
            ("macos-private-tmp", "/private/tmp/dw-eval/fixture/output.md"),
            ("linux-home", "/home/example/private/output.md"),
            ("posix-temp", "/tmp/dw-eval/fixture/output.md"),
            ("windows-backslash", r"C:\Users\example\private\output.md"),
            ("windows-slash", "C:/Users/example/private/output.md"),
            ("unapproved-workspace-root", "/workspace/other/private/output.md"),
        )
        for label, machine_local_path in machine_local_paths:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary_directory:
                repository = copy_repository(Path(temporary_directory))
                configure_evidence_only_target(
                    repository, "creating-development-specs-and-plans"
                )
                evidence = (
                    repository
                    / "evaluations"
                    / "creating-development-specs-and-plans"
                    / "green"
                    / "machine-local-output.md"
                )
                evidence.write_text(
                    f"raw evaluation path: {machine_local_path}\n",
                    encoding="utf-8",
                )

                result = run_repository_validator(
                    repository,
                    "--evidence-only",
                    "creating-development-specs-and-plans",
                )

            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn(
                "evaluation evidence contains sensitive or machine-local text",
                result.stderr,
            )

    def test_repository_validator_allows_ordinary_review_policy_text(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            configure_evidence_only_target(
                repository, "creating-development-specs-and-plans"
            )
            evidence = (
                repository
                / "evaluations"
                / "creating-development-specs-and-plans"
                / "green"
                / "ordinary-output.md"
            )
            evidence.write_text(
                "The plan requires one final review of the latest complete diff.\n",
                encoding="utf-8",
            )

            result = run_repository_validator(
                repository,
                "--evidence-only",
                "creating-development-specs-and-plans",
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_repository_validator_allows_sensitive_data_terms_without_values(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = copy_repository(Path(temporary_directory))
            configure_evidence_only_target(
                repository, "creating-development-specs-and-plans"
            )
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

            result = run_repository_validator(
                repository,
                "--evidence-only",
                "creating-development-specs-and-plans",
            )

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

    def test_repository_reviewers_use_risk_batched_latest_diff_contract(self):
        rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8").casefold()
        final_reviewer = (
            ROOT / ".codex" / "agents" / "final-reviewer.toml"
        ).read_text(encoding="utf-8").casefold()
        workflow_reviewer = (
            ROOT / ".codex" / "agents" / "workflow-final-reviewer.toml"
        ).read_text(encoding="utf-8").casefold()

        self.assertIn("最新完整 diff", rules)
        self.assertIn("最新完整 diff", final_reviewer)
        self.assertIn("风险里程碑评审（若有）", final_reviewer)
        self.assertIn("未受影响 skill", workflow_reviewer)
        self.assertNotIn("任务级评审", final_reviewer)
        self.assertNotIn("任务级与集成评审", workflow_reviewer)

    def test_agent_rules_record_tdd_and_self_containment_gates(self):
        root_rules = (ROOT / "AGENTS.md").read_text()
        skill_rules = (ROOT / "skills" / "AGENTS.md").read_text()
        for phrase in [
            "RED→GREEN→REFACTOR",
            "creating-product-requirements",
            "PRD",
            "六个 skill",
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
            configure_evidence_only_target(
                repository, "creating-development-specs-and-plans"
            )
            result = run_repository_validator(
                repository,
                "--evidence-only",
                "creating-development-specs-and-plans",
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("repository validation passed", result.stdout)

    def test_six_skill_workflow_docs_and_final_reviewer_are_current(self):
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
        self.assertIn("development request → fast | standard | full | blocked", readme)
        self.assertIn("PRD → spec+plan technical package → development prompt", readme)
        self.assertIn("approved bounded change → implementation", readme)
        self.assertIn("AGENTS rule governance", readme)
        self.assertIn("六个 skill", rules)
        self.assertIn("两个 authoring skill", reviewer)
        self.assertIn("prompt skill", reviewer)
        self.assertIn("bounded implementation skill", reviewer)
        self.assertIn("managing-agents-rules", reviewer)
        self.assertIn("六-skill plugin", reviewer)

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
            configure_evidence_only_target(
                repository, "creating-development-specs-and-plans"
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

            result = run_repository_validator(
                repository,
                "--evidence-only",
                "creating-development-specs-and-plans",
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
        self.assertIn("支持 Python 3.9 及以上", readme)
        self.assertIn("使用项目当前 `.venv`", readme)
        self.assertNotIn("维护矩阵至少覆盖 Python 3.9 和 Python 3.14", readme)

    def test_agent_development_batches_checks_and_accepts_dirty_evidence_suffix(self):
        guide = (ROOT / "docs" / "agent-development.md").read_text()

        self.assertIn(
            "scripts/check.py --skill <skill-name> [--skill <skill-name> ...]",
            guide,
        )
        self.assertIn("干净前序", guide)
        self.assertIn("连续 dirty 后序", guide)
        self.assertIn("直接运行一次统一完整门", guide)

    def test_public_workflow_describes_contiguous_dirty_evidence_suffix(self):
        workflow = (ROOT / "docs" / "workflow.md").read_text()

        self.assertIn("干净前序", workflow)
        self.assertIn("连续 dirty 后序", workflow)
        self.assertNotIn("要求完整 worktree evidence bundle", workflow)


if __name__ == "__main__":
    unittest.main()
