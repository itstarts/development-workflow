import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "discover_context.py"
MODULE_SPEC = importlib.util.spec_from_file_location("discover_context_under_test", SCRIPT)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
DISCOVER_CONTEXT = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = DISCOVER_CONTEXT
MODULE_SPEC.loader.exec_module(DISCOVER_CONTEXT)


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=True
    )


def initialize_repository(path: Path) -> None:
    git(path, "init", "-q")
    git(path, "config", "user.name", "Test User")
    git(path, "config", "user.email", "test@example.invalid")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    git(path, "add", "tracked.txt")
    git(path, "commit", "-q", "-m", "initial")


class DiscoverContextTestSupport:
    def setUp(self):
        super().setUp()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.base = Path(self.temporary_directory.name)

    def run_script(
        self, *args: str, process_cwd: Optional[Path] = None
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=process_cwd or self.base,
            text=True,
            capture_output=True,
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            self.fail(
                f"stdout must be one JSON document: {error}; "
                f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
            )
        return completed, payload


class DiscoverContextGitTests(DiscoverContextTestSupport, unittest.TestCase):
    def test_non_git_directory_has_null_repository_details(self):
        completed, payload = self.run_script("--cwd", str(self.base))

        self.assertEqual(0, completed.returncode)
        self.assertEqual("not-a-repository", payload["repository"]["status"])
        self.assertEqual(str(self.base.resolve()), payload["repository"]["workdir"])
        for field in ("root", "branch", "head"):
            self.assertIsNone(payload["repository"][field])
        self.assertEqual("unknown", payload["repository"]["worktree_kind"])
        self.assertEqual("", payload["repository"]["status_short_branch"])

    def test_branch_repository_reports_git_state(self):
        repository = self.base / "repository"
        repository.mkdir()
        initialize_repository(repository)
        branch = git(repository, "branch", "--show-current").stdout.strip()
        head = git(repository, "rev-parse", "HEAD").stdout.strip()

        completed, payload = self.run_script("--cwd", str(repository))

        self.assertEqual(0, completed.returncode)
        actual = payload["repository"]
        self.assertEqual("ok", actual["status"])
        self.assertEqual(str(repository.resolve()), actual["root"])
        self.assertEqual(branch, actual["branch"])
        self.assertEqual(head, actual["head"])
        self.assertEqual("main", actual["worktree_kind"])
        self.assertTrue(actual["status_short_branch"].startswith("## "))

    def test_detached_head_reports_null_branch(self):
        repository = self.base / "repository"
        repository.mkdir()
        initialize_repository(repository)
        head = git(repository, "rev-parse", "HEAD").stdout.strip()
        git(repository, "checkout", "-q", "--detach", head)

        completed, payload = self.run_script("--cwd", str(repository))

        self.assertEqual(0, completed.returncode)
        self.assertIsNone(payload["repository"]["branch"])
        self.assertEqual(head, payload["repository"]["head"])
        self.assertTrue(
            payload["repository"]["status_short_branch"].startswith("## HEAD")
        )

    def test_linked_worktree_is_detected(self):
        repository = self.base / "repository"
        linked = self.base / "linked"
        repository.mkdir()
        initialize_repository(repository)
        git(repository, "worktree", "add", "-q", "-b", "linked-test", str(linked))

        completed, payload = self.run_script("--cwd", str(linked))

        self.assertEqual(0, completed.returncode)
        self.assertEqual("linked", payload["repository"]["worktree_kind"])
        self.assertEqual(str(linked.resolve()), payload["repository"]["workdir"])
        self.assertEqual(str(linked.resolve()), payload["repository"]["root"])

    def test_explicit_cwd_wins_over_process_directory(self):
        repository = self.base / "repository"
        nested = repository / "packages" / "app"
        nested.mkdir(parents=True)
        initialize_repository(repository)
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()

        completed, payload = self.run_script(
            "--cwd", os.path.relpath(nested, elsewhere), process_cwd=elsewhere
        )

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(nested.resolve()), payload["repository"]["workdir"])
        self.assertEqual(str(repository.resolve()), payload["repository"]["root"])

    def test_output_has_fixed_top_level_shape(self):
        completed, payload = self.run_script("--cwd", str(self.base))

        self.assertEqual(0, completed.returncode)
        self.assertEqual(
            {
                "schema_version",
                "repository",
                "rules",
                "documents",
                "ambiguities",
                "errors",
                "warnings",
            },
            set(payload),
        )
        self.assertEqual(1, payload["schema_version"])
        self.assertEqual([], payload["rules"])
        self.assertEqual([], payload["ambiguities"])
        self.assertEqual([], payload["errors"])
        self.assertEqual([], payload["warnings"])

    def test_invalid_explicit_cwd_returns_json_error(self):
        missing = self.base / "missing"

        completed, payload = self.run_script("--cwd", str(missing))

        self.assertEqual(3, completed.returncode)
        self.assertTrue(payload["errors"])
        self.assertEqual(str(missing.resolve()), payload["repository"]["workdir"])

    def test_unavailable_git_returns_structured_json_error(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(self.base)],
            cwd=self.base,
            env={**os.environ, "PATH": str(self.base / "no-executables")},
            text=True,
            capture_output=True,
        )

        self.assertEqual(3, completed.returncode)
        self.assertEqual("", completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(
            {
                "schema_version",
                "repository",
                "rules",
                "documents",
                "ambiguities",
                "errors",
                "warnings",
            },
            set(payload),
        )
        self.assertEqual("not-a-repository", payload["repository"]["status"])
        self.assertTrue(
            any(
                "git" in error.casefold() and "unavailable" in error.casefold()
                for error in payload["errors"]
            )
        )


class DiscoverContextDocumentTests(DiscoverContextTestSupport, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repository = self.base / "repository"
        self.repository.mkdir()
        initialize_repository(self.repository)
        self.specs = self.repository / "docs" / "specs"
        self.plans = self.repository / "docs" / "plans"
        self.specs.mkdir(parents=True)
        self.plans.mkdir(parents=True)

    def write(self, relative_path: str, text: str, mtime_ns: int = None) -> Path:
        path = self.repository / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if mtime_ns is not None:
            os.utime(path, ns=(mtime_ns, mtime_ns))
        return path

    def discover(self, *args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        return self.run_script("--cwd", str(self.repository), *args)

    def test_default_document_directories_are_docs_specs_and_docs_plans(self):
        spec = self.write("docs/specs/2026-07-15-auth-design.md", "# Auth\n")
        plan = self.write("docs/plans/2026-07-15-auth.md", "# Auth\n")

        completed, payload = self.discover("--request", "Auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertEqual(str(plan.resolve()), payload["documents"]["plan"]["path"])

    def test_rules_are_listed_from_repository_root_to_workdir(self):
        app = self.repository / "packages" / "app"
        app.mkdir(parents=True)
        expected = [
            self.write("AGENTS.md", "root\n"),
            self.write("packages/AGENTS.md", "packages\n"),
            self.write("packages/app/AGENTS.md", "app\n"),
        ]

        completed, payload = self.run_script("--cwd", str(app))

        self.assertEqual(0, completed.returncode)
        self.assertEqual(
            [
                {"path": str(path.resolve()), "source": "filesystem", "precedence": i}
                for i, path in enumerate(expected)
            ],
            payload["rules"],
        )

    def test_automatic_rules_reject_symlink_that_resolves_outside_repository(self):
        app = self.repository / "packages" / "app"
        app.mkdir(parents=True)
        outside = self.base / "outside-AGENTS.md"
        outside.write_text("outside\n", encoding="utf-8")
        (app / "AGENTS.md").symlink_to(outside)

        completed, payload = self.run_script("--cwd", str(app))

        self.assertEqual(0, completed.returncode)
        self.assertEqual([], payload["rules"])
        self.assertNotIn(str(outside.resolve()), json.dumps(payload))

    def test_automatic_rules_reject_resolved_path_outside_repository(self):
        outside = self.base / "outside"
        outside.mkdir()
        outside_rule = outside / "AGENTS.md"
        outside_rule.write_text("outside\n", encoding="utf-8")
        (self.repository / "packages").mkdir()
        linked_directory = self.repository / "packages" / "linked"
        linked_directory.symlink_to(outside, target_is_directory=True)

        rules = DISCOVER_CONTEXT.discover_rules(
            {
                "status": "ok",
                "root": str(self.repository),
                "workdir": str(linked_directory),
            }
        )

        self.assertEqual([], rules)
        self.assertNotIn(str(outside_rule.resolve()), json.dumps(rules))

    def test_explicit_relative_documents_take_priority(self):
        explicit_spec = self.write("chosen/spec.md", "# Chosen Spec\n")
        explicit_plan = self.write("chosen/plan.md", "# Chosen Plan\n")
        self.write("docs/specs/2026-07-10-auth-design.md", "# Auth\n")
        self.write("docs/plans/2026-07-11-auth.md", "# Auth\n")

        completed, payload = self.discover(
            "--topic",
            "auth",
            "--spec",
            os.path.relpath(explicit_spec, self.repository),
            "--plan",
            os.path.relpath(explicit_plan, self.repository),
        )

        self.assertEqual(0, completed.returncode)
        self.assertEqual(
            {"path": str(explicit_spec.resolve()), "source": "explicit"},
            payload["documents"]["spec"],
        )
        self.assertEqual(str(explicit_plan.resolve()), payload["documents"]["plan"]["path"])
        self.assertEqual("explicit", payload["documents"]["plan"]["source"])

    def test_unreadable_explicit_document_exits_three_without_fallback(self):
        self.write("docs/specs/2026-07-10-auth-design.md", "# Auth\n")
        self.write("docs/plans/2026-07-11-auth.md", "# Auth\n")

        completed, payload = self.discover("--topic", "auth", "--spec", "missing.md")

        self.assertEqual(3, completed.returncode)
        self.assertTrue(payload["errors"])
        self.assertEqual("missing", payload["documents"]["spec"]["source"])

    def test_exact_topic_match_beats_partial_match(self):
        exact = self.write("docs/specs/2026-07-10-auth-design.md", "# Auth\n")
        self.write("docs/specs/2026-07-11-auth-login-design.md", "# Auth Login\n")
        self.write("docs/plans/2026-07-10-auth.md", "# Auth\n")

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(exact.resolve()), payload["documents"]["spec"]["path"])

    def test_request_derives_topic_when_explicit_topic_is_absent(self):
        related_spec = self.write(
            "docs/specs/2026-07-10-checkout-auth-design.md",
            "# Checkout Auth\n",
            1,
        )
        related_plan = self.write(
            "docs/plans/2026-07-10-checkout-auth.md",
            "# Checkout Auth\n",
            1,
        )
        self.write(
            "docs/specs/2026-07-12-reporting-dashboard-design.md",
            "# Reporting Dashboard\n",
            2,
        )
        self.write(
            "docs/plans/2026-07-12-reporting-dashboard.md",
            "# Reporting Dashboard\n",
            2,
        )

        completed, payload = self.discover(
            "--request", "Implement checkout auth safely"
        )

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(related_spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertEqual(str(related_plan.resolve()), payload["documents"]["plan"]["path"])

    def test_explicit_topic_takes_priority_over_request_derived_topic(self):
        checkout_spec = self.write(
            "docs/specs/2026-07-10-checkout-auth-design.md", "# Checkout Auth\n"
        )
        checkout_plan = self.write(
            "docs/plans/2026-07-10-checkout-auth.md", "# Checkout Auth\n"
        )
        reporting_spec = self.write(
            "docs/specs/2026-07-11-reporting-dashboard-design.md",
            "# Reporting Dashboard\n",
        )
        reporting_plan = self.write(
            "docs/plans/2026-07-11-reporting-dashboard.md",
            "# Reporting Dashboard\n",
        )

        completed, payload = self.discover(
            "--request", "Implement reporting dashboard", "--topic", "checkout auth"
        )

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(checkout_spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertEqual(str(checkout_plan.resolve()), payload["documents"]["plan"]["path"])
        self.assertNotEqual(str(reporting_spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertNotEqual(str(reporting_plan.resolve()), payload["documents"]["plan"]["path"])

    def test_normalized_filename_exact_match_beats_partial_heading(self):
        exact = self.write(
            "docs/specs/2026-07-10-auth-design.md", "No heading here.\n"
        )
        self.write(
            "docs/specs/2026-07-11-auth-login-design.md", "# Auth Login\n"
        )
        self.write("docs/plans/2026-07-10-auth.md", "# Auth\n")

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(exact.resolve()), payload["documents"]["spec"]["path"])

    def test_single_available_document_is_preserved_when_other_side_is_missing(self):
        spec = self.write("docs/specs/2026-07-10-auth-design.md", "# Auth\n")

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertEqual("discovered", payload["documents"]["spec"]["source"])
        self.assertEqual("missing", payload["documents"]["plan"]["source"])

    def test_auto_discovery_rejects_symlink_candidates_outside_repository(self):
        legal_spec = self.write(
            "docs/specs/2026-07-10-auth-design.md", "# Auth\n"
        )
        legal_plan = self.write(
            "docs/plans/2026-07-10-auth.md", "# Auth\n"
        )
        outside_spec = self.base / "outside-spec.md"
        outside_plan = self.base / "outside-plan.md"
        outside_spec.write_text("# Auth\n", encoding="utf-8")
        outside_plan.write_text(
            "---\nreview_status: approved\n---\n# Auth\n", encoding="utf-8"
        )
        (self.specs / "2026-07-11-auth-design.md").symlink_to(outside_spec)
        (self.plans / "2026-07-11-auth.md").symlink_to(outside_plan)

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(
            str(legal_spec.resolve()), payload["documents"]["spec"]["path"]
        )
        self.assertEqual(
            str(legal_plan.resolve()), payload["documents"]["plan"]["path"]
        )
        serialized = json.dumps(payload)
        self.assertNotIn(str(outside_spec.resolve()), serialized)
        self.assertNotIn(str(outside_plan.resolve()), serialized)

    def test_explicit_symlink_document_remains_allowed(self):
        outside_spec = self.base / "outside-spec.md"
        outside_plan = self.base / "outside-plan.md"
        outside_spec.write_text("# Auth\n", encoding="utf-8")
        outside_plan.write_text("# Auth\n", encoding="utf-8")
        spec_link = self.repository / "spec-link.md"
        plan_link = self.repository / "plan-link.md"
        spec_link.symlink_to(outside_spec)
        plan_link.symlink_to(outside_plan)

        completed, payload = self.discover(
            "--spec", str(spec_link), "--plan", str(plan_link)
        )

        self.assertEqual(0, completed.returncode)
        self.assertEqual(
            str(outside_spec.resolve()), payload["documents"]["spec"]["path"]
        )
        self.assertEqual(
            str(outside_plan.resolve()), payload["documents"]["plan"]["path"]
        )
        self.assertEqual("explicit", payload["documents"]["spec"]["source"])
        self.assertEqual("explicit", payload["documents"]["plan"]["source"])

    def test_token_coverage_breaks_non_exact_tie(self):
        covered = self.write(
            "docs/specs/2026-07-10-auth-login-session-design.md",
            "# Auth Login Session\n",
        )
        self.write("docs/specs/2026-07-11-auth-session-design.md", "# Auth Session\n")
        self.write("docs/plans/2026-07-10-auth-login.md", "# Auth Login\n")

        completed, payload = self.discover("--topic", "auth login")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(covered.resolve()), payload["documents"]["spec"]["path"])

    def test_newer_iso_date_breaks_topic_tie(self):
        self.write("docs/specs/2026-07-10-auth-design.md", "# Auth\n")
        newer = self.write("docs/specs/2026-07-11-auth-design.md", "# Auth\n")
        self.write("docs/plans/2026-07-11-auth.md", "# Auth\n")

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(newer.resolve()), payload["documents"]["spec"]["path"])

    def test_mtime_breaks_tie_after_topic_and_date(self):
        self.write("docs/specs/auth-one.md", "# Auth\n", 1_000_000_000)
        newer = self.write(
            "docs/specs/auth-two.md", "# Auth\n", 2_000_000_000
        )
        self.write("docs/plans/auth.md", "# Auth\n")

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(newer.resolve()), payload["documents"]["spec"]["path"])

    def test_complete_score_tie_requires_selection(self):
        first = self.write("docs/specs/auth-one.md", "# Auth\n", 1_000_000_000)
        second = self.write("docs/specs/auth-two.md", "# Auth\n", 1_000_000_000)
        self.write("docs/plans/auth.md", "# Auth\n")

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(2, completed.returncode)
        ambiguity = payload["ambiguities"][0]
        self.assertEqual("document_pair", ambiguity["field"])
        self.assertTrue({str(first.resolve()), str(second.resolve())}.issubset(ambiguity["candidates"]))
        self.assertIsNone(payload["documents"]["spec"]["path"])

    def test_explicit_spec_selects_plan_that_references_it(self):
        spec = self.write("chosen/auth-spec.md", "# Auth\n")
        referenced = self.write(
            "docs/plans/auth-one.md", "# Auth\n\nSee chosen/auth-spec.md.\n", 1
        )
        self.write("docs/plans/auth-two.md", "# Auth\n", 2)

        completed, payload = self.discover("--topic", "auth", "--spec", str(spec))

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(referenced.resolve()), payload["documents"]["plan"]["path"])

    def test_explicit_plan_selects_spec_that_it_references(self):
        referenced = self.write("docs/specs/auth-one.md", "# Auth\n", 1)
        self.write("docs/specs/auth-two.md", "# Auth\n", 2)
        plan = self.write("chosen/auth-plan.md", "# Auth\n\nSee auth-one.md.\n")

        completed, payload = self.discover("--topic", "auth", "--plan", str(plan))

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(referenced.resolve()), payload["documents"]["spec"]["path"])

    def test_auto_pair_prefers_single_direction_reference(self):
        referenced_spec = self.write("docs/specs/auth-one.md", "# Auth\n", 1)
        self.write("docs/specs/auth-two.md", "# Auth\n", 2)
        referenced_plan = self.write(
            "docs/plans/auth-one.md", "# Auth\n\nSee auth-one.md.\n", 1
        )
        self.write("docs/plans/auth-two.md", "# Auth\n", 2)

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(referenced_spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertEqual(str(referenced_plan.resolve()), payload["documents"]["plan"]["path"])

    def test_auto_pair_prefers_bidirectional_over_single_reference(self):
        bidirectional_spec = self.write(
            "docs/specs/auth-one.md", "# Auth\n\nSee auth-one-plan.md.\n", 1
        )
        self.write("docs/specs/auth-two.md", "# Auth\n", 2)
        bidirectional_plan = self.write(
            "docs/plans/auth-one-plan.md", "# Auth\n\nSee auth-one.md.\n", 1
        )
        self.write(
            "docs/plans/auth-two-plan.md", "# Auth\n\nSee auth-two.md.\n", 2
        )

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(bidirectional_spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertEqual(str(bidirectional_plan.resolve()), payload["documents"]["plan"]["path"])

    def test_explicit_conflicting_references_only_warn(self):
        spec = self.write("chosen/auth-spec.md", "# Auth\n\nSee other-plan.md.\n")
        plan = self.write("chosen/auth-plan.md", "# Auth\n\nSee other-spec.md.\n")

        completed, payload = self.discover("--spec", str(spec), "--plan", str(plan))

        self.assertEqual(0, completed.returncode)
        self.assertEqual(str(spec.resolve()), payload["documents"]["spec"]["path"])
        self.assertEqual(str(plan.resolve()), payload["documents"]["plan"]["path"])
        self.assertTrue(payload["warnings"])

    def test_highest_pair_tuple_tie_reports_all_involved_paths(self):
        first = self.write("docs/specs/auth-one.md", "# Auth\n", 1_000_000_000)
        second = self.write("docs/specs/auth-two.md", "# Auth\n", 1_000_000_000)
        plan = self.write(
            "docs/plans/auth.md",
            "# Auth\n\nSee auth-one.md and auth-two.md.\n",
            1_000_000_000,
        )

        completed, payload = self.discover("--topic", "auth")

        self.assertEqual(2, completed.returncode)
        ambiguity = payload["ambiguities"][0]
        self.assertEqual("document_pair", ambiguity["field"])
        self.assertEqual(
            {str(first.resolve()), str(second.resolve()), str(plan.resolve())},
            set(ambiguity["candidates"]),
        )


class DiscoverContextReviewTests(DiscoverContextTestSupport, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repository = self.base / "repository"
        self.repository.mkdir()
        initialize_repository(self.repository)
        self.spec = self.repository / "spec.md"
        self.spec.write_text("# Spec\n", encoding="utf-8")
        self.plan = self.repository / "plan.md"

    def review(self, text: str) -> dict:
        self.plan.write_text(text, encoding="utf-8")
        completed, payload = self.run_script(
            "--cwd",
            str(self.repository),
            "--spec",
            str(self.spec),
            "--plan",
            str(self.plan),
        )
        self.assertEqual(0, completed.returncode)
        return payload["documents"]["plan"]["review"]

    def test_frontmatter_approved_includes_optional_metadata(self):
        actual = self.review(
            "---\nreview_status: APPROVED\nreviewer: review-agent\n"
            "reviewed_at: 2026-07-11\n---\n# Plan\n"
        )

        self.assertEqual(
            {
                "status": "approved",
                "reviewer": "review-agent",
                "reviewed_at": "2026-07-11",
            },
            actual,
        )

    def test_chinese_plan_frontmatter_maps_review_lifecycle(self):
        approved = self.review(
            "---\n"
            "文档类型: 实施计划\n"
            "主题: localized-metadata\n"
            "技术规格: docs/specs/2026-07-19-localized-metadata-design.md\n"
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
            },
            approved,
        )

        pending = self.review(
            "---\n"
            "文档类型: 实施计划\n"
            "主题: localized-metadata\n"
            "技术规格: docs/specs/2026-07-19-localized-metadata-design.md\n"
            "技术规格用户批准: 已批准\n"
            "计划评审状态: 待评审\n"
            "---\n# Plan\n"
        )
        self.assertEqual(
            {"status": "not-approved", "reviewer": None, "reviewed_at": None},
            pending,
        )

    def test_mixed_or_invalid_chinese_plan_metadata_is_unknown(self):
        cases = (
            (
                "---\n文档类型: 实施计划\n主题: localized-metadata\n"
                "技术规格: docs/specs/example-design.md\n技术规格用户批准: 已批准\n"
                "计划评审状态: 已通过\n计划评审角色: skill-reviewer\n"
                "计划评审日期: 2026-07-19\nreview_status: approved\n---\n"
            ),
            (
                "---\n文档类型: 实施计划\n主题: localized-metadata\n"
                "技术规格: docs/specs/example-design.md\n技术规格用户批准: 已批准\n"
                "计划评审状态: 已通过\n计划评审状态: 已通过\n"
                "计划评审角色: skill-reviewer\n计划评审日期: 2026-07-19\n---\n"
            ),
            (
                "---\n文档类型: 实施计划\n主题: localized-metadata\n"
                "技术规格: docs/specs/example-design.md\n技术规格用户批准: 已批准\n"
                "计划评审状态: 已通过\n计划评审角色: skill-reviewer\n"
                "计划评审日期: 2026-07-19\n额外字段: 值\n---\n"
            ),
            (
                "---\n文档类型: 实施计划\n主题: localized-metadata\n"
                "技术规格: docs/specs/example-design.md\n技术规格用户批准: 已批准\n"
                "计划评审状态: approved\n计划评审角色: skill-reviewer\n"
                "计划评审日期: 2026-07-19\n---\n"
            ),
            (
                "---\n文档类型: 实施计划\n主题: localized-metadata\n"
                "技术规格: docs/specs/example-design.md\n技术规格用户批准: 已批准\n"
                "计划评审状态: \"已通过\"\n计划评审角色: skill-reviewer\n"
                "计划评审日期: 2026-07-19\n---\n"
            ),
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual("unknown", self.review(text)["status"])

    def test_incomplete_chinese_plan_or_approved_without_review_metadata_is_unknown(self):
        complete_pending_lines = [
            "文档类型: 实施计划",
            "主题: localized-metadata",
            "技术规格: docs/specs/example-design.md",
            "技术规格用户批准: 已批准",
            "计划评审状态: 待评审",
        ]
        for missing_index in range(len(complete_pending_lines)):
            lines = [
                line
                for index, line in enumerate(complete_pending_lines)
                if index != missing_index
            ]
            with self.subTest(missing=complete_pending_lines[missing_index]):
                self.assertEqual(
                    "unknown",
                    self.review("---\n" + "\n".join(lines) + "\n---\n")["status"],
                )

        for lifecycle in (
            complete_pending_lines[:-1] + ["计划评审状态: 已通过"],
            complete_pending_lines
            + ["计划评审角色: stale-reviewer", "计划评审日期: 2026-07-19"],
        ):
            with self.subTest(lifecycle=lifecycle):
                self.assertEqual(
                    "unknown",
                    self.review("---\n" + "\n".join(lifecycle) + "\n---\n")["status"],
                )

    def test_chinese_legacy_header_is_not_accepted(self):
        text = (
            "计划评审角色: skill-reviewer\n"
            "计划评审日期: 2026-07-19\n"
            "计划评审状态: 已通过\n\n# Plan\n"
        )
        self.assertEqual("unknown", self.review(text)["status"])

    def test_frontmatter_explicit_other_status_is_not_approved(self):
        self.assertEqual(
            "not-approved",
            self.review("---\nreview_status: pending\n---\n# Plan\n")["status"],
        )

    def test_frontmatter_without_status_is_unknown(self):
        self.assertEqual(
            "unknown", self.review("---\nreviewer: agent\n---\n# Plan\n")["status"]
        )

    def test_duplicate_or_conflicting_frontmatter_status_is_unknown(self):
        for text in (
            "---\nreview_status: approved\nreview_status: approved\n---\n",
            "---\nreview_status: approved\nreview_status: rejected\n---\n",
        ):
            with self.subTest(text=text):
                self.assertEqual("unknown", self.review(text)["status"])

    def test_unclosed_frontmatter_does_not_fall_back_to_header(self):
        text = "---\nreview_status: approved\nReview-Status: approved\n# Plan\n"
        self.assertEqual("unknown", self.review(text)["status"])

    def test_nested_multiline_and_unrecognized_quoted_scalars_are_unknown(self):
        malformed = (
            "---\nreview_status:\n  value: approved\n---\n",
            "---\nreview_status: |\n  approved\n---\n",
            "---\nreview_status: \"approved\"\n---\n",
        )
        for text in malformed:
            with self.subTest(text=text):
                self.assertEqual("unknown", self.review(text)["status"])

    def test_header_approved_before_content_is_recognized(self):
        actual = self.review(
            "Reviewer: header-agent\nReviewed-At: 2026-07-12\n"
            "Review-Status: approved\n\n# Plan\n"
        )
        self.assertEqual("approved", actual["status"])
        self.assertEqual("header-agent", actual["reviewer"])
        self.assertEqual("2026-07-12", actual["reviewed_at"])

    def test_header_other_status_is_not_approved(self):
        self.assertEqual(
            "not-approved",
            self.review("Review-Status: changes-requested\n\n# Plan\n")["status"],
        )

    def test_duplicate_or_conflicting_header_status_is_unknown(self):
        for text in (
            "Review-Status: approved\nReview-Status: approved\n# Plan\n",
            "Review-Status: approved\nReview-Status: rejected\n# Plan\n",
        ):
            with self.subTest(text=text):
                self.assertEqual("unknown", self.review(text)["status"])

    def test_marker_after_heading_or_body_is_ignored(self):
        for text in (
            "# Plan\nReview-Status: approved\n",
            "This is the plan.\nReview-Status: approved\n",
        ):
            with self.subTest(text=text):
                self.assertEqual("unknown", self.review(text)["status"])

    def test_code_fence_pseudo_marker_is_ignored(self):
        text = "```yaml\nReview-Status: approved\n```\n# Plan\n"
        self.assertEqual("unknown", self.review(text)["status"])

    def test_header_after_twenty_nonempty_metadata_lines_is_ignored(self):
        prefix = "".join(f"Meta-{index}: value\n" for index in range(20))
        self.assertEqual(
            "unknown", self.review(prefix + "Review-Status: approved\n# Plan\n")["status"]
        )

    def test_frontmatter_must_start_at_first_byte(self):
        text = "\ufeff---\nreview_status: approved\n---\n# Plan\n"
        self.assertEqual("unknown", self.review(text)["status"])


if __name__ == "__main__":
    unittest.main()
