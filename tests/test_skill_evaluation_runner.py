import importlib.util
import json
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_skill_evaluations.py"
MODULE_SPEC = importlib.util.spec_from_file_location("skill_evaluation_runner", SCRIPT)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = RUNNER
MODULE_SPEC.loader.exec_module(RUNNER)


class SkillEvaluationRunnerTests(unittest.TestCase):
    def _scenario_root(self, root: Path, case_name: str = "01-case") -> tuple[Path, Path]:
        evaluation = root / "evaluations" / "fixture-skill"
        (evaluation / "fixtures" / "common").mkdir(parents=True)
        (evaluation / "fixtures" / "common" / "README.md").write_text(
            "fixture\n", encoding="utf-8"
        )
        case = evaluation / "cases" / f"{case_name}.md"
        case.parent.mkdir(parents=True)
        case.write_text("request\n", encoding="utf-8")
        return evaluation, case

    def _write_scenario(
        self, evaluation: Path, case: Path, payload: dict
    ) -> Path:
        path = evaluation / "fixtures" / "scenarios" / f"{case.stem}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_fixture_scenario_defaults_to_legacy_git_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)

            scenario = RUNNER.load_fixture_scenario(case, evaluation)

            self.assertEqual("git", scenario.repository_mode)
            self.assertEqual((), scenario.nested_git_roots)
            self.assertEqual((), scenario.unreadable_paths)
            self.assertEqual({}, scenario.codex_home_files)

    def test_fixture_scenario_prepares_non_git_root_and_nested_git_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            (evaluation / "fixtures" / "common" / "packages" / "nested").mkdir(
                parents=True
            )
            self._write_scenario(
                evaluation,
                case,
                {
                    "schema_version": 1,
                    "repository_mode": "non-git",
                    "nested_git_roots": ["packages/nested"],
                },
            )
            fixture = root / "fixture"
            RUNNER._copy_fixture(case, fixture, evaluation)

            scenario = RUNNER.load_fixture_scenario(case, evaluation)
            RUNNER.prepare_fixture_repositories(fixture, scenario)

            self.assertFalse((fixture / ".git").exists())
            self.assertTrue((fixture / "packages" / "nested" / ".git").is_dir())

    def test_fixture_scenario_applies_and_restores_unreadable_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            locked = evaluation / "fixtures" / "common" / "AGENTS.md"
            locked.write_text("rules\n", encoding="utf-8")
            self._write_scenario(
                evaluation,
                case,
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "unreadable_paths": ["AGENTS.md"],
                },
            )
            fixture = root / "fixture"
            RUNNER._copy_fixture(case, fixture, evaluation)
            scenario = RUNNER.load_fixture_scenario(case, evaluation)

            original_modes = RUNNER.apply_unreadable_paths(fixture, scenario)

            self.assertEqual(0, stat.S_IMODE((fixture / "AGENTS.md").stat().st_mode))
            RUNNER.restore_path_modes(original_modes)
            self.assertEqual(0o644, stat.S_IMODE((fixture / "AGENTS.md").stat().st_mode))

    def test_fixture_scenario_stages_only_allowlisted_codex_home_rule_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root, "07-global")
            source_root = (
                evaluation
                / "fixtures"
                / "scenario-files"
                / case.stem
            )
            source_root.mkdir(parents=True)
            (source_root / "AGENTS.md").write_text("base rules\n", encoding="utf-8")
            (source_root / "AGENTS.override.md").write_text(
                "temporary rules\n", encoding="utf-8"
            )
            self._write_scenario(
                evaluation,
                case,
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "codex_home_files": {
                        "AGENTS.md": str(
                            source_root.relative_to(root) / "AGENTS.md"
                        ),
                        "AGENTS.override.md": str(
                            source_root.relative_to(root) / "AGENTS.override.md"
                        ),
                    },
                },
            )
            with mock.patch.object(RUNNER, "ROOT", root):
                scenario = RUNNER.load_fixture_scenario(case, evaluation)
                codex_home = root / "codex-home"
                codex_home.mkdir()
                RUNNER.stage_scenario_codex_home(codex_home, scenario)

            self.assertEqual(
                "base rules\n", (codex_home / "AGENTS.md").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "temporary rules\n",
                (codex_home / "AGENTS.override.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                {"AGENTS.md", "AGENTS.override.md"},
                {path.name for path in codex_home.iterdir()},
            )

    def test_fixture_scenario_rejects_malformed_or_unknown_metadata(self):
        invalid_payloads = (
            {},
            {"schema_version": 2, "repository_mode": "git"},
            {"schema_version": 1},
            {"schema_version": 1, "repository_mode": "checkout"},
            {
                "schema_version": 1,
                "repository_mode": "git",
                "nested_git_roots": "nested",
            },
            {
                "schema_version": 1,
                "repository_mode": "git",
                "unknown": [],
            },
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                evaluation, case = self._scenario_root(root)
                self._write_scenario(evaluation, case, payload)
                with self.assertRaises(RUNNER.EvaluationBlocked):
                    RUNNER.load_fixture_scenario(case, evaluation)

    def test_fixture_scenario_rejects_paths_outside_case_allowlists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            outside = root / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            invalid_payloads = (
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "nested_git_roots": ["../outside"],
                },
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "unreadable_paths": ["../outside.md"],
                },
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "codex_home_files": {"config.toml": "outside.md"},
                },
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "codex_home_files": {"AGENTS.md": "outside.md"},
                },
            )
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    self._write_scenario(evaluation, case, payload)
                    with mock.patch.object(RUNNER, "ROOT", root):
                        with self.assertRaises(RUNNER.EvaluationBlocked):
                            RUNNER.load_fixture_scenario(case, evaluation)

    def test_fixture_scenario_rejects_symlinks_in_allowlisted_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            outside = root / "outside"
            outside.mkdir()
            linked = evaluation / "fixtures" / "common" / "linked"
            linked.symlink_to(outside, target_is_directory=True)
            self._write_scenario(
                evaluation,
                case,
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "nested_git_roots": ["linked"],
                },
            )

            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                RUNNER.load_fixture_scenario(case, evaluation)

    def test_copy_fixture_rejects_undeclared_symlinks_in_source_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            outside = root / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            linked = evaluation / "fixtures" / "common" / "linked.md"
            linked.symlink_to(outside)

            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                RUNNER._copy_fixture(case, root / "fixture", evaluation)

    def test_copy_fixture_rejects_symlinked_fixtures_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            external_fixtures = root / "external-fixtures"
            shutil.copytree(evaluation / "fixtures", external_fixtures)
            shutil.rmtree(evaluation / "fixtures")
            (evaluation / "fixtures").symlink_to(
                external_fixtures, target_is_directory=True
            )

            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                RUNNER._copy_fixture(case, root / "fixture", evaluation)

    def test_copy_fixture_rejects_symlinked_evaluations_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            external_evaluations = root / "external-evaluations"
            (root / "evaluations").rename(external_evaluations)
            (root / "evaluations").symlink_to(
                external_evaluations, target_is_directory=True
            )

            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                RUNNER._copy_fixture(case, root / "fixture", evaluation)

    def test_codex_home_allowlist_root_cannot_be_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root, "07-global")
            outside = root / "outside"
            outside.mkdir()
            (outside / "AGENTS.md").write_text("rules\n", encoding="utf-8")
            source_root = (
                evaluation / "fixtures" / "scenario-files" / case.stem
            )
            source_root.parent.mkdir(parents=True)
            source_root.symlink_to(outside, target_is_directory=True)
            self._write_scenario(
                evaluation,
                case,
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "codex_home_files": {
                        "AGENTS.md": str(
                            source_root.relative_to(root) / "AGENTS.md"
                        )
                    },
                },
            )

            with mock.patch.object(RUNNER, "ROOT", root):
                with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                    RUNNER.load_fixture_scenario(case, evaluation)

    def test_codex_home_source_rejects_symlinked_fixtures_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root, "07-global")
            source_root = (
                evaluation / "fixtures" / "scenario-files" / case.stem
            )
            source_root.mkdir(parents=True)
            (source_root / "AGENTS.md").write_text("rules\n", encoding="utf-8")
            self._write_scenario(
                evaluation,
                case,
                {
                    "schema_version": 1,
                    "repository_mode": "git",
                    "codex_home_files": {
                        "AGENTS.md": str(
                            source_root.relative_to(root) / "AGENTS.md"
                        )
                    },
                },
            )
            external_fixtures = root / "external-fixtures"
            shutil.copytree(evaluation / "fixtures", external_fixtures)
            shutil.rmtree(evaluation / "fixtures")
            (evaluation / "fixtures").symlink_to(
                external_fixtures, target_is_directory=True
            )

            with mock.patch.object(RUNNER, "ROOT", root):
                with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                    RUNNER.load_fixture_scenario(case, evaluation)

    def test_broken_fixture_scenario_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            scenario = evaluation / "fixtures" / "scenarios" / f"{case.stem}.json"
            scenario.parent.mkdir(parents=True)
            scenario.symlink_to(root / "missing-scenario.json")

            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                RUNNER.load_fixture_scenario(case, evaluation)

    def test_scenario_rejects_symlinked_evaluations_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            self._write_scenario(
                evaluation,
                case,
                {"schema_version": 1, "repository_mode": "git"},
            )
            external_evaluations = root / "external-evaluations"
            (root / "evaluations").rename(external_evaluations)
            (root / "evaluations").symlink_to(
                external_evaluations, target_is_directory=True
            )

            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                RUNNER.load_fixture_scenario(case, evaluation)

    def test_case_overlay_symlink_to_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation, case = self._scenario_root(root)
            outside = root / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            overlay = evaluation / "fixtures" / case.stem
            overlay.symlink_to(outside)

            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "symlink"):
                RUNNER._copy_fixture(case, root / "fixture", evaluation)

    def test_evaluation_prompt_declares_fixture_root_without_expected_output(self):
        staged = Path("/tmp/codex-home/skills/creating-product-requirements")
        prompt = RUNNER.build_evaluation_prompt(
            "user request", "creating-product-requirements", staged
        )

        self.assertIn("current working directory is the fixture repository root", prompt)
        self.assertIn("Do not inspect or search any parent directory", prompt)
        self.assertIn("scenario-staged AGENTS.md or AGENTS.override.md", prompt)
        self.assertIn("Do not inspect any other Codex-home file", prompt)
        self.assertIn("Use $creating-product-requirements", prompt)
        self.assertNotIn("$creating-development-specs-and-plans", prompt)
        self.assertTrue(prompt.endswith("user request"))
        for leaked in ("rubric", "expected output", "failure explanation"):
            self.assertNotIn(leaked, prompt.casefold())

    def test_skill_name_selects_evaluation_root_and_matching_candidate(self):
        self.assertEqual(
            ROOT / "evaluations" / "creating-product-requirements",
            RUNNER.evaluation_root("creating-product-requirements"),
        )
        with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "invalid skill name"):
            RUNNER.evaluation_root("../outside")

        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "different-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: different-skill\ndescription: Use when testing.\n---\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "does not match"):
                RUNNER.validate_phase_inputs(
                    "green", "creating-product-requirements", skill
                )

    def test_case_must_belong_to_selected_skill_evaluation_root(self):
        wrong_case = (
            ROOT
            / "evaluations"
            / "creating-development-specs-and-plans"
            / "cases"
            / "01-approval-gate.md"
        )
        with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "does not belong"):
            RUNNER.resolve_case_path("creating-product-requirements", wrong_case)

    def test_evidence_roles_enforce_skill_presence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / "case.md"
            case.write_text("request\n", encoding="utf-8")
            skill = root / "creating-product-requirements"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: creating-product-requirements\n"
                "description: Use when testing.\n---\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "requires a candidate skill"):
                RUNNER.validate_phase_inputs(
                    "current-skill-red", "creating-product-requirements", None
                )
            with self.assertRaisesRegex(RUNNER.EvaluationBlocked, "cannot receive a target skill"):
                RUNNER.validate_phase_inputs(
                    "migration-baseline", "creating-product-requirements", skill
                )
            RUNNER.validate_phase_inputs(
                "current-skill-red", "creating-product-requirements", skill
            )
            RUNNER.validate_phase_inputs(
                "migration-baseline", "creating-product-requirements", None
            )
            RUNNER.validate_phase_inputs(
                "green", "creating-product-requirements", skill
            )

    def test_cli_requires_explicit_skill_name(self):
        with self.assertRaises(SystemExit):
            RUNNER.parse_args(
                [
                    "--phase",
                    "migration-baseline",
                    "--case",
                    "case.md",
                    "--output-root",
                    "output",
                ]
            )
        args = RUNNER.parse_args(
            [
                "--skill-name",
                "creating-product-requirements",
                "--phase",
                "migration-baseline",
                "--case",
                "case.md",
                "--output-root",
                "output",
            ]
        )
        self.assertEqual("creating-product-requirements", args.skill_name)

    def test_sandbox_profile_limits_writes_to_fixture_and_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture"
            codex_home = root / "codex-home"
            forbidden = root / "forbidden"
            for path in (fixture, codex_home, forbidden):
                path.mkdir()
            RUNNER.stage_runtime_shims(codex_home)
            staged_skill = codex_home / "skills" / "fixture-skill"
            staged_skill.mkdir(parents=True)
            (staged_skill / "SKILL.md").write_text("skill\n", encoding="utf-8")
            profile = RUNNER.build_sandbox_profile(
                fixture,
                codex_home,
                staged_skill,
                [
                    Path("/bin"),
                    Path("/usr"),
                    Path("/Library"),
                    Path("/System"),
                    Path("/private/etc"),
                    Path("/private/var/db"),
                    Path("/dev"),
                ],
            )

            self.assertIn("(deny default)", profile)
            self.assertNotIn("(allow default)", profile)
            self.assertIn('(literal "/")', profile)
            self.assertIn('(literal "/dev/null")', profile)
            self.assertIn("xcrun_db(-", profile)
            self.assertNotIn(str(forbidden), profile)
            self.assertIn(str(fixture), profile)
            self.assertIn(str(codex_home), profile)
            self.assertIn(str(staged_skill), profile)

    def test_result_schema_keeps_only_operational_evidence(self):
        result = RUNNER.build_result(
            phase="green",
            case_name="01-approval-gate.md",
            exit_code=0,
            contaminations=[],
            warnings=[],
        )

        self.assertEqual(
            {
                "schema_version": 1,
                "phase": "green",
                "evidence_role": "green",
                "case": "01-approval-gate.md",
                "valid": True,
                "exit_code": 0,
                "contaminations": [],
                "warnings": [],
            },
            result,
        )
        self.assertNotRegex(repr(result), r"sha256|digest|manifest")

    def test_codex_command_uses_an_isolated_persisted_thread_for_collaboration(self):
        command = RUNNER.build_codex_command(Path("/tmp/fixture"), Path("/tmp/final.md"))

        self.assertEqual("codex", command[0])
        self.assertEqual("exec", command[1])
        for value in (
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--json",
            "--dangerously-bypass-approvals-and-sandbox",
            "/tmp/fixture",
            "/tmp/final.md",
            "-",
        ):
            self.assertIn(value, command)
        self.assertNotIn("--ephemeral", command)
        self.assertNotIn("read-only", command)
        self.assertNotIn("workspace-write", command)

    def test_collaboration_session_count_exposes_no_identifiers_or_content(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory)
            sessions = codex_home / "sessions" / "2026" / "07" / "17"
            sessions.mkdir(parents=True)
            (sessions / "parent.jsonl").write_text("parent secret\n", encoding="utf-8")
            (sessions / "reviewer.jsonl").write_text(
                "reviewer secret\n", encoding="utf-8"
            )
            (sessions / "ignored.txt").write_text("ignored\n", encoding="utf-8")

            self.assertEqual(2, RUNNER.collaboration_session_count(codex_home))
            output_root = codex_home / "raw-output"
            copied = RUNNER.copy_isolated_session_records(codex_home, output_root)
            self.assertEqual(2, copied)
            records = sorted((output_root / "collaboration-sessions").iterdir())
            self.assertEqual(["session-01.jsonl", "session-02.jsonl"], [p.name for p in records])
            self.assertEqual("parent secret\n", records[0].read_text(encoding="utf-8"))
            self.assertEqual("reviewer secret\n", records[1].read_text(encoding="utf-8"))

    def test_shell_environment_overrides_set_only_isolated_runtime_values(self):
        overrides = RUNNER.build_shell_environment_overrides(
            Path("/tmp/codex-home/bin"), Path("/tmp/codex-home")
        )

        self.assertEqual(
            [
                'shell_environment_policy.inherit="none"',
                "shell_environment_policy.ignore_default_excludes=false",
                'shell_environment_policy.set={ PATH = "/tmp/codex-home/bin:/usr/bin:/bin", HOME = "/tmp/codex-home", TMPDIR = "/tmp/codex-home/tmp", ZDOTDIR = "/tmp/codex-home" }',
            ],
            overrides,
        )
        self.assertNotRegex(repr(overrides), r"KEY|SECRET|TOKEN")

    def test_provider_overrides_preserve_only_selected_model_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text(
                'model_provider = "fixture-provider"\n'
                'model = "fixture-model"\n'
                'model_reasoning_effort = "high"\n'
                '[model_providers.fixture-provider]\n'
                'name = "Fixture"\n'
                'base_url = "https://fixture.example.invalid/v1"\n'
                'wire_api = "responses"\n'
                'requires_openai_auth = true\n'
                '[mcp_servers.secret]\n'
                'env = { TOKEN = "must-not-leak" }\n',
                encoding="utf-8",
            )

            overrides = RUNNER.load_provider_overrides(config)

            self.assertEqual(
                [
                    'model_provider="fixture-provider"',
                    'model="fixture-model"',
                    'model_reasoning_effort="high"',
                    'model_providers.fixture-provider.name="Fixture"',
                    'model_providers.fixture-provider.base_url="https://fixture.example.invalid/v1"',
                    'model_providers.fixture-provider.wire_api="responses"',
                    'model_providers.fixture-provider.requires_openai_auth=true',
                ],
                overrides,
            )
            self.assertNotIn("must-not-leak", repr(overrides))

    def test_trace_scanner_rejects_nested_forbidden_paths_and_denials(self):
        forbidden = Path("/workspace/private-repository")
        events = [
            {"type": "tool", "arguments": {"path": str(forbidden / "rubric.json")}},
            {"type": "message", "text": "sandbox: deny file-read-data"},
            {"type": "item.completed", "item": {"type": "file_change", "status": "failed"}},
        ]

        problems = RUNNER.scan_trace(events, [forbidden])

        self.assertTrue(any("private-repository" in problem for problem in problems))
        self.assertTrue(any("sandbox" in problem.casefold() for problem in problems))
        self.assertTrue(any("file_change" in problem for problem in problems))

    def test_trace_scanner_treats_generic_operation_not_permitted_as_warning(self):
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "status": "failed",
                    "aggregated_output": "rg: ..: Operation not permitted (os error 1)",
                },
            }
        ]

        problems = RUNNER.scan_trace(events, [])

        self.assertEqual([], problems)
        self.assertEqual(
            ["event 0 contains failed command_execution (exit unknown)"],
            RUNNER.scan_trace_warnings(events),
        )

    def test_failed_diagnostic_command_is_a_warning_not_contamination(self):
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "status": "failed",
                    "exit_code": 72,
                    "command": "python -m unittest",
                    "aggregated_output": "python unavailable",
                },
            }
        ]

        self.assertEqual([], RUNNER.scan_trace(events, [Path("/workspace/private")]))
        warnings = RUNNER.scan_trace_warnings(events)
        self.assertEqual(1, len(warnings))
        self.assertIn("exit 72", warnings[0])

    def test_stage_codex_home_copies_only_auth_and_optional_skill_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_home = root / "source-home"
            source_home.mkdir()
            (source_home / "auth.json").write_text(
                json.dumps({"token": "fixture-secret"}), encoding="utf-8"
            )
            (source_home / "config.toml").write_text("model = 'ignored'\n", encoding="utf-8")
            target_home = root / "target-home"

            RUNNER.stage_codex_home(source_home, target_home, None)

            self.assertEqual({"auth.json"}, {path.name for path in target_home.iterdir()})
            mode = stat.S_IMODE((target_home / "auth.json").stat().st_mode)
            self.assertEqual(0o600, mode)

            skill = root / "creating-development-specs-and-plans"
            (skill / "agents").mkdir(parents=True)
            (skill / "tests").mkdir()
            (skill / "SKILL.md").write_text("skill\n", encoding="utf-8")
            (skill / "agents" / "openai.yaml").write_text("interface: {}\n", encoding="utf-8")
            (skill / "tests" / "test_contract.py").write_text("ignored\n", encoding="utf-8")
            green_home = root / "green-home"

            RUNNER.stage_codex_home(source_home, green_home, skill)

            staged = green_home / "skills" / skill.name
            self.assertTrue((staged / "SKILL.md").is_file())
            self.assertTrue((staged / "agents" / "openai.yaml").is_file())
            self.assertFalse((staged / "tests").exists())
            self.assertNotIn("fixture-secret", repr(RUNNER.stage_codex_home))

    def test_stage_codex_home_blocks_when_auth_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_home = root / "source-home"
            source_home.mkdir()

            with self.assertRaises(RUNNER.EvaluationBlocked):
                RUNNER.stage_codex_home(source_home, root / "target-home", None)

    def test_runtime_shims_prefer_system_python_and_git(self):
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = RUNNER.stage_runtime_shims(Path(directory))

            self.assertEqual(Path("/usr/bin/python3"), (bin_dir / "python").readlink())
            self.assertEqual(Path("/usr/bin/python3"), (bin_dir / "python3").readlink())
            self.assertEqual(Path("/usr/bin/git"), (bin_dir / "git").readlink())
            self.assertEqual(
                'export PATH="$HOME/bin:/usr/bin:/bin"\n',
                (Path(directory) / ".zprofile").read_text(encoding="utf-8"),
            )
            node = shutil.which("node")
            if node:
                self.assertEqual(Path(node).resolve(), (bin_dir / "node").readlink())


if __name__ == "__main__":
    unittest.main()
